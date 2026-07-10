# 08 — MOS: Arquitectura completa (V0.85 → V2.0+) — RFCs de diseño

> **Origen**: `FABLE5_PROMPTS/PROMPT_03_MOS_FULL_ARCHITECTURE.md`, con la corrección
> de `PROMPT_05` (Capas 3/4 tienen versión LOCAL siempre disponible) y dos requisitos
> del usuario: **RFC-007 Compactación** (la memoria no puede ser un océano de GB) y
> **RFC-006 Intercambiabilidad tecnológica** (toda capa debe poder cambiar de motor).
>
> Documento de DISEÑO PURO. La implementación de V0.85 está en `07_MOS_V085_DISENO.md`.
> Lo que aquí se define son los contratos y la visión que 07 prefigura.

---

## RFC-001 — Arquitectura general

### El MOS no es una base de datos

Almacena, pero además **entiende** (embeddings + grafo), **conecta** (relaciones y
provenance), **decide qué recordar** (lifecycle RFC-007) y **sobrevive a cualquier
runtime** (los modelos pasan; la memoria pertenece a Aithera). Analogia: Wikipedia
(estructura) + Git (historia) + Linux (modularidad) + un OS (gestiona conocimiento
como el OS gestiona RAM).

### Dos niveles

**Nivel interno** (invisible; 11 componentes): Conversational, Working, Semantic,
Episodic, Knowledge Engine, Decision, Error, Tool, Automation, Skill, Context.
Cada uno con su tecnología de referencia (tabla RFC-006). **Prohibido** el acceso
directo desde Orchestrator/chat/Hermes: todo pasa por el nivel lógico.

**Nivel lógico** (las APIs públicas): 4 capas + sus equivalentes locales (P05):

```
CAPA 1  PRIVATE MEMORY        V0.85   local, aislada por construcción
CAPA 2  PROJECT MEMORY        V1.2+   por-proyecto, permisos granulares (stub antes)
CAPA 3  SKILLS                 ├─ LOCAL: Local Skill Library (V1.1, doc 09) — sin red
                               └─ GLOBAL: Global Skill Network (V2.0+) — extensión opcional
CAPA 4  INTELIGENCIA           ├─ LOCAL: Local Learning Loop (V1.0 básico, doc 09) — sin red
                               └─ GLOBAL: Collective Intelligence Engine (V2.0+) — opcional
```

**Regla de autosuficiencia (P05)**: Aithera sin red = funcionalmente completa para
un usuario. La red solo AMPLIFICA (conocimiento de otros); jamás es prerrequisito.

### Aislamiento arquitectónico de Private Memory (P03 §7.4)

No es un permiso: es topología. Los mecanismos, por construcción:

1. **Direccionalidad de imports**: los módulos de GSN/CIE (V2.0+) viven en un
   paquete `app/network/` que importa SOLO `ISkillStore.export_anonymized()` —
   no existe símbolo importable que devuelva contenido de `mem_personal`.
2. **Export tipado**: lo único que puede salir hacia la red es `PortableSkill`
   (dataclass sin campos libres de texto personal), producido por un
   `PrivacyFilter` que es parte del contrato de export, no un paso opcional.
3. **Guardians sin credenciales locales**: los Guardian runtimes se instancian con
   un `MemoryRouter` capado que solo registra stores de GSN/CIE (inyección de
   dependencias: si no te inyectan el store privado, no puedes leerlo).

## RFC-002 — Las 6 APIs públicas (contratos formales)

Todas son `Protocol`/`ABC` Python; la implementación es intercambiable. Firmas
canónicas (los tipos exactos viven en `app/memory/interfaces.py`, doc 07 §3):

| API | Operaciones | Nace | Notas |
|---|---|---|---|
| **Memory** | `add, search, retrieve, update, delete, context, forget` | V0.85 | = `IMemoryStore` (doc 07) |
| **Decision** | `store_decision, search_decisions, link_outcome, history` | V0.85 (tabla) / V0.9 (uso real) | tabla `decisions` + espejo semántico |
| **Skill** | `create, improve, validate, publish, list, execute` | V0.85 stub → V1.1 completa | `publish` = no-op hasta GSN |
| **Knowledge** | `index(source), retrieve, link, get_graph` | V1.2+ (Cognee) | stub con NotImplementedError |
| **Graph** | `link_entities, find_relations, shortest_path` | V1.2+ (KuzuDB) | stub |
| **Context** | `build_context, compress, summarize` | V0.85 (`context()`) → V1.x (compress) | `compress` usa el lifecycle |

Pre/postcondiciones comunes: toda operación de escritura acepta `dedup_key`
(idempotencia); toda lectura acepta presupuesto (`top_k`, `max_tokens`, timeout);
todo error degrada a valor vacío + log (nunca rompe al caller); toda salida de LLM
interna pasa por `strip_reasoning()`.

