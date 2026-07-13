# 07 — MOS V0.85: Diseño de implementación (Memory Operating System Skeleton)

> **Origen**: `FABLE5_PROMPTS/PROMPT_01_MEMORY_MOS_V085.md` — **Opción elegida: B (MOS
> Skeleton)**, la recomendada. Arquitectura correcta, implementación mínima, deuda ≈ 0.
> **Audiencia**: Claude Code (Opus 4.8). Este documento es la especificación de
> implementación. La visión completa del MOS está en `08_MOS_ARQUITECTURA_COMPLETA.md`
> — leerla ANTES de implementar, porque los contratos de aquí son los definitivos.
>
> **Criterio de cierre de V0.85**: preguntar *"¿qué me ha llegado importante hoy?"*
> responde desde memoria local sin llamar a Gmail en caliente.
>
> **Δ 2026-07-12 (Cognitive Runtime, docs 14/15/16)** — 4 deltas menores, ya
> integrados abajo con la marca `[Δ]`: (1) el stub de skills usa el `LocalSkill`
> ampliado con linaje (doc 09 §1.1); (2) `decisions.mission_id`; (3) nace
> `app/core/events.py` y la ingesta emite eventos; (4) disciplina modular del doc
> 16 §4 desde M1. **Nada más cambia**: `IMemoryStore`, `MemoryRouter`, `MemoryType`,
> ingesta, summarizer, briefing, compactación y la posición de V0.85 quedan intactos.

---

## 1. Decisión registrada

| Campo | Valor |
|---|---|
| Decisión | Opción B — MOS Skeleton |
| Razón | Contratos definitivos desde el día 1 (Orchestrator V1.0 y Hermes V1.1 dependen de `IMemoryStore`); coste 4-6 sesiones; deuda ≈ 0 |
| Alternativas | A (Express: refactor obligado en V1.0), C (ACI Full: retrasa V0.9 1-2 meses — incompatible con V1.0 = MVP alcanzable) |
| Regla aplicada | §2.3 PROMPT_01: "diseñar hoy la arquitectura para todo, implementar hoy solo lo necesario" |

## 2. Estructura de código nueva

```
backend/app/memory/
├── memory_manager.py        # EXISTENTE — no se reescribe (restricción P01 §4.4).
│                            # Pasa a ser el backend interno de LocalMemoryStore
│                            # para la colección conversacional legacy.
├── interfaces.py            # NUEVO — IMemoryStore, ISkillStore, MemoryType,
│                            #         MemoryItem, MemoryQuery (contratos 10 años)
├── stores/
│   ├── local_store.py       # NUEVO — LocalMemoryStore(IMemoryStore) sobre ChromaDB
│   ├── distributed_store.py # NUEVO — stub NotImplementedError("V2.0+")
│   └── skill_store.py       # NUEVO — LocalSkillStore(ISkillStore) básico (stub de LSL,
│                            #         contratos de 09_LSL_LLL_RFC.md)
├── router.py                # NUEVO — MemoryRouter: MemoryType -> IMemoryStore
├── ingestion.py             # NUEVO — jobs asyncio de ingesta (email + calendario)
├── summarizer.py            # NUEVO — batch nocturno de resúmenes (Ollama-first)
├── lifecycle.py             # NUEVO — MemoryLifecycleManager (compactación; en V0.85
│                            #         solo dedup + presupuesto; diseño completo en 08 RFC-007)
└── vault.py                 # NUEVO (opcional, sprint 4) — espejo Markdown
```

Regla de dependencias (P01 §6.2, inviolable):
`endpoints → MemoryRouter → IMemoryStore → ChromaDB`. Nadie salta capas. El chat y
el gateway consultan por `MemoryRouter`, jamás por ChromaDB directo.

## 3. Contratos (interfaces.py) — CONGELADOS

Estos contratos son los que usarán V0.9 (briefing), V1.0 (Orchestrator), V1.1
(adapters de Hermes) y V2.0+ (stores distribuidos). No cambian; solo se extienden.

```python
class MemoryType(str, Enum):
    # V0.85 — activos (nombres de capa, NO de tecnología — P03 §9.2)
    CONVERSATIONAL = "mem_conversational"
    PERSONAL       = "mem_personal"
    PROJECT        = "mem_project"
    SKILL          = "mem_skill"
    DECISION       = "mem_decision"
    # Reservados (colección creada lazy cuando se usen; NO en V0.85)
    EPISODIC       = "mem_episodic"      # V1.2+
    ERROR          = "mem_error"         # V0.9 (Automation los escribe)
    TOOL           = "mem_tool"          # V1.x
    AUTOMATION     = "mem_automation"    # V0.9
    KNOWLEDGE      = "mem_knowledge"     # V1.2+
    WORKING        = "mem_working"       # V1.1 (interno de HermesRuntime)


@dataclass(frozen=True)
class MemoryItem:
    id: str
    content: str
    memory_type: MemoryType
    source: str                  # "email" | "calendar" | "chat" | "hermes" | "user" | ...
    created_at: datetime
    metadata: dict               # source_id, sender, category, project, channel...
    score: float | None = None   # relevancia en resultados de search


class IMemoryStore(ABC):
    """Contrato único de acceso a memoria. Implementaciones: LocalMemoryStore
    (V0.85, ChromaDB), QdrantMemoryStore (V1.x), DistributedMemoryStore (V2.0+).
    El caller NUNCA sabe qué tecnología hay debajo (RFC-006 de doc 08)."""

    @abstractmethod
    async def store(self, content: str, memory_type: MemoryType, source: str,
                    metadata: dict | None = None, dedup_key: str | None = None) -> str:
        """Indexa. dedup_key (p.ej. email_id) hace la operación idempotente:
        si ya existe un item con ese dedup_key en ese tipo, se actualiza."""

    @abstractmethod
    async def search(self, query: str, memory_types: list[MemoryType] | None = None,
                     top_k: int = 5, filters: dict | None = None) -> list[MemoryItem]: ...

    @abstractmethod
    async def retrieve(self, item_id: str) -> MemoryItem | None: ...

    @abstractmethod
    async def summarize(self, memory_type: MemoryType, date_from: date,
                        date_to: date) -> str:
        """Resumen del rango (usa resúmenes precalculados si existen)."""

    @abstractmethod
    async def forget(self, memory_type: MemoryType, filters: dict) -> int:
        """Borra por criterio. Devuelve nº de items. Transparencia: el usuario
        siempre puede olvidar. Con vault activo, borra también el .md espejo."""

    @abstractmethod
    async def context(self, query: str, max_tokens: int = 1500,
                      memory_types: list[MemoryType] | None = None) -> str:
        """Bloque de contexto listo para inyectar en un prompt, con atribución
        de fuente por línea ('[email de X, martes] ...'). Es LA llamada que
        harán chat (V0.85), briefing (V0.9) y Context Enricher (V1.0)."""
```

`MemoryRouter`: mantiene `{MemoryType: IMemoryStore}`; V0.85 mapea TODO a
`LocalMemoryStore`; expone los mismos 6 métodos delegando; singleton `memory_router`
(patrón `ai_manager`). Registro futuro de stores sin tocar callers: ese es el punto
de intercambio tecnológico que pide el usuario.

## 4. Esquema ChromaDB (colecciones + metadata)

Una colección por `MemoryType` activo. Metadata obligatoria en todo item:
`{source, source_id, created_at_iso, date (YYYY-MM-DD)}`. Específica:

| Colección | Metadata adicional | Contenido típico |
|---|---|---|
| `mem_conversational` | channel, role, model | mensajes chat/gateway (migra la colección `conversations` actual vía alias — sin migración de datos: se lee de ambas hasta que la vieja se agote por lifecycle) |
| `mem_personal` | kind (preference/fact/contact/routine) | "prefiere reuniones por la mañana" |
| `mem_project` | project, kind | estado/decisión de proyecto (stub: pocas escrituras en V0.85) |
| `mem_skill` | skill_name, status, version | stub de LSL (doc 09) |
| `mem_decision` | decision_id (FK a tabla `decisions`) | espejo semántico de la tabla SQL |

**Emails y calendario NO tienen colección propia**: se indexan en
`mem_conversational`... **NO** — corrección de diseño: van a colecciones de ingesta
`mem_inbox` y `mem_agenda` bajo `MemoryType.PERSONAL`? Tampoco. Decisión final:
**los emails/eventos se indexan en `mem_personal`** con `source="email"|"calendar"`
y `kind="inbox_item"|"agenda_item"` — son contexto personal del usuario, la capa
Private Memory (P03 Capa 1). Los filtros por `source` los separan sin multiplicar
colecciones. Menos colecciones = menos superficie (principio 8 AOS).

## 5. Modelos SQL nuevos (una migración Alembic)