## RFC-003 — Guardians (V2.0+)

Agentes que NO trabajan para el usuario: protegen el conocimiento colectivo.
`GuardianRuntime(AgentRuntime)` (contrato de doc 10) con
`capabilities={"validation","deduplication","conflict_detection","provenance_audit"}`.

- **Validan**: spam/duplicados semánticos, skills falsas, malas prácticas, código
  malicioso, fugas de información privada (doble control: PrivacyFilter en origen
  + Guardian en destino).
- **Resuelven contradicciones**: `ConflictReport` → comparación de evidencias →
  prevalece la mejor evidencia o se crean branches A/B con contexto.
- **Aislamiento**: solo ven GSN/CIE (inyección capada, RFC-001). N Guardians
  independientes por aprobación (parámetro de red).

## RFC-004 — Global Skill Network (V2.0+)

Red mundial de conocimiento TÉCNICO reutilizable. Contiene: skills versionadas
(semver), workflows con benchmarks, patrones con evidencia. JAMÁS contiene:
conversaciones, datos personales, nada identificable.

Diseño de plataforma abierta: API pública autenticada + rate limiting; publicación
= `PROPOSED → validación automática → N Guardians → PUBLISHED`; retiro formal
(deprecated → archived, nunca borrado); compatibilidad: minor no rompe contrato;
anticontaminación: provenance obligatorio + evidencia mínima + cuarentena de
instancias con ratio de rechazo alto. Otros asistentes pueden conectarse si
cumplen el protocolo (la GSN no es exclusiva de Aithera).

## RFC-005 — Collective Intelligence Engine (V2.0+)

No almacena: analiza (solo datos anonimizados ya en GSN). Pipeline: detectar que
miles de instancias resuelven lo mismo distinto → comparar estadísticamente →
proponer skill/mejora → Guardians → publicar con provenance. **El CIE propone,
nunca decide.** Su equivalente local (LLL, doc 09) usa los mismos algoritmos
acotados a una instancia — el CIE es el LLL a escala de red.

## RFC-006 — Intercambiabilidad tecnológica (requisito del usuario #2)

**Principio**: cada componente interno declara su motor DETRÁS de una interfaz;
cambiar de motor = escribir un store nuevo + migrar datos + re-mapear el router.
Cero cambios en Orchestrator, chat, Hermes o automatizaciones.

| Componente | V0.85 | Candidato futuro | Interfaz que lo aísla |
|---|---|---|---|
| Vector store | ChromaDB | Qdrant (V1.x) | `IMemoryStore` |
| Working memory | — | Letta (V1.1, interno a HermesRuntime) | detalle del runtime |
| Grafo | — | KuzuDB (V1.2+) | `Graph API` |
| Episódica | — | Graphiti/Zep (V1.2+) | `Memory API (EPISODIC)` |
| Knowledge | — | Cognee (V1.2+) | `Knowledge API` |
| Contexto auto | casero | Mem0 (V1.x) | `Context API` |
| Relacional | PostgreSQL | PostgreSQL | SQLAlchemy (ya aislado) |

**Protocolo de migración sin trauma** (aplica a cualquier swap, p.ej. Chroma→Qdrant):

1. `NewStore(IMemoryStore)` pasa la MISMA suite `test_memory_contracts.py` (los
   tests de contrato son la definición ejecutable de la interfaz).
2. **Dual-write**: el router escribe en ambos stores; lee del viejo (flag
   `MEMORY_BACKEND=chromadb|dual|qdrant` en Settings).
3. **Backfill batch** nocturno del histórico (reusa el patrón del summarizer).
4. **Shadow-read**: N días comparando resultados (log de divergencias > umbral).
5. Flip de lectura al nuevo → periodo de gracia → retirar el viejo.
6. **Rollback**: en cualquier paso, volver el flag atrás. El viejo store nunca se
   borra hasta cerrar el periodo de gracia.

Regla para TODO diseño futuro: si una feature nueva necesita algo que la interfaz
no ofrece, se EXTIENDE la interfaz (método nuevo con default), nunca se accede al
motor por debajo. Las tecnologías de la tabla son candidatas, no compromisos: si
en 2027 aparece algo mejor que Qdrant, cambia la celda, no la arquitectura.

## RFC-007 — Ciclo de vida y compactación (requisito del usuario #1)

**Decisión: SÍ hay compactación, por diseño y desde V0.85 (mínima) → V1.x (completa).**
Sin ella, la ingesta de email/calendario crece sin límite y la búsqueda degrada.
Principio: **la memoria no se borra: se destila.** Detalle pierde resolución con la
edad; el significado se conserva en resúmenes; lo importante se ancla.

### Tiers por edad

```
HOT   (0-30 días)   item completo + embedding            búsqueda directa
WARM  (1-6 meses)   resumen del día/semana + items "anclados"
COLD  (>6 meses)    resumen mensual + decisiones + skills + anclados
ARCHIVE             vault Markdown (%APPDATA%/Aithera/vault/) — legible, fuera de índice
```

### Políticas por tipo (defaults; configurables en Settings)

| Tipo | Compactación |
|---|---|
| `mem_personal` (emails/agenda ingestados) | item→ resumen diario (30d) → semanal (6m) → mensual+archive. **Excepción**: items con `pinned=true` o `category=urgente` respondidos se conservan 1 año |
| `mem_conversational` | igual, con resumen por conversación antes de podar |
| `mem_decision`, `mem_skill` | **NUNCA se compactan** (son el conocimiento destilado; tamaño marginal) |
| `daily/weekly summaries` | los diarios se podan al existir el semanal (>6m); los semanales al existir el mensual (>18m) |
| `mem_error` / `mem_automation` (V0.9+) | detalle 90 días; el patrón extraído (skill/regla) es lo permanente |

### Mecanismos

- **`MemoryLifecycleManager`** (`lifecycle.py`): job nocturno post-summarizer.
  Fases: (1) dedup semántico (similitud > 0.97 mismo tipo → merge conservando
  metadata más rica); (2) roll-up (genera el resumen del nivel superior si falta);
  (3) prune (borra items cuyo resumen superior ya existe, salvo pinned);
  (4) archive (escribe al vault antes de podar COLD). Micro-batch ≤ 500 items/noche.
- **Presupuesto global**: `MEMORY_BUDGET_MB` (default 512). Si se supera, el
  lifecycle aprieta las ventanas (30d→21d...) empezando por el tipo más voluminoso,
  y avisa en el Hub ("memoria compactada al 85% del presupuesto").
- **Trazabilidad de la poda**: cada prune escribe una línea en `MemoryJobRun`
  (cuántos, de qué tipo, a qué resumen fueron). `forget()` del usuario es
  inmediato e incondicional (la transparencia manda sobre la política).
- **En V0.85 se implementa**: dedup + presupuesto + roll-up diario (ya lo hace el
  summarizer). Prune semanal/mensual y archive → V0.9/V1.x (el diseño ya está).

## Mapa de evolución del MOS

| Componente | V0.85 | V0.9 | V1.0 | V1.1 | V1.2 | V2.0+ |
|---|---|---|---|---|---|---|
| Private Memory (Capa 1) | ✅ Chroma | ✅ | ✅ | ✅ | ✅ (+Qdrant opc.) | ✅ nodo aislado |
| Conversational | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Decision | ✅ tabla | ✅ en uso | ✅ +planes | ✅ | ✅ +KuzuDB | ✅ |
| Skill Memory | ✅ stub | ✅ | ✅ | ✅ **LSL completa** | ✅ | ✅ +GSN sync |
| Error / Automation | contrato | ✅ en uso | ✅ | ✅ | ✅ | ✅ |
| Working (Letta) | — | — | — | ✅ en Hermes | ✅ | ✅ |
| Episodic (Graphiti) | — | — | — | — | ✅ | ✅ |
| Knowledge (Cognee) | — | — | — | — | ✅ | ✅ |
| Project Memory (Capa 2) | stub | — | — | — | ✅ | ✅ |
| **LLL (Capa 4 local)** | — | — | ✅ básico | ✅ completo | ✅ | ✅ |
| **LSL (Capa 3 local)** | stub | — | — | ✅ | ✅ | ✅ |
| Lifecycle/compactación | ✅ mínima | ✅ prune | ✅ | ✅ | ✅ | ✅ |
| GSN / CIE / Guardians | — | — | — | — | — | ✅ opcional |

## Riesgos por capa

| Riesgo | Detección | Mitigación |
|---|---|---|
| Crecimiento sin control | `stats` + presupuesto | RFC-007 (compactación) |
| Lock-in tecnológico | tests de contrato por store | RFC-006 (protocolo de swap) |
| Fuga privada → red | Guardian + PrivacyFilter tipado | RFC-001 (aislamiento estructural) |
| Contaminación GSN | provenance + cuarentena | RFC-004 |
| Resúmenes que pierden lo importante | pinned + excepciones por categoría | RFC-007 políticas |
| Latencia en critical path | tests de performance (doc 12 §5) | presupuestos + caché de contexto |

---
*Diseño 2026-07-09 (Fable 5). Los contratos de aquí son los que implementa 07 en
V0.85 y los que consumen 09 (LSL/LLL), 10 (Hermes) y 11 (AE/Orchestrator).*