```python
class MemoryJobRun(Base):          # tracking de jobs de ingesta/resumen
    __tablename__ = "memory_job_runs"
    id, job_name (ix), started_at, finished_at, status (ok|error|running, ix),
    items_processed, error_detail, checkpoint (JSON: p.ej. último email_id/fecha)

class Decision(Base):              # Decision Memory (P03 §5.1) — nace en V0.85
    __tablename__ = "decisions"
    id (UUID str), title, body, reason, alternatives (JSON), project (ix, null),
    outcome (null), impact (high|med|low), status (active|superseded|archived, ix),
    superseded_by (null), created_at (ix),
    mission_id (str, null, ix)     # [Δ 14 §4.1] enlaza planes/reflexiones del TIE
                                   # (V1.0+) sin migración nueva; null hasta entonces
```

`decisions` nace ahora porque V0.9 (aprobaciones) y V1.0 (planes) escriben en ella
desde su primer día — así no hay migración funcional después. API interna:
`decision_service.store_decision(...)` en `app/services/` + espejo en `mem_decision`.

## 6. Ingesta (ingestion.py)

- **Job email** (cada 20 min, configurable `MEMORY_INGEST_INTERVAL_MIN`): lee el
  preview del inbox VÍA `email_service`/`EmailTool` (nunca Gmail directo), cruza con
  `EmailTriage` (categoría ya calculada), e indexa `subject + snippet + sender` con
  `dedup_key=email_id`. NO llama al LLM (el triaje ya existe; si un email no está
  triado, se indexa con category=null y se re-etiqueta en la pasada siguiente).
- **Job calendario** (cada 60 min): eventos locales (`CalendarEvent`) + Google
  (`calendar_tool`, fail-soft) de −7 a +14 días, `dedup_key=f"cal:{id}"`.
- **Arranque**: `asyncio.create_task()` en el `lifespan` (P01 §6.4), try/except
  total, escribe `MemoryJobRun` por pasada, jitter inicial 30 s para no competir
  con el arranque. Si Google no está conectado → pasada "ok, 0 items", sin ruido.
- **Idempotencia**: `dedup_key` + checkpoint (último `internalDate` procesado).
- **[Δ 14 §4.1] Eventos**: cada pasada con items nuevos emite `memory.ingested`
  (y el triaje `email.triaged`) en `app/core/events.py` — pub/sub in-process
  mínimo (≤80 líneas; **especificación canónica: doc 17** — contrato `Event`,
  naming, reglas de payload y `test_events.py`). Consumers ya con fecha:
  `EventTrigger` del AE (V0.9), micro-análisis del Learner (V1.1), tarjetas del
  Hub. Sin esto, V0.9 tendría que retro-instrumentar la ingesta.

## 7. Resumen nocturno (summarizer.py)

- Job diario 03:30 local (asyncio, mismo patrón). Genera **resumen del día**:
  emails del día agrupados por categoría de triaje + eventos + nº de conversaciones.
- **Modelo**: Ollama si está sano (coste 0) → si no, proveedor activo → si no hay
  ninguno, resumen **determinista** (plantilla con conteos y asuntos top; el sistema
  degrada, nunca se salta el día). Salida SIEMPRE por `strip_reasoning()` (B21).
- Persistencia: item en `mem_personal` (`kind="daily_summary"`, `date=...`,
  `dedup_key=f"day:{date}"` → re-ejecutar un día lo sobreescribe) + entrada
  `MemoryJobRun`. Jerarquía superior (semana/mes) llega con lifecycle en 08 RFC-007;
  el campo `kind` ya lo soporta (`weekly_summary`).

## 8. Contexto en chat + endpoints

- `chat.py::_build_system_prompt` pasa a llamar `memory_router.context(query,
  max_tokens=1200)` (que internamente combina RAG conversacional existente + los
  nuevos items con atribución de fuente). **Presupuesto de latencia**: ≤ 300 ms; si
  la búsqueda excede el timeout → contexto vacío, el chat no espera (P07 §5.1).
- **Consolidación** (P07 §7.2): `gateway.chat_message_handler` y `/api/chat` usan la
  MISMA función `app/services/chat_service.py::answer(envelope_or_request)` — se
  extrae en el sprint 4 y elimina la duplicación actual.
- Endpoints nuevos (aditivos; los `/api/memory/*` existentes NO cambian):

| Ruta | Qué devuelve |
|---|---|
| `GET /api/memory/briefing?date=` | briefing estructurado: resumen del día, urgentes pendientes, agenda, top remitentes. Solo BD/Chroma local. **Es el endpoint que V0.9 `daily_briefing` consumirá tal cual** |
| `GET /api/memory/ingest/status` | últimas `MemoryJobRun` por job + próximo run |
| `POST /api/memory/ingest/run` | fuerza una pasada (para probar sin esperar 20 min) |
| `GET /api/memory/stats` (extiende) | items por colección, tamaño estimado, cobertura de días |

- Hub: tarjeta "Memoria" (última ingesta, días cubiertos, briefing de hoy en 2 líneas).

## 9. Vault — ✅ IMPLEMENTADO (2026-07-13, post-cierre de M1-M5)

`vault.py`: espejo Markdown de `mem_personal.kind=daily_summary` y `decisions` en
`%APPDATA%/Aithera/vault/YYYY/MM/` (`AITHERA_VAULT_PATH` la reubica — aislado en
tests, mismo patrón que `AITHERA_CHROMA_PATH`). Solo escritura en V0.85
(bidireccional = V1.x, sin fecha). Best-effort: un fallo de disco nunca rompe al
caller. Wiring: `summarizer.run_summarizer()` escribe el resumen del día tras
persistir en `mem_personal`; `decision_service._mirror_to_memory()` escribe cada
decisión (alta y `link_outcome`) tras el espejo semántico. Expuesto en el barrel
(`vault_write_daily_summary`, `vault_write_decision`); `app.memory.vault` añadido
a `FORBIDDEN` en `test_module_boundaries.py`. Cobertura: `test_vault.py` (9 tests
+ 2 de integración con summarizer/decision_service). No se había hecho antes por
gestión de tiempo durante el sprint M1-M5, no por ningún motivo técnico.

## 10. Plan de sprints (Opus 4.8)

| Sprint | Contenido | Cierre verificable |
|---|---|---|
| M1 | `interfaces.py` + `LocalMemoryStore` + `MemoryRouter` + stubs + colecciones + migración (`memory_job_runs`, `decisions` con `mission_id` [Δ]) + `test_memory_contracts.py` + **[Δ 16 §4] API pública en `app/memory/__init__.py` + `test_module_boundaries.py`** | suite verde; `memory_router.store/search/context` funcionan e2e con ChromaDB; rutas `/api/memory/*` existentes intactas por contrato; test de fronteras verde |
| M2 | `ingestion.py` (email+calendario) + endpoints ingest + `test_memory_ingestion.py` + **[Δ] `app/core/events.py` + emisión `memory.ingested`/`email.triaged`** | `POST ingest/run` indexa el inbox real; segunda pasada = 0 duplicados; job visible en `ingest/status`; un handler de prueba recibe el evento |
| M3 | `summarizer.py` + `GET /briefing` + tarjeta Hub + `test_memory_briefing.py` | "¿qué me ha llegado hoy?" responde desde memoria con Gmail desconectado (**criterio de cierre de fase**) |
| M4 | contexto en chat vía router + consolidación chat/gateway (`chat_service.py`) + `test_memory_context.py` + vault si cabe | el chat cita fuentes ("según el email de X del martes"); handler del gateway y endpoint comparten implementación |
| M5 | hardening: init async de ChromaDB en background (P07-B2), migración de índices (P07-B3), presupuestos de latencia, `test_startup_time.py` | backend acepta peticiones < 2 s; búsqueda < 200 ms con 10k items; CLAUDE.md + roadmap actualizados; tag `v0.8.5` |

## 11. Handoff a V0.9 (contrato garantizado)

Al cerrar V0.85, V0.9 puede asumir SIN comprobar: (1) `GET /api/memory/briefing`
estable y testeado por contrato; (2) `memory_router.context()` con presupuesto
≤ 300 ms; (3) tabla `decisions` + `decision_service` listos para las aprobaciones;
(4) `MemoryType.ERROR/AUTOMATION` definidos (colección se crea sola al primer
`store`); (5) jobs asyncio como patrón de referencia para migrar a APScheduler;
(6) [Δ] `app/core/events.py` operativo con `memory.ingested`/`email.triaged` —
el `EventTrigger` de V0.9 solo se suscribe, no instrumenta nada.

## 12. Riesgos

| Riesgo | Mitigación |
|---|---|
| Ingesta duplica items | `dedup_key` obligatorio + test de segunda pasada |
| Resumen nocturno sin ningún LLM | plantilla determinista (nunca se salta el día) |
| Chroma lento con crecimiento | lifecycle 08 RFC-007 + presupuesto/timeout en `context()` |
| Contexto envenena el prompt | atribución de fuente + límite duro de tokens + `strip_reasoning` |

---
*Diseño 2026-07-09 (Fable 5). Implementación: Opus 4.8. Contratos congelados: ver 08.*
