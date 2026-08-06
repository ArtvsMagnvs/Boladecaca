# 27 — Plan de Desarrollo V1.0 → V1.5 (dependencias, sesiones, modelos y tests)

> **Estatus**: plan ejecutivo definitivo del tramo V1.0→V1.5. Cada sesión queda
> especificada para que en las sesiones de trabajo NO se decida nada: alcance,
> diseño de referencia, tests obligatorios, criterio de cierre, y **modelo +
> esfuerzo asignado**. De V1.5 a V2.0 el trabajo es AVCS MVP1/MVP2 + GSN + CIE
> (doc 13 §20, doc 08 RFC-004/005; se planificará al cerrar V1.5 con los
> contratos ya revisados en su sesión O5).
>
> **Punto de partida real** (CLAUDE.md, 2026-08-05): **`v1.0.0`** — TIE v1, MEL
> v1, Tools (15/105), Orquestrator R1-R7, auditoría global S1-S11, bloque de
> pulido PU1-PU10, fiabilidad A·B·C y navegación web B·WEB-1/2 + C·WEB-3/4
> CERRADOS. Suite ~1350 tests.
>
> ---
>
> ### ⚠️ REORDENACIÓN DE 2026-08-05 (decisión del usuario) — leer antes que nada
>
> **El MVP-beta (instalador + onboarding + verificación total, sesiones B1-B4)
> se APLAZA de "V1.0 cierre" a V1.5.** Motivo del usuario, literal: *«sé que en
> teoría toca cerrar fase 1.0 con el instalador, pero dado que no tengo usuarios
> beta para testear todavía, voy a continuar desarrollando y cerraremos el
> installer más adelante»*. Empaquetar sin nadie a quien entregar es trabajo que
> caduca: el instalador tendrá que rehacerse igualmente tras V1.1-V1.4 (nuevas
> dependencias, nuevas pantallas de onboarding, nuevos permisos). El tag
> `v1.0.0` YA se puso (2026-08-02, §29 de CLAUDE.md) por el volumen de bloques
> cerrados, así que la versión no queda esperando a nadie.
>
> **Todo el AVCS maduro (MVP1 y MVP2) se traslada a V2.0+.** Génesis —lo que el
> usuario usa a diario— está entregado desde V0.82/83 y se ha seguido puliendo
> (PU5a-g). Lo que queda son los 4 ritmos restantes, los campos maduros y la UI
> orgánica: mejora de una capacidad que YA existe, no una capacidad ausente. Con
> el organismo cognitivo (Learner, MCP, Hermes, red) sin terminar, esas 10
> sesiones de frontend/GPU competían por el sitio equivocado.
>
> **Consecuencia**: V1.6 desaparece como fase. Lo único que tenía de no-AVCS
> (Project Memory Capa 2 + revisión de contratos GSN/CIE, sesión O5) sube a
> V1.5, que pasa a ser la fase de CIERRE del tramo. Nace **V1.4.5**
> (multi-instancia de runtimes), que era la segunda mitad de la vieja sesión A5
> y no tenía nada que ver con el AVCS: depende de Hermes, no de partículas.

---

## 1. Análisis de dependencias (por qué este orden y no otro)

Grafo de dependencias entre los bloques post-V1.0 (→ = "necesita a"):

```
MEL Learning Engine ──────→ model_stats ──→ LEARNER (Mission Learning la puebla)
AutomationLearner ────────→ LEARNER
Skill Evolution ──────────→ LSL completa (LEARNER) + uso real de skills
TIE v2 (olas/replan/missions) → TIE v1 ✅ + sesiones browser por misión ✅ (S3)
TIE v3 "reflexión continua"  → LEARNER (doc 14 ya movió Reflection al Learner)
TIE v3 "routing predictivo"  → MEL Learning Engine
TIE v3 "multi-runtime"       → HERMES (o 2º runtime)
HERMES (H1-H4) ───────────→ LSL completa (LEARNER) + AgentRuntime ✅ + gates ✅
MCP client/server ────────→ ToolManager ✅ (independiente; además AMPLIFICA a Hermes)
AVCS Génesis (Fase 0) ────→ nada del backend (frontend puro) ✅ ENTREGADO en V0.82/83
AVCS MVP1/MVP2 ───────────→ AVCS Génesis ✅   [→ V2.0+, reordenación 2026-08-05]
Multi-instancia runtimes ─→ HERMES (o 2º runtime)  [→ V1.4.5]
Web+PWA+PIN ──────────────→ nada (independiente; mejor tras estabilizar el núcleo)
MVP-beta (instalador) ────→ nada TÉCNICO; depende de que HAYA a quién entregar
GSN/CIE (V2.0) ───────────→ LSL madura + Skill Evolution + contratos revisados
```

**Nota sobre la última línea** (la que movió el plan el 2026-08-05): el
instalador nunca tuvo dependencias técnicas —por eso estaba el primero—, pero sí
tiene una dependencia de PRODUCTO que el grafo no capturaba: sin beta testers no
entrega valor, y sí caduca (cada fase posterior añade dependencias, pantallas de
onboarding y permisos que habría que reempaquetar). Se mueve al final, donde
empaqueta un producto que ya no va a cambiar de forma.

**Tres decisiones estructurales que se derivan del grafo** (delegadas por el usuario):

1. **TIE v3 se DISUELVE como fase.** Sus tres piezas viven donde están sus
   dependencias: reflexión continua → Learner (V1.1); routing predictivo → MEL
   Learning (V1.2); multi-runtime → fase Hermes/V1.5. Mantener "TIE v3" como
   etiqueta habría creado una fase fantasma esperando a otras. TIE v2 SÍ es fase
   real (mejoras mecánicas del executor sin dependencia del Learner).
2. **El Learner sube a V1.1 y Hermes baja a V1.3.** El Learner es el nodo con más
   dependientes (MEL learning, AutomationLearner, Skill Evolution, reflexión,
   y la LSL que Hermes necesita). Hermes, además, se beneficia de que MCP (V1.2)
   ya exista (sus tools = tools de Aithera, incluidas las MCP). Investigación de
   viabilidad: **GO condicional** — `hermes-agent` es paquete Python (0.14.0,
   pip/git), con **pluggable memory providers** (v2026.4.3) que encajan con
   nuestros adapters del doc 10, y proveedores LLM configurables (incluido
   endpoint OpenAI-compatible custom → apuntará al MEL). Integración **GRADUAL**
   (H0 verifica en real; H1-H4 incremental), nunca "de golpe": hay que interceptar
   memoria+tools+LLM y desactivar sus superficies propias, y las garantías de la
   auditoría (grounding, gates, honestidad) deben aplicarse a Hermes igual que al
   toolloop propio. Contingencia si NO-GO intacta (doc 10 §6).
3. **[Corrección 2026-07-22] AVCS Génesis NO necesita recuperarse en V1.1 — ya
   se construyó en V0.82/83.** Este plan (escrito 2026-07-20) asumía, citando
   una nota de CLAUDE.md del sprint W2b, que Génesis seguía sin construir; una
   auditoría de commits (`c457393`…`918138a`, 2026-07-10 a 07-12, ver doc 03
   §2) confirma que el motor GPGPU completo, 3 ritmos reales (Reposo/Escucha/
   Comunicación con audio), Modo Presencia, Chat limpio y PerformanceManager
   Q1-Q4 YA ESTÁN en manos del usuario — la nota de CLAUDE.md comparaba con el
   AVCS *maduro* de MVP1/MVP2, no con esta fase. V1.1 se reduce a Learner
   puro (backend, 4 sesiones); los 4 ritmos que faltan (Comprensión/Acción/
   Error/Recuperación con pesos propios) y los campos maduros siguen siendo
   MVP1/MVP2, en su sitio (V1.5/V1.6) — sin cambios ahí.

## 2. Roadmap resultante (V1.0 → V1.5)

| Fase | Nombre | Sesiones | Por qué aquí |
|---|---|---|---|
| ~~**V1.0 cierre**~~ | ~~MVP-beta (instalador + onboarding + verificación total)~~ → **APLAZADA a V1.5** (§9) | — | **[2026-08-05]** sin beta testers no entrega valor, y caduca con cada fase que añade dependencias/pantallas. El tag `v1.0.0` ya está puesto |
| **V1.1** ⬅ **SIGUIENTE** | Learner operativo | 5 | máximo fan-out de dependencias (AVCS Génesis YA entregado en V0.82/83 — corrección 2026-07-22, ver §1.3). **[2026-08-06]** +1 sesión (L2b, taxonomía de fallos): la atribución tiene que empezar a grabarse YA — datos acumulados sin atribuir valen la mitad |
| **V1.2** | MCP interop + TIE v2 + MEL Learning + Skill Evolution/AutomationLearner + **aprendizaje profundo (Informe de Salud · Torneo de variantes · Erosión de caminos · Exploración en paralelo)** | 10 | consume model_stats (V1.1); MCP prepara a Hermes. **[2026-08-06]** +4 sesiones (ML3/SE1/PE1/PE2, ampliación del usuario): necesitan la infraestructura de esta fase (evals de T2, olas paralelas de T1, taxonomía de L2b) — antes no pueden existir |
| **V1.3** | Hermes Runtime (H0 GO/NO-GO → H1-H4) | 5 | necesita LSL (V1.1) y aprovecha MCP (V1.2) |
| **V1.4** | Red (Web+PWA+PIN) + 2 canales (Discord/WhatsApp) + sandboxing Docker + voz data-driven + UX/memoria legible | 7 | independiente; mejor con el núcleo agéntico ya estable. +3 sesiones de la comparativa competitiva (doc 32 Anexo) |
| **V1.4.5** | Multi-instancia de runtimes por perfil | 1-2 | era la 2.ª mitad de la vieja A5 y no era AVCS: depende de Hermes (V1.3), no de partículas |
| **V1.5** | Project Memory Capa 2 + puerta a GSN/CIE + **cierre MVP con instalador** | 5 | cierra el organismo local Y lo empaqueta cuando ya no va a cambiar de forma; revisa contratos de red para V2.0 |
| **V2.0+** | AVCS MVP1 + MVP2 · GSN + CIE | 10 + ? | **[2026-08-05]** el AVCS maduro mejora una capacidad ENTREGADA (Génesis); la red es otro organismo. Ver §10 |

Total del tramo activo (V1.1 → V1.5): **28-29 sesiones**. Histórico del recuento:
35 → 33 (2026-07-22, AVCS Génesis ya construido: se retiran AV1-AV2 de V1.1) →
36 (2026-07-24, +3 en V1.4 desde la comparativa competitiva: W3 canales, S1
sandboxing, U1 ampliada con memoria legible) → 23-24 activas + 10 aparcadas en
V2.0+ (2026-08-05: MVP-beta aplaza de la cabeza a V1.5, AVCS MVP1/MVP2 sale
del tramo) → **28-29 activas** (2026-08-06: +5 de la ampliación del sistema de
aprendizaje — L2b en V1.1, ML3/SE1/PE1/PE2 en V1.2 — diseño en §5/§6). Reparto
de modelos del tramo activo: Fable 5 ×8 (crítico), Opus 4.8 ×19, Sonnet ×2. Regla de asignación: **Fable = contratos nuevos, concurrencia,
seguridad, GPU delicado** (equivocarse ahí cuesta el doble de arreglar — aquí no
hay economía); **Opus = features sobre patrones ya establecidos**; **Sonnet =
mecánico/UI simple/docs**.

## 3. Estrategia de tests (la lección del Orquestrator, sistematizada)

Los 4 fallos de producción pasaron 751 tests de módulo. La causa: faltaba la capa
de COMPORTAMIENTO en las costuras. Desde ahora, **toda fase cumple la pirámide de
4 capas**, y las capas 3-4 se escriben ANTES de construir:

1. **Unit/módulo** — como siempre (aislamiento, fronteras, lógica pura).
2. **Contratos técnicos** — rutas/API/barrels congelados (patrón `test_email_contracts`).
3. **Contratos de PRODUCTO** (`tests/test_product_contracts.py`, patrón S4):
   comportamiento en las costuras con UN solo fake (la frontera LLM), todo lo
   demás real (ToolManager escribiendo disco, gates reales, BD real de test).
   **Regla nueva: la PRIMERA sesión de cada fase escribe sus contratos de
   producto EN ROJO** (fallan porque la feature no existe) — son la definición
   ejecutable del cierre de fase.
4. **Verificación en vivo** — script aparte contra Postgres/proveedores reales
   (nunca el proceso del usuario), limpieza total confirmada; + al cerrar cada
   fase: **suite completa en Windows** + (desde V1.2) **mission evals** (doc 15
   §9: misiones canónicas de regresión que se corren pre-release).

Reglas permanentes: todo bug de producción entra como test de producto que falla
ANTES del fix (vigente desde S4); un solo fake (LLM); presupuestos de rendimiento
como asserts (patrón `test_tie_perf`); los tests de producto de cada fase se
listan en su sección de abajo — no se improvisan.

---

## 4. ~~V1.0 cierre — MVP-beta~~ → **APLAZADA a V1.5** (decisión 2026-08-05)

> Las 4 sesiones B1-B4 **no se han retirado ni se han rebajado**: se ejecutan
> tal cual están escritas, pero al FINAL del tramo, en **§9 (V1.5)**. Se dejan
> aquí como tumba con puntero para que nadie las dé por perdidas ni las
> reescriba desde cero.
>
> **El razonamiento**, para que no haya que reconstruirlo: el instalador es lo
> único del plan sin dependencias técnicas, y por eso estaba el primero. Pero
> tiene una dependencia de PRODUCTO — beta testers — que hoy no existe, y una
> propiedad que el resto de sesiones no tiene: **caduca**. Cada fase posterior
> añade dependencias que empaquetar (Hermes en V1.3, Docker en V1.4), pantallas
> nuevas de onboarding (proveedores del Learner, servidores MCP, PIN de red) y
> permisos nuevos que enseñar. Empaquetarlo ahora significaría rehacerlo
> después. El tag `v1.0.0` ya está puesto desde el 2026-08-02 (CLAUDE.md §29),
> así que la numeración no queda esperando a nadie.
>
> **Lo que sí conviene NO aplazar de B1**: su primera mitad no es empaquetado,
> es deuda de calidad —la carrera `state=done`/`outcome` del tracer y la suite
> completa en Windows—. Queda anotado en la propia §9 para que se pueda adelantar
> a cualquier hueco entre fases sin arrastrar el instalador con ella.

**Detalle íntegro de B1-B4 → ver §9 (V1.5).**

---

## 4b. Sesiones B1-B4 (texto original, ejecutable donde toque)

### B1 — Verificación total + deudas de cierre · **Opus, esfuerzo alto**
- Alcance: correr la suite completa EN WINDOWS (post S1-S4/optimización) y los 3
  escenarios de aceptación de doc 24 §5 en vivo; arreglar la carrera
  `state=done`/`outcome` del tracer (hallazgo T5: escribir outcome antes de
  `_finalize()` o estado intermedio `synthesizing`); limpiar scripts debug de
  `backend/` raíz; banner `iniciar_app.bat`.
- Tests: los 13 product-contracts existentes verdes en Windows + 1 nuevo:
  `test_outcome_nunca_desfasado` (misión terminada ⇒ outcome coherente al leer).
- Cierre: suite Windows verde, 3 escenarios grabados/anotados en doc 24.

### B2 — Instalador + auto-start · **Fable 5, esfuerzo extra**
- Alcance: electron-builder NSIS empaquetando backend (venv embebido con Python
  portable — pyinstaller DESCARTADO por chromadb/torch); `main.cjs` lanza uvicorn
  (health-wait 20 s, splash, kill on quit, attach si el puerto ya está en uso);
  **decisión Playwright**: Chromium NO va en el instalador — descarga opcional
  post-install desde onboarding ("habilitar navegación web", ~300 MB, con
  progreso); rutas %APPDATA% verificadas; DPAPI intacto tras empaquetar.
- Por qué Fable: arranque/empaquetado es seguridad + un fallo aquí bloquea a
  TODOS los beta testers.
- Tests: `test_product_contracts` += "instalación limpia arranca y responde /health
  en <20 s" (script de humo del instalador, no pytest); checklist manual firmada.

### B3 — Onboarding wizard · **Opus, esfuerzo alto**
- Alcance: primer arranque sin config → wizard: (1) proveedores IA + detección
  Ollama → **auto-políticas MEL** (ya existe el compilador — solo UI del flujo) +
  pantalla-resumen; (2) Google OAuth opcional **con detección de Calendar API
  deshabilitada y guía visual** (el 403 real que sufrimos); (3) Telegram opcional;
  (4) perfil de permisos (manual/balanced/full, A3b); (5) tier visual básico.
  Sin `.env` manual en ningún paso.
- Tests de producto (en rojo al empezar): "backend recién instalado sin .env +
  wizard completado ⇒ chat responde, briefing accesible, 0 excepciones en log".
- Cierre: vídeo del flujo completo en máquina limpia.

### B4 — Beta kit + release · **Sonnet, esfuerzo medio**
- Alcance: logging rotativo, botón "Exportar diagnóstico" (zip de logs+versions
  sin secretos), BETA_README para testers, canal de feedback, bump sincronizado
  `1.0.0` + tag. CLAUDE.md §1 actualizado.

---

## 5. V1.1 — Learner operativo (5 sesiones) → tag `v1.1.0` · ⬅ **FASE ACTIVA**

> **[Ampliación 2026-08-06, decisión del usuario]** Dos ideas rectoras se suman
> al diseño del Learner (detalle y reparto por versión en la nota bajo L2b):
> **(1) un error vale tanto como un éxito** — pero solo si se sabe DE QUIÉN es:
> un fallo de conexión no puede contar como fallo del modelo ni del sistema, y
> un mal razonamiento tiene que quedar atribuido al modelo concreto que lo
> produjo; **(2) los éxitos enseñan CÓMO hacer las cosas** — y tareas similares
> resueltas por caminos distintos hay que diferenciarlas, compararlas y quedarse
> con lo que DEMUESTRA funcionar mejor (nunca con lo que "parece" mejor). De
> aquí nace L2b (V1.1, la atribución — hay que grabarla desde ya) y las 4
> sesiones nuevas de V1.2 (ML3/SE1/PE1/PE2 — el análisis profundo, que necesita
> la infraestructura de esa fase). La fase pasa de 4 a 5 sesiones.

> **[2026-08-05] Ésta es la fase que se empieza ahora**, tras aplazar el
> MVP-beta a V1.5. Punto de partida: `v1.0.0` en `master`, suite ~1350 tests,
> con TODO lo que el Learner necesita ya construido y en producción:
> `mission.completed/failed/cancelled` emitiéndose desde V1.0 T4a ·
> `automation_learner` stub con su interfaz congelada desde V0.9 A4 ·
> `mem_automation`/`mem_error` acumulando rastro real desde A4 · Decision API
> con `history()` desde A4 · `skill_store` + `LocalSkill` con linaje
> (`derived_from`/`superseded_by`) congelados desde V0.85 M1 · telemetría de
> misiones punta a punta desde el bloque de doc 31. El Learner no arranca en
> blanco: nace con meses de datos reales que el sistema lleva guardando a
> propósito para él.
>
> **Orden de ejecución**: L1 (Fable) → L2 → **L2b** → L3 → L4. L1 escribió los
> contratos de producto EN ROJO; L2b añade el 5.º contrato de la fase (fallos
> con dueño); la fase cierra cuando los 5 están en verde (§3).
>
> #### Terreno verificado contra el código (2026-08-05, no contra los docs)
>
> Comprobado con grep sobre `backend/app/` para que L1 no descubra a mitad de
> sesión que una pieza que el plan daba por hecha no está:
>
> | Pieza | Estado REAL | Consecuencia para L1/L2 |
> |---|---|---|
> | `LocalSkill` con linaje | ✅ congelado en `memory/interfaces.py` (`derived_from`/`superseded_by`, provenance idéntica a la GSN). Su propio docstring ya dice: *«la migración a tabla `skills` en V1.1 es un backfill mecánico»* | L1 migra, no diseña |
> | `LocalSkillStore` | ✅ existe, **sobre ChromaDB** (`memory/stores/skill_store.py`): create/get/list/search/improve/validate/publish reales; `execute` en `NotImplementedError` | L1 lleva el ALMACÉN a SQL; `execute` sigue fuera de alcance |
> | `automation_learner` | ✅ stub con las 3 firmas congeladas y `NotImplementedError("V1.2")` | es de V1.2, NO de esta fase — no tocarlo en L1-L4 |
> | Eventos `mission.*` | ✅ emitidos y ya CONSUMIDOS (`tie/conversation.py` se suscribe a `completed`/`failed`) | L2 se suscribe igual; hay un consumidor real de referencia |
> | Decision API `history()` | ✅ `services/decision_service.py` con filtros project/mission_id/status | L2/L3 la usan tal cual |
> | `mem_automation` / `mem_error` | ✅ escribiéndose desde V0.9 A4 | datos reales acumulados para el LLL |
> | **`model_stats`** | ❌ **NO existe como tabla** — solo aparece en comentarios de `mel/models.py` y `mel/contracts.py` apuntando a doc 19 §9.2. Lo que SÍ existe es `mel_executions` (E1) con las señales por ejecución | **L2 la CREA**; es tabla nueva compartida con el MEL, no una que se consuma |
> | `app/learner/` | ❌ no existe | L1 lo crea con barrel + fronteras (doc 16) y lo añade a `test_module_boundaries` |

> **[Corrección 2026-07-22]** Esta fase incluía originalmente una pista
> frontend paralela (AV1 "el motor" + AV2 "ritmos+producto") para construir
> AVCS Génesis, asumiendo que no existía. Auditoría de commits confirmó que
> Génesis (ParticleEngine GPGPU, ShaderSystem, RhythmEngine, semilla+ondas+
> Reposo, ritmos Escucha/Comunicación con audio real, Modo Presencia, Chat
> limpio, PerformanceManager Q1-Q4) se construyó en V0.82/83, 2026-07-10 a
> 07-12 (commits `c457393`, `93b3e8b`, `8f5ad70`, `7b6d376`,
> `6d8b820`/`19adbb4`/`aadb180`, `918138a` — ver doc 03 §2). AV1 y AV2 se
> retiran de este plan; los 4 ritmos que faltan (Comprensión/Acción/Error/
> Recuperación) y los campos maduros siguen en V1.5 (AVCS MVP1, §9), sin
> cambios. V1.1 queda 100% backend.

### ✅ L1 — Contratos del Learner + LSL completa · **Fable 5, extra** — EJECUTADA (2026-08-05)
- Alcance: tabla `skills` + `skill_events` con linaje (docs 09 §1.1, 15 §6.2),
  migración desde el stub `mem_skill` (backfill mecánico), escalera de confianza
  (doc 15 §3: estados y transiciones por evidencia/HITL), API `app/learner/`
  (barrel + fronteras doc 16). **Escribe EN ROJO los product-contracts de la
  fase**: "una misión repetida 3+ veces produce una skill DRAFT"; "ninguna
  propuesta del Learner se aplica sin evidencia o aprobación"; "undo restaura
  el estado anterior"; "el Learner jamás escribe fuera de sus tablas/colecciones".
- Por qué Fable: estos contratos gobiernan V1.1→V2.0 (la GSN hereda LocalSkill).

> **✅ Cierre L1 (2026-08-05, Fable 5).** Módulo `app/learner/` NUEVO (6 archivos
> + barrel), migración 26.ª `a8b9c0d1e2f3` (3 tablas, idempotente), cableado en
> el lifespan (import de modelos + backfill en background).
>
> **Decisiones de diseño que L2-L4 heredan** (para no re-decidirlas):
> 1. **SQL manda, ChromaDB espeja** — la tabla `skills` es la fuente de verdad
>    y `mem_skill` su espejo semántico best-effort, el MISMO reparto que
>    `decisions`/`mem_decision` lleva un año haciendo. El espejo se escribe por
>    la API PÚBLICA del MOS (`skill_store.create`, que upserta por dedup_key) —
>    un solo serializador, cero imports a internos ajenos.
> 2. **Una sola escalera, dos vestidos** — las skills NO usan
>    `learner_proposals`: su propio `SkillStatus` ES su escalera (mapeo
>    documentado en `ladder.py`: DRAFT=proposed, VALIDATED=validated,
>    LOCAL=consolidated). La cuarentena general (`LearnerProposal`) es para el
>    aprendizaje no-skill (preferencias, pins, reglas) y las operaciones de
>    evolución de V1.2. Dos maquinarias para el mismo camino habría sido
>    frameworkitis.
> 3. **La política de validación vive en UN sitio** — `ladder.py`, funciones
>    puras y fail-closed: riesgo alto = SIEMPRE HITL (50 evidencias automáticas
>    no lo mueven, con test); riesgo medio = 3 ejecuciones OK reales o el
>    usuario; riesgo bajo = 5 contextos distintos y CERO contradicciones (una
>    sola para la auto-ruta en seco); una racha en la MISMA misión cuenta como
>    UN contexto; y "el LLM dijo que salió bien" se rechaza EN LA PUERTA
>    (`EXTERNAL_SIGNAL_KINDS` — anti-contaminación §3.3 como código, no como
>    intención).
> 4. **El undo es historia, no goma de borrar** — cada transición guarda el
>    snapshot COMPLETO previo en su `SkillEvent` (snapshot y no diff: restaura
>    en una operación, no puede corromperse por un eslabón perdido) y el propio
>    undo deja su evento `reverted`. Un test de INVARIANTE exige que el snapshot
>    cubra todas las columnas mutables del modelo — y CAZÓ su primera
>    discrepancia al escribirse (`created_by`, resuelta declarándola inmutable
>    por contrato: la provenance no cambia nunca).
> 5. **Appliers registrables** (patrón del registro de ejecutores del gate):
>    `proposals.py` no sabe escribir preferencias ni reglas — cada kind registra
>    su applier (L2/L4) que devuelve el snapshot previo para el undo. L1
>    registra el real de `skill_new`: consolidar crea la skill EN DRAFT (nace en
>    SU cuarentena, nunca validada); su undo la depreca — jamás borra.
> 6. **La lección de las 4 veces, institucionalizada**: test de invariante que
>    exige que CADA columna del ORM del Learner aparezca por nombre en la
>    migración (el desfase ORM↔migración que rompió la app en Postgres 4 veces).
>
> Los 4 product-contracts (`tests/test_product_learner.py`): **nº 1 EN ROJO**
> (xfail ESTRICTO sobre la firma congelada `analyze_repeated_missions` — cuando
> L2/L3 lo implementen, el xfail revienta la suite y obliga a retirar la marca:
> el flip a verde es un acto deliberado); **nº 2, 3 y 4 EN VERDE desde L1** (la
> escalera, el undo y la frontera — el nº 4 con DOS mitades: inspección estática
> de imports prohibidos Y un diff de conteos de TODAS las tablas alrededor de un
> apply real). Tests: `test_learner_lsl.py` (35) + `test_product_learner.py` (6).
> **Comprobación de mutación** (4, restauradas y verificadas byte a byte):
> desactivar la escalera en validate() tumba 2; desactivar la restauración del
> undo tumba 1; autovalidar el riesgo alto tumba 2; hacer que el applier escriba
> en una tabla AJENA (`decisions`) lo caza el diff de BD del contrato 4b.
> Regresión: **112 passed, 1 xfailed** (learner + boundaries + memory_contracts +
> migracion + smoke + product_contracts + automation_mos + cweb4), cero rotos;
> el único fallo visto en la pasada amplia (`test_import_app_main`, presupuesto
> de 2 s) es el flake de entorno documentado desde T5 — verificado que
> `app.learner` NI SE CARGA en el import (va dentro del lifespan).
> **Pendiente en Windows**: `cd backend && alembic upgrade head` (migración
> 26.ª — verás `Running upgrade f7a8b9c0d1e2 -> a8b9c0d1e2f3`), reiniciar el
> backend y comprobar en el log que no hay aviso de `check_schema_drift`.

### ✅ L2 — Mission Learning · **Opus, alto** — EJECUTADA (2026-08-05)
- Alcance: suscripción a `mission.completed` → job post-misión asíncrono (doc 15
  §4): agrega a `model_stats` (tabla compartida con MEL — doc 19 §9.2), registra
  decisiones/pins, propone skills candidatas (DRAFT + cuarentena). Capability
  `ANALYZE` vía MEL (nunca ai_manager).
- Tests: producto L1 en verde parcial + unit del agregador; verificación en vivo
  con 3 misiones reales.

> **✅ Cierre L2 (2026-08-05, Opus).** `mission_learning.py` + `stats.py` nuevos,
> migración 27.ª `b9c0d1e2f3a4` (`model_stats` + `tool_stats`), suscripción al
> bus en el lifespan. Tres salidas concretas por misión, ninguna decorativa:
>
> 1. **Contadores** (determinista, 0 LLM, SIEMPRE — también en la charla).
> 2. **Reflexión** de 2-4 líneas → Decision API con `mission_id` (el delta #2 de
>    doc 14 §4.1 existía justo para esto). Solo en misiones no triviales.
> 3. **Candidato a skill** → propuesta que ACUMULA EVIDENCIA.
>
> **LA DECISIÓN QUE HACE ESTO ÚTIL Y NO TEATRO**: el punto 3 no crea una skill
> por misión — eso sería la "proliferación de skills-basura" que doc 15 §10 teme.
> Crea UNA propuesta por tipo de trabajo y le suma una evidencia cada vez que ese
> trabajo se repite; **la escalera de L1 hace el resto sola**: a las MIN_REP=3
> misiones DISTINTAS sube a `candidate`. Es "una misión repetida 3 veces produce
> un candidato" implementado por ACUMULACIÓN en vez de por una pasada de
> clustering — y sin gastar un LLM extra en las repeticiones. Y hereda gratis la
> protección contra rachas: el `context_key` es el `mission_id`, así que tres
> entregas del mismo evento cuentan como un solo contexto (test dedicado).
>
> **`model_stats` mide lo que ninguna métrica de transporte puede medir**: no
> "¿respondió el modelo?" sino "¿sirvió la misión?". `mel_executions` ya tenía lo
> operativo (200 OK, latencia, coste); un modelo puede devolver 200 OK y una
> respuesta inútil — la llamada un éxito y la misión un fracaso. El ranking
> ordena por tasa de éxito de MISIÓN, no por latencia (test que lo fija). Es la
> señal que el Model Router necesita en V1.2.
>
> **Coste bajo control** (doc 15 §10, "coste silencioso"): 0 LLM en el camino
> corto —reflexionar sobre "¿qué hora es?" es reflection theater—, 1 llamada
> ANALYZE con `policy_override="economy"` (Ollama primero) en el resto, plazo
> duro `LEARNER_REFLECTION_BUDGET_S` (20 s) tras el cual la misión se queda con
> sus contadores, y ring anti-duplicado porque el bus es best-effort. De una
> misión FALLIDA se reflexiona (es la señal más valiosa) pero NO se propone
> convertirla en procedimiento: sería enseñar a fallar.
>
> **`tracer.mission_snapshot()` (accesor NUEVO en el TIE)**: el Learner necesita
> las trazas —su fuente de aprendizaje nº 1 (doc 15 §2)— pero leerlas por SQL lo
> habría acoplado a un esquema ajeno. El TIE expone un accesor de lectura pura y
> controla su propia superficie. En consecuencia, **el contrato de producto nº 4
> se AFINÓ, no se debilitó**: `app.tie` deja de estar vetado en bloque y pasa a
> tener su propia regla, más estricta en lo que importa — solo el barrel, solo
> `tracer` y `extract_json`, y un test que reviente si alguien importa
> `submit_mission` "para reintentar una misión fallida". El invariante real de
> doc 15 nunca fue "no mirar al TIE": era **nunca planificar, nunca ejecutar**.
>
> **HALLAZGO REAL, y lo destapó el test que escribí para ello**: la primera
> versión de la firma de trabajo era un hash sha1 de "las 6 palabras más largas"
> — exacto, barato y ROTO. Dos redacciones naturales del mismo encargo
> («prepárame el resumen semanal del proyecto X» / «por favor, quiero el resumen
> semanal para el proyecto X») daban hashes distintos porque una cortesía larga
> desplazaba a una palabra de contenido del top 6. Un hash exacto sobre texto
> libre es frágil por construcción. Sustituido por comparación de CONJUNTOS
> (Jaccard ≥ 0.5 + mismas tools), que sigue costando microsegundos porque solo se
> compara contra las propuestas abiertas. Segundo hallazgo menor: mi propio test
> de la frontera no descartaba el comentario de la línea y leía el texto del
> comentario como si fuera un símbolo importado.
>
> Tests: `test_learner_mission.py` (NUEVO, 29 — similitud de trabajo con sus
> negativos, agregación incremental, el ranking por éxito de misión, 0 LLM en la
> charla, exactamente 1 llamada en lo demás, capability+política verificadas,
> plazo duro, anti-duplicado, JSON basura, reflexión enlazada, **una misión no
> crea una skill**, **tres misiones distintas sí suben a candidata**, tres
> entregas de la misma no, misión fallida no propone procedimiento, sin tools no
> hay procedimiento, el bus real disparando el aprendizaje, y el accesor nuevo
> contra el tracer REAL). **Comprobación de mutación** (4, restauradas y
> verificadas byte a byte): quitar la exención de la charla tumba 1; contar toda
> misión como éxito tumba 2; crear una propuesta por misión tumba 1; aprender de
> las fallidas tumba 1. Regresión: **91 + 101 + 106 passed** en los subconjuntos
> learner/boundaries/migración/smoke, tie/telemetría/product_contracts/
> automation/memory, y e2e/perf/orquestador/cweb4/agentes — cero rotos. Arranque
> intacto (2,2 s; `app.learner` NO se carga en el import de `app.main`).
>
> **Pendiente en Windows**: `cd backend && alembic upgrade head` (ahora son DOS
> migraciones, `a8b9c0d1e2f3` de L1 y `b9c0d1e2f3a4` de L2), reiniciar el backend
> y lanzar 3 misiones reales — luego mirar `model_stats`/`tool_stats` en la BD y
> las reflexiones en `decisions` (filtrando por `mission_id`).

### ✅ L2b — Taxonomía y atribución de fallos + stats justas · **Opus, alto** — EJECUTADA (2026-08-06)

> **Cierre L2b (2026-08-06, Opus)** — un fallo ya tiene dueño.
>
> **Lo construido, tal como se especificó**: `app/core/failures.py` (13
> `FailureKind` congelados + eje `blame` + `classify_failure` determinista, 0
> LLM) · los 6 enganches sobre eventos que YA existían (aditivos: solo se añade
> `failure_kind`/`blame` al `detail`) · tabla `failure_stats` + migración 27.ª
> `c0d1e2f3a4b5` encadenada tras la de L2 · `missions_excused`/`fails_external`
> · `config_gaps` + propuestas `config_fix` sin applier · el contrato de
> producto nº 5 de la fase EN VERDE.
>
> **Tres desviaciones sobre el diseño, todas hacia arriba y razonadas**:
> **(1) `provider_auth` pasa de culpa "external" a "config"** — un 401 es "tu
> API key está mal", algo que el usuario arregla en dos clics; con "external"
> el panel lo habría enterrado bajo "no es culpa de Aithera" y jamás habría
> generado una propuesta accionable. En consecuencia `config_gaps` filtra por
> CULPA y no por un kind concreto, así que un kind nuevo con esa misma culpa
> queda cubierto sin tocar nada. **(2) El orden de clasificación pone LO
> NUESTRO primero**: un traceback propio que arrastre la palabra "connection"
> se clasifica como `system_bug`, no como red — si no, quedaría excusado y
> desaparecería de las stats para siempre; al revés solo cuesta una revisión de
> más. **(3) `user_question` deja de ser un fallo**: pasa por el mismo funnel
> de telemetría (se graba con ok=False) pero `kind_from_loop_event` devuelve
> `None` y `annotate` lo deja intacto — si no, el panel de Salud contaría
> preguntas como averías.
>
> **DOS BUGS REALES encontrados por los tests, ninguno visible leyendo el
> código.** **(a) `record_failures` creaba una fila por repetición en vez de
> incrementar el contador**: `SessionLocal` va con `autoflush=False` (patrón
> estándar del proyecto), así que la fila recién añadida NO era visible para el
> `query` de la vuelta siguiente. Efecto: todas las filas atascadas en
> `count=1`, el umbral de ≥3 nunca alcanzado y **la propuesta `config_fix`
> muerta en silencio** — la feature entera habría estado presente y sin
> funcionar. **(b) `fails_external` se contaba por tool y no por `tool.action`**,
> así que `search.search_web` y `search.search_news` se sumaban mutuamente sus
> fallos externos y el contador podía superar al total de fallos.
>
> **Y un fallo de mi propia corrección, cazado por su test**: al arreglar el
> componente para que una tool INVENTADA no creara una fila
> `tool:<alucinación>`, la primera versión se pasó de frenada y mandaba también
> los `config_missing` a `tie:toolloop` — perdiendo el nombre de la herramienta,
> que es justo lo que hace accionable el aviso ("falta la API key de search"
> sirve; "algo del bucle de herramientas" no). La regla quedó en una sola:
> **si la culpa es del modelo, el componente jamás es una tool**; el resto sí
> la nombra.
>
> Tests: `tests/test_learner_failures.py` NUEVO (**49** — taxonomía con
> mensajes REALES del proyecto incluida la traducción completa del vocabulario
> del MEL, los 6 enganches verificando que el kind LLEGA al payload —no solo
> que la función clasifica bien: la lección "correcto pero desconectado" de
> S9b/S9c—, el contrato nº 5 con su contrario, el doble conteo, el ring de
> ejemplos acotado, `config_fix` a las 3 y no a las 2, y el invariante
> ORM↔migración extendido a las tres tablas). **Comprobación de mutación** (4,
> restauradas y verificadas byte a byte con `cmp`): quitar la exención tumba el
> contrato de producto; desconectar el enganche del toolloop tumba 1; devolver
> el componente a la etapa tumba 1; quitar el índice anti-`autoflush` tumba 3.
> Regresión: **440 passed** en tres lotes (learner/boundaries/migración/
> telemetría · tie/toolloop/planner/executor/auditorías · mel/orquestador/
> product_contracts/arranque), cero rotos. Arranque intacto: la taxonomía se
> importa de forma diferida en los 6 enganches, así que `app.main` no la carga.
>
> **Pendiente en Windows**: `cd backend && alembic upgrade head` (ahora son
> TRES migraciones del Learner: `a8b9c0d1e2f3` de L1, `b9c0d1e2f3a4` de L2 y
> `c0d1e2f3a4b5` de L2b), reiniciar y provocar dos fallos reales de distinto
> tipo — uno de red (desconectar y mandar un mensaje) y otro de configuración
> (una búsqueda web sin API key, repetida 3 veces) — para confirmar en la BD
> que `failure_stats` los separa, que `model_stats.missions_excused` sube con
> el de red, y que aparece una propuesta `config_fix` con su pestaña de Ajustes.

#### Especificación original (para referencia)

**El porqué**: hoy un fallo se GRABA (mem_error, telemetría, `automation_executions`)
pero no se ATRIBUYE. "La misión falló" puede significar que se cayó la conexión,
que faltaba una API key, que el modelo razonó mal, que el planner asignó mal las
tools, o que hay un bug en el propio código de Aithera — y para el aprendizaje
son cinco cosas COMPLETAMENTE distintas. Sin atribución, `model_stats` (L2)
castiga a un modelo por un timeout de red, y el análisis de patrones de L3
mezcla peras con manzanas. Esta sesión pone el dueño a cada fallo, de forma
**DETERMINISTA** (el código en el punto del fallo ya SABE qué pasó — pedirle a
un LLM que adivine la culpa sería violar la anti-contaminación de doc 15 §3.3;
el LLM solo entra después, en L3/ML3, para analizar fallos YA atribuidos).

**1 · La taxonomía** — `app/core/failures.py` (NUEVO). Vive en `core/` y no en
`app/learner/` porque los ESCRITORES son MEL/toolloop/executor/planner y no
pueden importar internos del Learner (mismo criterio que llevó `grounding.py` a
core en S2·S6). Contenido:
- `FailureKind` (enum congelado, append-only — mismo régimen que `MemoryType`):
  `connection` (red/DNS/timeout/5xx) · `provider_auth` (401/403/key inválida) ·
  `provider_limit` (rate limit/cuota) · `config_missing` (preflight: sin API key
  de búsqueda, Calendar API deshabilitada, Telegram sin token…) ·
  `external_content` (muro de cookies irresoluble, captcha, página bloqueada) ·
  `tool_error` (la tool corrió y falló por causa propia) · `model_reasoning`
  (rendición NEW-4, answer rechazado por grounding A-1, atasco Sesión A) ·
  `model_format` (JSON inválido del clasificador/planner/toolloop) · `planning`
  (PlanRejection, grafo inválido tras reintento) · `system_bug` (excepción no
  controlada de código Aithera) · `permission_denied` (gate rechazado — NO es
  un error: es el usuario mandando) · `user_cancelled` (kill-switch) · `unknown`.
- `blame_of(kind) -> str` — mapeo FIJO en código, un solo sitio:
  `external` ← connection/provider_auth/provider_limit/external_content ·
  `config` ← config_missing · `model` ← model_reasoning/model_format ·
  `tool` ← tool_error · `aithera` ← planning/system_bug · `none` ←
  permission_denied/user_cancelled · `unknown` ← unknown (bucket propio y
  VISIBLE en el panel — lo que no se sabe atribuir no puede esconderse).
- `classify_failure(source: str, error_text: str, extra: dict) -> FailureKind` —
  funciones puras, 0 LLM, patrones sobre los MENSAJES DE ERROR REALES del
  proyecto (getaddrinfo failed, TargetClosedError, "sin ejecutor", los textos
  del preflight…). Los tests se escriben con mensajes recolectados de
  `mem_error`/logs reales, no inventados.

**2 · Los 6 puntos de enganche** (cada uno ya emite/graba — solo se AÑADE el
kind al payload, aditivo, cero eventos nuevos):
1. `mel/executor.py::_record_async` — la razón del breaker (`fallback.py` ya
   clasifica transient/timeout/auth por llamada) se mapea a FailureKind y viaja
   en el evento de telemetría de cada llamada LLM.
2. `tie/toolloop.py` — al registrar un fallo de tool (donde hoy nace la firma
   de S9c) se clasifica el error; el kind va en el evento de tool de telemetría.
3. `tie/executor.py::_validate_result` — rendición/grounding → `model_reasoning`
   con el `provider:model` del nodo (la telemetría ya sabe cuál corrió).
4. `tie/planner.py` — PlanRejection / grafo inválido tras el reintento →
   `planning`.
5. preflight (doc 40 Sesión A) — `preflight_not_ready` → `config_missing`
   (el mensaje accionable del preflight se conserva ÍNTEGRO: es la semilla de
   la propuesta `config_fix`, ver punto 5).
6. `tie/executor.py`/`automation/engine.py` — excepción no controlada →
   `system_bug` (solo el NOMBRE de la excepción + 200 chars del mensaje en la
   metadata, jamás el traceback completo).

**3 · Almacenamiento** (tres capas, todas aditivas):
(a) los payloads de eventos de telemetría ganan `failure_kind`/`blame`;
(b) la metadata de `mem_error` gana los mismos campos + `model_key`/`tool`;
(c) tabla nueva **`failure_stats`** en `app/learner/models.py` (patrón exacto de
`ModelStat`): `id, kind (ix), blame, component` (`tie|mel|orchestrator|
tool:<id>|model:<provider:model>|email|calendar|...`), `model_key` nullable,
`tool` nullable, `count, last_seen, sample_mission_ids JSON` (ring de 10, para
que el panel enlace a misiones reales), `updated_at`. La escribe
`mission_learning._learn` al agregar cada misión (los contadores por fallo
individual salen del timeline, que ya trae todos los eventos). **Migración
NUEVA encadenada tras `b9c0d1e2f3a4`** — jamás editar una aplicada (la lección
del segundo round, §27 de CLAUDE.md) — con el test de invariante ORM↔migración
de L1 extendido a la tabla nueva.

**4 · Stats JUSTAS** (la petición literal: "que los fallos de conexión no
cuenten como errores del sistema"): `mission_learning._learn` calcula el
`dominant_kind` de una misión fallida — el kind del fallo FATAL (el del último
nodo/llamada que tumbó la misión); a igualdad, prioridad `system_bug > planning
> model_* > tool_error > config_missing > external` (lo interno pesa más que lo
externo: ante la duda, la culpa se la queda casa). Con `blame(dominant_kind) ∈
{external, config, none}`: `ModelStat.missions_excused += 1` (columna nueva,
misma migración) y la misión SALE del denominador — la fórmula de
`model_ranking()` pasa a `mission_success_rate = missions_ok / (missions −
missions_excused)`. `ToolStat` gana `fails_external` con el mismo criterio (un
timeout de red dentro de una tool no es culpa de la tool). La reflexión de L2
(`_reflect`) añade UNA línea al resumen con el kind dominante — coste ~0.

**5 · Primera consecuencia accionable — propuestas `config_fix` (0 LLM)**: si
`failure_stats` acumula ≥3 fallos del MISMO `config_missing` (misma
configuración ausente, dedup por el texto del preflight), nace una
`learner_proposals kind="config_fix"` con el texto EXACTO de qué configurar y
un deep-link a la pestaña de Ajustes correspondiente (patrón `location.state
.tab` ya usado por el banner local-only, §25 CLAUDE.md). **SIN applier
registrado** — no hay nada que auto-aplicar: configurar es del usuario; el
panel (L4) la muestra con el botón "Ir a Ajustes" en vez de "Aceptar".
Con 2 repeticiones NO nace (el umbral 3 de siempre).

**Contrato de producto nº 5 de la fase** (nace con esta sesión, EN VERDE al
cerrarla): *"un fallo de conexión jamás cuenta como fallo del modelo ni del
sistema"* — test de producto real: misión que falla por `getaddrinfo` simulado
→ `model_stats` del modelo implicado queda con `missions_excused=1` y su
`mission_success_rate` intacto.

**Tests** (además del contrato): taxonomía pura con mensajes reales (≥15 casos,
incluidos los ambiguos); los 6 enganches (unit por punto, verificando que el
kind LLEGA al payload — no solo que la función clasifica bien: la lección
"correcto pero desconectado" de S9b/S9c, tres veces ya); dominant_kind con
prioridades; fairness (mutación obligada: quitar la exención tumba el
contrato); config_fix a las 3 y no a las 2 (mutación: quitar el umbral);
`failure_stats` con ring de ejemplos acotado a 10.

### ✅ L3 — LLL análisis 1-5 + `/learn` · **Opus, alto** — EJECUTADA (2026-08-06)

> **Cierre L3 (2026-08-06, Opus)** — el Learner deja de mirar solo el momento.
>
> **La diferencia que justifica la sesión**: L2 mira UNA misión cuando termina
> y solo ve lo obvio. `app/learner/analysis.py` mira SEMANAS de golpe, de
> madrugada y sin prisa, y ve lo que ninguna misión suelta enseña — que un
> encargo se repite, que un fallo lleva un mes ocurriendo, que un procedimiento
> sirve en dos proyectos.
>
> **Los cinco análisis, con lo que los datos REALES dan de sí**: **(1)
> repetidas** — agrupa por trabajo (mismo `same_work` de L2) y deja una
> candidata en cuarentena; NO duplica lo que L2 ya propuso: le suma la
> evidencia que falte y la escalera de L1 hace el resto. Nace **sin pasos** a
> propósito: unos pasos redactados por un LLM que nadie ha visto funcionar son
> la fábrica de basura de doc 15 §10. **(2) errores** — sobre `failure_stats`
> YA ATRIBUIDA (L2b), nunca sobre `mem_error` en crudo; lo accionable
> (configuración) se propone, y lo demás va al informe porque no hay nada que
> el usuario pueda aceptar ahí. **(3) inter-proyecto** — el mismo trabajo en ≥2
> proyectos deja de ser de uno; para que tuviera datos, `mission_snapshot` y la
> evidencia de L2 ganan el `project_id` (un dato que no se guarda cuando se
> tiene no se recupera después). **(4) calidad** — `quality_score`/`error_rate`
> deterministas desde `skill_events`. **(5) informe semanal** — determinista,
> más la AUTOPSIA: la ÚNICA llamada al LLM de todo el archivo, con el modelo
> más fiable (ANALYZE + policy quality), una vez por semana. Un hallazgo sin
> evidencia enlazada se descarta (misma disciplina que el grounding), y sin
> fallos que analizar no se llama a nadie.
>
> **`/learn`** (`app/learner/authoring.py` + acción `aithera.learn_skill`): el
> usuario dice «aprende esto» y unas notas se convierten en un procedimiento.
> Se implementa como ACCIÓN DE TOOL y no como intercepción del chat — el
> clasificador ya enruta la auto-operación a `aithera`, así que no hace falta
> acoplar el TIE al Learner ni meter nada en el camino caliente. Y entra por la
> MISMA puerta que lo observado: `status=DRAFT`, misma escalera, mismo panel.
> Que lo pida el usuario no lo hace verdad — pide el TEMA, no certifica el
> RESULTADO, y lo que se guarda lo redacta un modelo. `created_by="user_taught"`
> deja la provenance a la vista. Hereda el proyecto de la misión por el mismo
> mecanismo que `create_agent` (el `project_id` lo pone el bucle desde la
> autoridad, no la memoria del modelo).
>
> **Job nocturno**: 04:45 local, el ÚLTIMO — analiza lo que los jobs del MOS y
> la limpieza del TIE acaban de dejar ordenado. El informe se decide por fecha
> del último y no por día de la semana: si la app estuvo apagada el lunes, sale
> el primer día que se encienda.
>
> **Contrato de producto nº 1 EN VERDE**: el xfail estricto de L1 hizo
> exactamente su trabajo — al implementarse dejó de lanzar, reventó la suite y
> obligó a venir a retirar la marca. Se reescribió sembrando tres misiones
> reales (el mismo encargo dicho de tres formas) en vez de llamar al análisis
> sobre una BD vacía, que era lo que el cuerpo de L1 describía sin poder hacer.
>
> **HALLAZGO DE DISEÑO real, cazado por su test**: el peso por recencia de
> `quality_score` **se cancelaba en la proporción** — con un único evento
> `peso_ok == peso_total` y el ratio vale 1.0 tenga la edad que tenga, así que
> una skill de hace seis meses puntuaba IGUAL que la de hoy. El decaimiento
> estaba escrito, documentado… y no hacía nada. Corregido con un factor de
> frescura sobre el último éxito, que es además la forma en que las skills se
> estropean de verdad: el mundo cambia debajo y ellas ni se enteran.
>
> **Y un fallo en mis propios tests**, encontrado por la mutación: el test de
> «si el modelo no lo ve claro no se guarda nada» mandaba `confident:false`
> JUNTO a una lista de pasos vacía, así que lo rechazaba el OTRO guard —
> desactivar la comprobación de la bandera pasaba con 33 tests en verde.
> Endurecido a lo que el modelo hace de verdad: dudar y rellenar el hueco
> igualmente.
>
> **La frontera con V1.2, respetada**: proponer mejoras de SKILLS es ML2 y
> proponer mejoras del SISTEMA es ML3. L3 ve cosas que no puede proponer
> todavía; van al informe como hallazgo, nunca a la bandeja como propuesta.
>
> Tests: `tests/test_learner_analysis.py` NUEVO (**33**) + el contrato nº 1
> reescrito. 4 mutaciones confirmadas y restauradas byte a byte (umbral de
> repeticiones, frescura, `confident`, DRAFT). La frontera modular cazó de paso
> que `aithera_tool` importaba el interno `app.learner.authoring` en vez del
> barrel. Regresión: **387 passed** en dos lotes (learner/boundaries/migración/
> telemetría/arranque · tie/toolloop/executor/agentes/product_contracts), cero
> rotos.
>
> **Pendiente en Windows**: reiniciar y (a) decirle por chat «aprende esto: …»
> con unos pasos reales, confirmando que aparece un borrador; (b) forzar la
> pasada nocturna a mano (`from app.learner import run_nightly_analysis`) tras
> unas cuantas misiones y mirar el informe en `Config` bajo
> `learner.weekly_report`.

#### Especificación original (para referencia)

### L3 — LLL análisis 2-5 · **Opus, alto**
- Alcance: patrones de error (mem_error), skills transferibles entre proyectos
  (WPMS tags), calidad de skills (quality_score/error_rate), briefing semanal de
  aprendizaje (doc 09 §2.2). Jobs APScheduler idle, micro-batch ≤50.
- **[Ampliación 2026-08-06] El análisis 2 consume la ATRIBUCIÓN de L2b**: los
  patrones se buscan POR `failure_kind` (no sobre la sopa entera de mem_error) —
  "3 fallos `model_format` del mismo modelo en el clasificador" y "3 timeouts
  de red" son patrones distintos con salidas distintas. La **autopsia semanal**
  (dentro del briefing de aprendizaje que ya estaba en el alcance) se hace con
  los modelos MÁS FIABLES — `mel.complete(capability=ANALYZE,
  policy_override="quality")`, 1 llamada semanal grande, batch nocturno idle:
  ahí el coste de calidad se lo puede permitir — y produce: (a) más propuestas
  `config_fix` que el umbral determinista de L2b no cazó, (b) candidatos a
  "skill preventiva" (par error→solución repetido ≥3, doc 15 §4), (c) los
  hallazgos del briefing. **Frontera deliberada, para que no haya solape**: las
  propuestas de MEJORA de skills (Improve/merge/split) son de ML2 (V1.2), las
  de mejora del SISTEMA son de ML3 (V1.2) — L3 no las adelanta; lo que L3 ve y
  no puede proponer todavía se guarda como hallazgo en el briefing.
- **[Comparativa competitiva 2026-07-24, doc 32 Anexo] `/learn`-style skill
  authoring (idea de Hermes Agent)**: la redacción de una skill DRAFT no tiene
  por qué ser 100% automática desde traces — se añade la vía de que el usuario
  invoque "aprende esto" pasando una conversación/URL/notas y el propio agente
  investigue y escriba un `SKILL.md` conforme al estándar (Hermes lo hace con su
  comando `/learn`). Encaja en el LLL como una FUENTE más de skills DRAFT (misma
  cuarentena, mismo linaje, misma revisión HITL del panel L4) — no un pivote,
  una entrada adicional. Detalle de diseño también en doc 09 (LSL/LLL) §skills.
- Tests: unit por análisis con fixtures deterministas; "un error repetido 3×
  genera propuesta" (producto); "`/learn` desde notas produce un `SKILL.md`
  válido en cuarentena, nunca activo directo".

### ✅ E2E del Learner completo (L1+L2+L2b+L3) — 2026-08-06, Opus

> **Petición del usuario tras cerrar L3**: nada de testeos aislados de
> funciones — una simulación REAL del Learner haciendo aquello para lo que se
> creó, con todo el conjunto involucrado.
>
> **`tests/test_learner_e2e.py` NUEVO (12)**: se simula una semana de trabajo y
> se recorre la cadena entera sin atajos — misión real → traza real
> (`tracer.record_start/plan/end`) → telemetría por los HOOKS DE PRODUCCIÓN
> (`mel._record_async`, `toolloop._record_loop_event`: la atribución la produce
> el código de verdad, no el test) → evento real del bus → el handler REAL del
> Learner → contadores, atribución, reflexión y candidata → escalera de L1 →
> análisis nocturno de L3 → informe → el usuario acepta → se aplica → se
> arrepiente → se deshace. **UN SOLO DOBLE: la frontera del LLM.** La BD, el
> bus, el tracer, la cuarentena, la biblioteca y las stats son las reales.
>
> **DOS BUGS DE PRODUCCIÓN que ningún test unitario podía ver.**
>
> **(1) `mission_snapshot` devolvía SIEMPRE `nodes: []`** — `TaskGraph.nodes`
> es un dict y se iteraba a secas, recorriendo las CLAVES: el primer `n.id`
> lanzaba `AttributeError`, lo tragaba el `except` de al lado, y el snapshot
> salía vacío. Consecuencia: `_accumulate_candidate` deriva las herramientas de
> ahí y corta si no hay ninguna, así que **NINGUNA misión real llegó jamás a
> producir una skill candidata** desde que L2 se entregó. Media sesión L2 era
> código muerto y estaba en verde. Los unitarios no podían verlo porque
> construían el snapshot a mano en lugar de pasar por el accesor.
>
> **(2) `record_failures` perdía cuentas con misiones concurrentes** — el
> incremento era un read-modify-write en Python, así que dos misiones que
> fallan por lo mismo casi a la vez (lo normal con el Orquestador corriendo
> varias en paralelo) leían el mismo valor y escribían el mismo +1. Un contador
> corto no es solo impreciso: es el que decide si el usuario llega a VER la
> propuesta de arreglo. Corregido con incremento atómico en SQL y agregación
> previa de las repeticiones de una misma pasada.
>
> **Y un tercer hallazgo, en la frontera entre L2b y el preflight**: el evento
> del preflight guarda su motivo bajo `{"tools": {...}}`, y `failures_in` solo
> miraba `error`/`reason`/`notes` — así que la propuesta de configuración salía
> **sin destino y sin nombre de herramienta**: justo "un aviso que solo sabe
> quejarse". Ahora se lee esa forma, que es donde está lo accionable.
>
> **Hardening del propio E2E, con causas reales detrás**: se espera al EFECTO y
> nunca a un reloj; se drena el registro de tareas en vuelo del bus antes de
> limpiar (fire-and-forget significa que una tarea de otro test puede aterrizar
> después); y las repeticiones se hacen de una en una porque un usuario no pide
> lo mismo tres veces en el mismo milisegundo — al hacerlo de golpe aflora una
> carrera benigna (dos propuestas para el mismo trabajo, que el análisis
> nocturno reconcilia) que no merece complicar el código de producción.
>
> Regresión: **415 passed** en dos lotes, 4 pasadas seguidas del E2E sin
> parpadeo (con el orden aleatorio de pytest activado).

### ✅ L4 — Panel "Aithera aprende" · **Opus, alto** — EJECUTADA (2026-08-06)

> **Cierre L4 (2026-08-06, Opus)** — lo aprendido, por fin, se ve.
>
> **`app/api/endpoints/learner.py` NUEVO**: 7 endpoints que NO añaden lógica de
> aprendizaje, la EXPONEN — y la traducen a lenguaje llano en el BACKEND, no en
> la UI. El `kind` técnico no sale nunca (`skill_new` → "Procedimiento nuevo"),
> el riesgo se dice como se le dice a alguien ("riesgo alto — siempre te
> preguntaré"), y cada culpa lleva su explicación ("Conexión o servicios de
> terceros — no es culpa de Aithera ni de los modelos"). Traducir en el backend
> y no en el frontend tiene una razón: así el panel, el briefing y cualquier
> canal futuro cuentan lo mismo con las mismas palabras.
>
> **`pages/Learning.tsx` NUEVO** + ruta `/learning` + botón propio en el Dock
> (`IconLearning`: una semilla germinando, mismo vocabulario de la lámina) con
> badge de lo que espera decisión. **Pestañas como DATO**: añadir "Caminos" o
> "Informe" en V1.2 será una entrada más en el array, no un refactor.
> Propuestas con la evidencia PLEGADA (la primera lectura es una frase; el dato
> crudo a un clic) y cada misión enlazada a Mission Control — una propuesta que
> no se puede comprobar es una propuesta que hay que creerse. Salud con el
> reparto por culpa, el ranking justo de modelos y el bucket "Sin atribuir"
> VISIBLE. Historial distinguiendo "me lo enseñaste tú" de "lo aprendí
> observando", con Deshacer.
>
> **La garantía de L1, reflejada y no reinventada**: el backend devuelve
> `applicable` (¿hay applier registrado?) y la UI ofrece "Aceptar" o "Ir a
> Ajustes" según eso. Si mañana nace un kind sin applier, el panel hace lo
> correcto solo — nadie tiene que acordarse de añadir una condición.
>
> **Aceptar es UN gesto para el usuario y tres peldaños por dentro**
> (`candidate → proposed → validated → consolidated`): la escalera no se relaja
> por comodidad de la UI, se esconde. Y ni aceptada nace activa: la skill entra
> en DRAFT.
>
> Tests: `tests/test_learner_panel.py` NUEVO (**13**, contra la app REAL vía
> TestClient — es también la prueba de que el router está cableado). Regresión:
> **194 passed** en el subconjunto del Learner + fronteras + arranque; `tsc
> --noEmit` limpio; 38 claves i18n nuevas ×4 idiomas (paridad verificada, 1334).
>
> **Pendiente en Windows**: `vite build` real (el del sandbox no termina dentro
> del límite, patrón ya documentado en PU6a/PU10) y un vistazo a la página:
> aceptar una propuesta, deshacerla, y ver la pestaña Salud con datos reales.

#### Especificación original (para referencia)

### L4 — Panel "Aithera aprende" · **Opus, alto** *(ampliada 2026-08-06)*

**Qué es**: la cara visible de TODO el sistema de aprendizaje — página propia
`/learning` con **entrada propia en el Dock** (icono nuevo en `DockIcons.tsx`,
mismo vocabulario de línea fina: una semilla germinando con nodos; badge
punto-ámbar cuando hay propuestas pendientes, patrón MEL ya existente en el
Dock). NO va como pestaña de Ajustes: el aprendizaje es una capacidad de
primera clase, no una configuración.

**Estructura: pestañas como DATO** (el array de tabs es una lista declarativa —
añadir la pestaña "Caminos" o "Informe" en V1.2 = añadir una entrada, cero
refactor). En V1.1 nacen TRES:

1. **Propuestas** (la bandeja): tarjetas en LENGUAJE LLANO, nunca jerga —
   título tipo *"He visto 3 veces cómo preparas el resumen semanal — ¿lo
   convierto en un procedimiento fijo?"*; badge de riesgo con texto y color
   (verde "riesgo bajo" / ámbar "medio" / rojo "alto — siempre te preguntaré");
   evidencia PLEGADA (*"Visto en 3 misiones"* → expandir lista con enlaces a
   Mission Control vía `mission_id`, el id único de S7·S8); botones
   **Aceptar / Editar / Rechazar**. Rechazar pide un motivo opcional de 1 línea
   que se guarda en la propuesta (el Learner aprende de los "no", doc 15 §8).
   Las `config_fix` (L2b) muestran **"Ir a Ajustes"** en vez de Aceptar
   (deep-link `location.state.tab`); los kinds sin applier JAMÁS muestran
   Aceptar (la garantía de L1 en el backend, reflejada en la UI).
2. **Salud** (el "por qué fallan las cosas" de L2b, en llano): distribución de
   fallos por `blame` con etiquetas honestas — *"Conexión y servicios externos
   — no es culpa de Aithera"*, *"Configuración pendiente — N arreglos
   sugeridos"*, *"Modelos"*, *"Herramientas"*, *"El propio sistema"*, *"Sin
   atribuir"* (visible a propósito: lo que no se sabe no se esconde). Debajo,
   ranking de modelos por `mission_success_rate` (con los excused ya fuera —
   `model_ranking()` de L2/L2b tal cual) y de tools por `error_rate`
   (`tool_ranking()`). Cada barra/fila clicable → misiones de ejemplo
   (`sample_mission_ids` de `failure_stats`).
3. **Historial**: timeline de `skill_events` + decisiones del Learner
   (Decision API filtrando por origen), con **Deshacer** donde aplique
   (`undo_last` de L1) — deshacer deja su propio evento, nunca borra.

**Backend**: router nuevo `/api/learner` (`endpoints/learner.py`) —
`GET /proposals`, `POST /proposals/{id}/approve|reject` (con `note`),
`POST /proposals/{id}/undo`, `GET /health` (failure_stats agregado + rankings),
`GET /history`. Todo lectura sobre APIs YA existentes de L1/L2/L2b — esta
sesión no añade lógica de aprendizaje, la EXPONE.

**UX/estética** (criterios cerrados, no a decidir): mismo lenguaje visual del
resto — `glass-surface` para tarjetas, `holo-frame` SOLO en el contenedor
primario de la página, iconografía informativa propia (patrón `MemoriaPanel`,
stroke 1.1-1.4, `currentColor`); empty states con caja punteada y texto que
explica (*"Aithera todavía no ha aprendido nada — deja que trabaje unas cuantas
misiones y aquí verás lo que va descubriendo"*); i18n ×4 idiomas COMPLETO
(paridad verificada por script, como siempre); tema claro/oscuro sin nada
hardcodeado; nada de tablas de datos crudos — el dato crudo vive a un clic
(expandir), la primera lectura es siempre una frase.

**Además**: línea en el briefing diario (*"esta semana: 1 procedimiento nuevo
propuesto, 2 arreglos de configuración pendientes"*) reusando el patrón de
secciones de PU4b.

- Cierre de fase: los **5** product-contracts (4 de L1 + el de L2b) verdes +
  evals: 2 misiones canónicas nuevas sobre aprendizaje + suite Windows.

*(AV1 "el motor" y AV2 "ritmos + producto" — retirados: ya entregados en
V0.82/83, ver nota de corrección arriba. Contenido histórico recuperable en
el git log de este doc si hiciera falta consultar el alcance original.)*

---

## 6. V1.2 — MCP + TIE v2 + MEL Learning + aprendizaje profundo (10 sesiones) → tag `v1.2.0`

> **[Ampliación 2026-08-06, decisión del usuario]** Se suman 4 sesiones al
> final de la fase — ML3 (Informe de Salud del Sistema), SE1 (Torneo de
> variantes de skills), PE1 (Erosión de caminos) y PE2 (Exploración en
> paralelo). Van AQUÍ y no en V1.1 porque dependen de piezas de esta fase:
> SE1 necesita el banco de evals de T2; PE2 necesita las olas paralelas de T1;
> todas necesitan la taxonomía de L2b acumulando datos atribuidos durante
> semanas. **Orden de ejecución**: C1 → C2 → T1 → T2 → ML1 → ML2 → ML3 → SE1 →
> PE1 → PE2. C1 (primera sesión) añade a sus product-contracts EN ROJO los dos
> de la ampliación: *"una exploración jamás cambia el output del usuario"* y
> *"una variante solo llega a la bandeja tras ganar en el banco"*.

> **[Comparativa competitiva 2026-07-24, doc 32 Anexo]** MCP (cliente+servidor)
> ya estaba planeado aquí — la comparativa con OpenJarvis/OpenClaw/Hermes lo
> CONFIRMA como el estándar de interoperabilidad del sector (los tres lo tienen;
> OpenJarvis además con A2A bidireccional). Ninguna reprogramación: C1/C2 cierran
> ese gap. Nota de diseño: OpenJarvis expone MCP cliente Y servidor de forma
> bidireccional — nuestro C2 (server) ya lo prevé, mantenerlo en el alcance.

### C1 — MCP client · **Fable 5, extra**
- Alcance: `MCPToolProxy` — tools de servidores MCP externos registradas en el
  ToolManager con LAS MISMAS validaciones (schema, whitelist, gates, permiso
  nuevo `mcp.use` en A3b); config de servidores en Ajustes (stdio/SSE); sandbox
  de argumentos. Product-contracts EN ROJO de la fase: "una tool MCP jamás se
  ejecuta sin pasar el gate"; "un servidor MCP caído no rompe el ToolManager";
  "misión con paralelismo no mezcla sesiones" (para T1); "un modelo mal puntuado
  N veces baja en la cadena tras el ciclo nocturno" (para ML1).
- Por qué Fable: superficie de seguridad nueva (código externo de facto).

### C2 — MCP server · **Opus, alto**
- Alcance: exponer el ToolManager como servidor MCP (stdio para Claude
  Code/Desktop) con gates intactos y token local; docs de conexión; las tools
  `internal=True` (aithera_tool) NUNCA se exponen.

### T1 — TIE v2: executor por olas + replan · **Fable 5, extra**
- Alcance: olas paralelas (`asyncio.gather` + semáforo `TIE_MAX_PARALLEL`,
  estructura ya preparada en T3 de doc 21), retry por clase de error, replan de
  subárbol (nodos DONE inmutables — doc 14 §5), presupuestos DUROS por misión
  (tokens/coste desde `usage` del MEL, ya medidos). Aislamiento de recursos por
  misión ya garantizado (S3 browser sessions).
- Tests: producto "paralelismo no mezcla sesiones" en verde; perf: 2 nodos
  paralelos ≈ max(t1,t2) no suma; replan no re-ejecuta nodos DONE (unit).

### T2 — Mission Manager + evals · **Opus, alto**
- Alcance: tabla `missions` formal (hoy misión≡trace), panel Misiones ampliado
  (historial, coste por misión, presupuesto), `MissionAction` del AE (reglas que
  lanzan misiones); **suite de mission evals** (doc 15 §9): 6-8 misiones
  canónicas ejecutables pre-release con criterios objetivos.

### ML1 — MEL Learning + Recommendation Engines · **Opus, alto**
- Alcance: doc 19 §9.2-9.3 completo: job nocturno sobre `mel_executions` +
  `model_stats` (prior bayesiano, half-life 30d, n≥20, ±10/ciclo), recompilación
  en sombra, bandeja de recomendaciones con evidencia, auto-aplicar solo pristine.
- Tests: producto "modelo mal puntuado baja tras ciclo" verde; unit de las 4
  defensas anti-conclusión-falsa (fixtures sintéticas).

### ML2 — Skill Evolution + AutomationLearner · **Opus, alto**
- Alcance: operaciones merge/split/specialize/deprecate como PROPUESTAS (doc 15
  §6) con linaje; AutomationLearner real (doc 11 A: sugerir reglas desde
  patrones de aprobación/uso, HITL); dedup conceptual básico del Knowledge
  Evolution.
- **[2026-08-06]** La operación **Improve** deja de proponerse "a pelo": cuando
  hay ≥2 formas observadas de resolver el mismo trabajo (o una skill existente
  con patrón de fallo identificable), Improve DELEGA en el torneo de SE1 — la
  propuesta que llega a la bandeja es la GANADORA verificada, no la primera
  redacción del LLM. Con una sola forma observada, Improve sigue el camino
  directo de siempre (no se frena el caso simple).

### ML3 — Informe de Salud del Sistema · **Opus, alto** *(NUEVA 2026-08-06)*

**El porqué** (idea 1 del usuario, segunda mitad): la atribución de L2b y el
análisis de L3 arreglan la EJECUCIÓN; falta el nivel de arriba — *"ver por
dónde cojea Aithera"* como sistema y proponer mejoras de ARQUITECTURA. Eso no
puede hacerlo un job barato: es exactamente el caso de "revisar con los modelos
más fiables".

**Qué hace**: job MENSUAL (APScheduler idle, + botón "Generar ahora" en el
panel) con `mel.complete(capability=ANALYZE, policy_override="quality")` — el
primario de la política Calidad, 1-2 llamadas grandes al mes, coste acotado por
diseño. Entrada (todo YA existe cuando esta sesión llega): `failure_stats`
agregada por kind/blame/componente (L2b) + `path_stats` si PE1 ya corrió (si
no, degrada sin ella — el job no espera a nadie) + histórico de
`learner_proposals` (qué se propuso, qué se aceptó/rechazó y por qué) +
`telemetry.report` agregado (doc 31). Salida: informe estructurado de
HALLAZGOS — ejemplos del tipo que se busca: *"el planner asigna tools de
lectura de más en misiones de resumen (evidencia: 12 misiones)"*, *"el 40% de
los fallos de browser vienen del mismo muro de consentimiento"*, *"el modelo X
rinde 30 puntos menos en misiones con documento largo"*. **Cada hallazgo lleva
sus `mission_ids` de evidencia** — un hallazgo sin evidencia enlazada se
descarta en el parseo (determinista, mismo espíritu que el grounding).

**La honestidad estructural** — Aithera JAMÁS modifica su propio código: los
hallazgos se persisten como `learner_proposals kind="system_improvement"`
**SIN applier registrado** — la garantía de L1 hace imposible aplicarlos por
construcción, ni por accidente ni por prompt injection. En el panel no tienen
botón Aceptar: tienen **"Exportar para sesión de desarrollo"** → genera un
markdown en `docs/informes-learner/` (carpeta nueva, committeada) con hallazgo
+ evidencia + archivos del código implicados (el mapeo componente→módulo es una
tabla fija en el código: `tie→app/tie/`, `mel→app/mel/`…), listo para pegarle
a una sesión de Claude. **El bucle se cierra por el usuario** — es la versión
honesta de "Aithera se mejora a sí misma": ella detecta y documenta dónde
cojea; el cambio de código lo hace una sesión de desarrollo con todas las
garantías de siempre (tests, mutación, regresión).

- Tests: hallazgo sin evidencia se descarta (mutación obligada); el kind
  `system_improvement` no se puede aplicar (extiende el test de L1 al endpoint);
  el export produce markdown válido con los enlaces; el job degrada sin
  `path_stats`; JSON basura del modelo → informe vacío honesto, jamás inventado.

### SE1 — Torneo de variantes de skills · **Opus, extra** *(NUEVA 2026-08-06)*

**El porqué** (idea 2 del usuario, primera mitad): tareas similares resueltas
con éxito por CAMINOS DISTINTOS no deben fundirse en una sola skill "promedio"
— hay que diferenciarlas, enfrentarlas y quedarse con la que DEMUESTRA generar
mejores resultados. "Demostrar" = comparar outputs en tareas de prueba, no
opinar.

**Disparador** (determinista, job nocturno, máx 1 torneo/noche): un candidato
de L2 listo para promoción cuya evidencia contiene **≥2 secuencias de tools
distintas** (similitud de secuencia < 0.6 — la evidencia de L2 ya guarda las
tools por misión; esta sesión añade la SECUENCIA ordenada al payload de
evidencia, campo aditivo), O una skill existente con `quality_score < 0.6` y
patrón de fallo identificable (la señal que ML2-Improve le delega). **Si todos
los éxitos fueron por el mismo camino → NO hay torneo**: la escalera de L1/L2
sigue tal cual — el torneo es para cuando hay algo real que comparar, no un
peaje universal que frene la escalera.

**Variantes** (máx 3): una por camino observado — extraída de las misiones-
evidencia REALES de ese camino, no inventada — + como mucho 1 refinada por LLM
(`REASON`, quality). Si había skill existente en uso, entra como **incumbente**
y compite.

**El banco** — `app/learner/bench.py`, construido SOBRE la infraestructura de
mission evals de T2 (por eso SE1 va después): las tareas de prueba son
repeticiones de las misiones-evidencia (goal + contexto grabado en la traza).
**Regla dura de seguridad**: el banco ejecuta con whitelist de tools de
LECTURA; si la skill inherentemente escribe, toda escritura va a
`test-lab/bench-sandbox/` (gitignored, patrón test-lab) y las acciones de
envío (email/telegram) se sustituyen por un stub que REGISTRA "habría enviado
X" — el banco jamás toca el disco real del usuario ni el mundo exterior.
Ejecución con política ECONOMY (correr variantes es volumen); juzgar es lo
caro y va aparte.

**Comparación** (en este orden, el LLM lo último): criterios OBJETIVOS primero
— ¿completó?, nº de pasos, nº de errores, coste en tokens, latencia (todo ya
medido por la telemetría del propio run) —; juez LLM SOLO para desempate de
calidad del output (`ANALYZE`, quality), con regla anti-sesgo: **el juez nunca
es el mismo modelo que ejecutó la variante juzgada**; si solo hay un modelo
capaz disponible, se juzga igual pero el resultado queda marcado
`judge_bias=true` (visible en la evidencia — nunca silencioso).

**Resultado**: SOLO la ganadora entra como propuesta REAL en la bandeja, con la
**tabla comparativa completa adjunta como evidencia** (el usuario ve por qué
ganó); las perdedoras se registran en `skill_events` con la comparativa en el
payload — el porqué nunca se pierde. **Si el incumbente gana, no hay
propuesta** (anti-churn: no se molesta al usuario para decirle que lo que ya
tiene es lo mejor).

- Tests: torneo con fixtures deterministas (2 variantes con outputs conocidos →
  gana la correcta); incumbente ganador no genera propuesta; camino único no
  dispara torneo (mutación); la whitelist de lectura del banco (mutación
  obligada: quitarla tumba el test de que nada se escribe fuera del sandbox);
  el juez ≠ ejecutor; contrato de producto de fase: *"una variante solo llega
  a la bandeja tras ganar en el banco"* EN VERDE.

### PE1 — Erosión de caminos · **Opus, alto** *(NUEVA 2026-08-06)*

**El porqué** (la metáfora del usuario, que es exactamente el diseño): *"como
agua sobre una montaña de tierra — la primera gota busca un camino, las
siguientes a veces repiten y a veces abren otros, y al cabo de muchas gotas el
agua baja casi siempre por el mejor, porque la propia erosión lo ha ido
formando"*. Una misma clase de trabajo entra hoy por caminos distintos (charla
/ acción directa / plan / multi-objetivo) según cómo la clasifique el intent —
y nadie mide cuál funciona mejor PARA ESA clase. La erosión es esa medición
convertida, con evidencia suficiente, en cauce.

**1 · El tipo de trabajo se vuelve entidad**: tabla `work_types` (`id, label,
words JSON` — el conjunto canónico de `content_words` —, `tools JSON,
missions, created_at`). L2 ya agrupa por Jaccard dentro de las propuestas;
PE1 lo PERSISTE para que todos los análisis (torneo, caminos, informe) hablen
del mismo concepto. Asignación en `mission_learning._learn`: `same_work` ≥0.5
contra los existentes → cuenta; sin match y con repetición ≥3 → nace uno.

**2 · La medición**: tabla `path_stats` (`work_type_id × path`
[chat|direct|planned|multi] `× missions, ok, excused, avg_llm_calls, avg_ms,
explored, explored_better, last_seen`). El `path` YA lo registra la telemetría
desde S3 y los excused vienen de L2b — **cero instrumentación nueva**: esta
tabla solo agrega lo que ya se graba.

**3 · El análisis** (job nocturno, determinista): cuando un work_type acumula
**n≥5 misiones por DOS caminos distintos** con diferencia de éxito **≥20
puntos** (excused fuera del denominador, como siempre), nace una propuesta
`path_hint` (*"este tipo de trabajo va mejor por el camino X — visto en N
misiones"*). Riesgo MEDIO en la escalera: 3 confirmaciones más o aprobación
del usuario en el panel.

**4 · La aplicación del hint ACEPTADO** (la única parte que toca al TIE —
exacta, sin margen): hints activos en la tabla `Config`
(`learner.path_hint.<work_type_id>` = `"direct"|"planned"`).
`tie/intents.classify()`, DESPUÉS del clasificador y solo si el mensaje
matchea el work_type (`same_work` ≥0.5), ajusta **ÚNICAMENTE**
`requires_planning` según el hint, dejándolo registrado en la traza
(`intent.path_hint_applied`, campo append-only). Nunca toca `requires_tools`,
nunca fuerza camino corto a algo con herramientas (`is_short_path` se deriva
solo, como siempre) — el clasificador conserva la última palabra en todo lo
demás. Un hint es un CAUCE, no una presa.

- Tests: nacimiento de work_type al 3.º match; hint solo con n≥5 Y diferencia
  ≥20 (mutación: quitar el umbral); hint aceptado ajusta `requires_planning` y
  deja rastro en la traza; hint NO aceptado no toca nada (mutación); mensaje
  que no matchea el work_type queda intacto; los excused no inflan ninguna
  tasa.

### PE2 — Exploración en paralelo (shadow runs) · **Opus, extra** *(NUEVA 2026-08-06)*

**El porqué** (idea 2 del usuario, cierre): la erosión sola converge y se
estanca — *"siempre está bien que el sistema pruebe caminos nuevos"* — pero
sin arriesgar NUNCA el resultado: *"si el camino que busca mejoras no funciona
tan bien, el output de Aithera será el del camino fiable, pero seguiremos
aprendiendo"*. Exploración sin riesgo = la sombra corre en paralelo y solo
deja apuntes.

**Activación**: `LEARNER_EXPLORATION_RATE` (config, **default 0 = APAGADO**).
Se enciende desde la pestaña Caminos del panel con la explicación de coste a
la vista (*"cada exploración duplica aproximadamente el coste de esa misión"*)
— transparencia antes que sorpresa en la factura.

**Condiciones para explorar** (TODAS, deterministas, evaluadas en
`tie/pipeline.py` DESPUÉS de tener el plan primario — así se decide sobre el
plan real, no sobre una predicción): el work_type es conocido y tiene camino
fiable (`path_stats` n≥5, éxito ≥80%) · el plan primario contiene SOLO tools
de la **whitelist de lectura** (search, browser-lectura, document-lectura,
`filesystem.read_file`, memory-search — JAMÁS write/send/execute/desktop) ·
ningún nodo requiere gate · no hay otra misión corriendo (el semáforo de T1) ·
dado de exploración (`random() < rate`).

**Ejecución**: la misión primaria corre EXACTAMENTE igual que siempre — mismo
camino, misma política, mismo todo: la no-regresión del usuario es por
construcción, no por promesa. La sombra, en paralelo (la ola de T1): plan
alternativo pedido al planner con instrucción explícita de explorar otra vía ·
política ECONOMY forzada · presupuesto duro = 50% del primario ·
**`Authority.shadow=True`** (campo nuevo append-only) que bloquea en segunda
capa toda escritura de memoria (`memory.save`, los `_remember` del engine) y
cualquier acción fuera de la whitelist — la sombra no deja huella ni en el
mundo NI en la memoria, aunque su plan viniera mal generado.

**Resultado**: el usuario recibe SIEMPRE el output primario — la sombra ni se
menciona en la respuesta. La comparación (criterios objetivos de SE1; juez
solo si empatan) se escribe ÚNICAMENTE en `path_stats.explored/
explored_better` — evidencia para futuros hints de PE1. Si la sombra falla o
se pasa de presupuesto: se cancela, se apunta, y nadie se entera salvo la
telemetría. La pestaña Caminos lo cuenta después: *"esta semana probé 3
caminos nuevos; 1 resultó mejor y ya te lo he propuesto"*.

- Tests (los de seguridad son la sesión): la sombra jamás ejecuta una tool
  fuera de la whitelist (mutación obligada); jamás escribe memoria (mutación);
  contrato de producto *"una exploración jamás cambia el output del usuario"*
  EN VERDE — output byte-idéntico con rate 0 y con rate 1 forzando sombra;
  rate 0 = ni una sombra; presupuesto de la sombra respetado; el resultado
  llega a `path_stats` y a ningún otro sitio.

- Cierre de fase (se traslada aquí desde ML2): evals completas + suite Windows
  + los product-contracts de la ampliación en verde.

---

## 7. V1.3 — Hermes Runtime (5 sesiones, GO/NO-GO) → tag `v1.3.0`

### H0 — Investigación en real · **Fable 5, extra**
- Alcance: instalar `hermes-agent` (pip/git, v0.14+) en entorno aislado y
  VERIFICAR: (1) API real de memory providers enchufables (v2026.4.3) — ¿cubre
  save/retrieve/search?; (2) interceptación de tools (¿provider formal o wrapper?);
  (3) LLM vía endpoint OpenAI-compatible local (shim del MEL) — ¿todas sus
  llamadas pasan?; (4) desactivación de sus superficies (gateway/canales/browser
  propios); (5) huella RAM/CPU junto a Chroma+sentence-transformers; (6) licencia
  y telemetría/llamadas a Nous (¿operable offline?). Entregable: informe +
  **GO/NO-GO** + contratos `AgentTask`/providers cerrados en doc 10.
- Los product-contracts de la fase EN ROJO: "Hermes ejecuta una tarea usando
  memoria de Aithera sin escribir UN archivo propio"; "toda tool de Hermes pasa
  por whitelist+gate"; "todas las llamadas LLM de Hermes pasan por el MEL";
  "matar Hermes a mitad de tarea deja la misión recuperable".

### H1 — HermesRuntime + shim MEL · **Fable 5, extra**
- Alcance: `HermesRuntime(AgentRuntime)` esqueleto + endpoint local
  OpenAI-compatible que traduce a `mel.complete/stream` (así TODAS las llamadas
  LLM de Hermes respetan políticas/fallbacks/aprendizaje del MEL) + lifecycle.
- **[Comparativa competitiva 2026-07-24, doc 32 Anexo] Patrón "narrow waist" de
  Hermes**: Hermes usa UN único contrato `provider.py`+`registry.py`+`plugin.yaml`
  para TODO lo pluggable (modelos, canales, navegador, TTS/STT, memoria) — no un
  interfaz bespoke por capacidad. Aithera hoy solo lo hace para modelos (el MEL).
  H1 es el momento natural de generalizarlo: al enchufar Hermes como 2.º runtime
  bajo `AgentRuntime`, formalizar el mismo contrato uniforme para runtimes (y
  dejar el camino abierto a aplicarlo a voz/navegador/memoria/canales cuando
  toque). Es la lección arquitectónica de tener un 2.º runtime real: el valor del
  contrato uniforme se paga justo aquí. Detalle en doc 10 (AgentRuntime).
  **Nota honesta**: el TIE de Aithera ya es MÁS estructurado que el bucle plano
  de Hermes (planner+DAG vs ReAct) — Hermes NO trae planificación "gratis"; lo
  que aporta es su ecosistema (32 proveedores, 24 canales, 181 skills) y el
  patrón del contrato uniforme, no su arquitectura de razonamiento.

### H2 — Memory + Context providers · **Opus, alto**
- AitheraMemoryProvider/ContextProvider sobre `memory_router` (doc 10 §2) +
  tests de aislamiento (contrato "cero archivos propios" en verde).

### H3 — Tool + Skill providers · **Opus, alto**
- AitheraToolProvider (gates SIEMPRE; grounding A-1 aplicado: lo que Hermes dice
  haber hecho debe tener tool ejecutada) + AitheraSkillProvider (skills de
  Hermes → LSL como DRAFT con cuarentena).

### H4 — Routing + cierre · **Opus, alto**
- Routing por capabilities en el TIE (tareas complejas→Hermes, simples→toolloop
  propio), panel de agentes actualizado, 0 menciones a "Hermes" en UI, evals con
  2 misiones vía Hermes.
- **Si H0 = NO-GO**: H1-H4 se sustituyen por 2 sesiones (Opus, alto) del plan B
  (doc 10 §6): endurecer `AitheraNativeRuntime` (toolloop) con reflection loop
  ligero del Learner. La fase sigue entregando valor.

---

## 8. V1.4 — Red + voz + pulido + hardening (7 sesiones) → tag `v1.4.0`

> **[Comparativa competitiva 2026-07-24, doc 32 Anexo]** V1.4 absorbe 3 items
> derivados de la comparativa OpenJarvis/OpenClaw/Hermes (W3 canales, S1
> sandboxing, y memoria legible dentro de U1) — encajan aquí porque V1.4 es la
> pasada de "red + clientes + pulido/hardening" antes del gran V1.5 (AVCS).

### W1 — Web client + PIN + rate limiting · **Fable 5, extra**
- Build React servido en `/app`, token/PIN para orígenes no-localhost, slowapi,
  CORS ampliado controlado, sesiones. Superficie de red = Fable. Product-contract:
  "sin PIN válido, NINGÚN endpoint responde datos desde origen de red".
### W2 — PWA + móvil · **Opus, alto** — manifest, service worker, layout móvil.
### W3 — 2 canales más del Gateway (Discord + WhatsApp) · **Opus, alto**
- **[Comparativa, post-1.0 decidido por el usuario]** OpenClaw/Hermes/OpenJarvis
  tienen 24-37 canales; Aithera solo Telegram. El patrón `ChannelAdapter` (ABC)
  + `Gateway.dispatch` YA está pensado para esto (doc 20, de hecho inspirado en
  OpenClaw) — añadir un adapter es fino, cero cambios en el resto (principio 3).
  Discord y WhatsApp son los dos siguientes obvios. Whitelist por usuario, token
  cifrado DPAPI (mismo patrón que Telegram). Product-contract: "un canal nuevo
  no toca la lógica de negocio; un adapter roto no tumba el Gateway".
### S1 — Sandboxing de ejecución (Docker/contenedor) · **Fable 5, extra**
- **[Comparativa, antes de v1.5 decidido por el usuario]** Hoy `shell_tool`/
  `powershell_tool`/`desktop_tool`/`browser_tool` se apoyan en whitelist de
  comandos, NO en aislamiento de proceso — 2 de 3 competidores (OpenClaw: Docker
  por defecto; Hermes: Docker/SSH/Singularity/Modal/Daytona/NVIDIA OpenShell;
  OpenJarvis: WASM+Docker) lo tratan como imprescindible. Alcance: modo de
  ejecución CONTENEDORIZADA opcional para las tools peligrosas (Docker como
  backend por defecto, degradación graciosa a whitelist si Docker no está),
  sin romper el modelo de permisos A3b existente. Superficie de seguridad = Fable.
  Product-contract: "con Docker disponible, `shell.run` corre en un contenedor
  aislado, no en el proceso del backend"; "sin Docker, sigue funcionando con la
  whitelist de siempre (nunca deja al usuario sin la capacidad)".
### V1 — Voz data-driven · **Opus, alto** — decidir VZ2 (tiny/GPU), VZ3 (Silero
  VAD), VZ4 con los datos reales del profiling VZ5; implementar lo que los datos
  justifiquen; presupuesto TTFB < 2 s (JWIKI 08).
### U1 — UX remanentes + memoria humano-legible · **Sonnet, medio**
- ConfirmDialog restantes, empty-states, focus-trap (doc 26 U1-U3).
- **[Comparativa, retoque MOS/UX decidido por el usuario]** Memoria humano-legible
  (inspirado en `MEMORY.md` de OpenClaw): el MOS de Aithera es MÁS sofisticado
  (ChromaDB, 5 tipos, lifecycle) pero nada es tan auditable como un texto que el
  usuario pueda abrir y editar. Extender `memory/profile.py` (R6.5c, ya visible y
  borrable en Ajustes) hacia una VISTA/EXPORT legible del perfil + memoria
  personal — el usuario ve y edita lo que Aithera sabe de él en texto plano.
  Sigue siendo el MOS por debajo; esto es una capa de legibilidad, no un cambio
  de almacén. Product-contract: "el usuario puede leer y editar su perfil en
  texto; una edición se refleja en el MOS".

---

## 8b. V1.4.5 — Multi-instancia de runtimes (1-2 sesiones)

> **[Nace el 2026-08-05]** Era la segunda mitad de la vieja sesión A5 («UI
> rediseñada alrededor de la presencia **+ multi-instancia de runtimes por
> perfil (si H=GO)**»). Estaba dentro de la fase AVCS por convivencia, no por
> dependencia: no tiene nada de frontend ni de partículas — depende de Hermes
> (V1.3) y del registro de runtimes del doc 10. Al mover el AVCS a V2.0+ se
> habría ido con él por error, así que sale a fase propia.

### R1 — Varios runtimes vivos a la vez · **Fable, extra**
- Alcance: el registro `{name: runtime}` del doc 10 pasa de "uno activo" a
  varias instancias por PERFIL (p. ej. un HermesRuntime por proyecto, o uno
  nativo y uno Hermes conviviendo), con selección por misión/agente y
  aislamiento de estado entre instancias. Si H0 salió NO-GO, la fase se reduce a
  varias instancias del runtime nativo — sigue teniendo sentido (aislar el
  estado de dos proyectos que trabajan a la vez) y el contrato queda listo para
  el día que entre un segundo runtime.
- Por qué Fable: es concurrencia + aislamiento, la combinación que más caro sale
  equivocar (la fuga de sesión de navegador de S3/S9 fue exactamente esto).
- Product-contract: "dos misiones concurrentes en runtimes distintos no comparten
  estado"; "un runtime caído no tumba al otro".

---

## 9. V1.5 — Cierre del organismo local + MVP-beta (5 sesiones) → tag `v1.5.0`

> **[Reordenación 2026-08-05]** Esta fase es la FUSIÓN de dos cosas: la sesión
> O5 de la antigua V1.6 (lo único de esa fase que no era AVCS) y las 4 sesiones
> B1-B4 del antiguo "V1.0 cierre". Tiene sentido junto: se empaqueta cuando el
> producto ya no va a cambiar de forma, y se revisan los contratos de red con el
> organismo local terminado delante.

### O5 — Project Memory Capa 2 + puerta a GSN/CIE · **Fable, extra**
- Alcance: **Project Memory Capa 2 formal** (permisos por proyecto, doc 08 Capa
  2) + **revisión de contratos GSN/CIE** (PortableSkill, PrivacyFilter,
  aislamiento RFC-001, GuardianRuntime) → handoff documentado a V2.0.
- Va PRIMERA de la fase a propósito: si la revisión de contratos obliga a tocar
  algo del núcleo, mejor antes de empaquetarlo que después.

### B1 — Verificación total + deudas de cierre · **Opus, esfuerzo alto**
- Texto íntegro en §4b. **Su primera mitad se puede adelantar** a cualquier
  hueco entre fases: la carrera `state=done`/`outcome` del tracer (hallazgo T5) y
  la suite completa en Windows son deuda de calidad, no empaquetado, y no ganan
  nada esperando aquí.
- Al llegar aquí, su alcance habrá crecido con lo acumulado: cada bloque desde
  V1.1 deja su propio "Pendiente en Windows", y esta sesión es donde se saldan
  todos de una pasada.

### B2 — Instalador + auto-start · **Fable 5, esfuerzo extra**
- Texto íntegro en §4b. **Ojo al revisarlo**: se escribió en 2026-07-20 y su
  lista de dependencias a empaquetar es la de entonces. Al ejecutarlo habrá que
  añadir lo que hayan traído V1.1-V1.4 (al menos: Docker opcional de S1, los
  servidores MCP de C1, `hermes-agent` si H0 = GO, y Playwright/Chromium, cuya
  decisión —descarga opcional post-install— sigue en pie).

### B3 — Onboarding wizard · **Opus, esfuerzo alto**
- Texto íntegro en §4b, **más los pasos que las fases nuevas hagan necesarios**:
  perfil del Learner y su panel de aprendizaje (V1.1), servidores MCP (V1.2),
  runtime por defecto si Hermes entró (V1.3), PIN de red (V1.4).

### B4 — Beta kit + release · **Sonnet, esfuerzo medio**
- Texto íntegro en §4b. Bump sincronizado a `1.5.0` (ya no `1.0.0`: ese tag se
  puso el 2026-08-02) + tag + CLAUDE.md §1.

**Cierre V1.5 = Aithera como organismo completo local, empaquetado y
distribuible.** Después: **V2.0+** (AVCS maduro, GSN + CIE), plan de sesiones
propio al llegar, sobre los contratos revisados en O5.

---

## 10. V2.0+ — Aparcadero explícito (no es "algún día", es "aquí")

> **[Reordenación 2026-08-05]** Lo que sale del tramo activo. Se guarda con su
> alcance íntegro para que retomarlo sea leer, no rediseñar.

### AVCS MVP1 "Lenguaje completo" (5 sesiones, doc 13 §20)

| Sesión | Alcance (doc 13) | Modelo/esfuerzo |
|---|---|---|
| A1 | campos componibles íntegros + factor de sincronía S + 7 ritmos en el motor | **Fable, extra** |
| A2 | raíces/ramas maduras + mandalas de Comprensión + Error/Recuperación | Opus, alto |
| A3 | AudioReactor completo (bandas) + ritmo Acción (canalización elemental) | Opus, alto |
| A4 | PerformanceManager íntegro (escalera + invariantes) + tests de presencia/no-repetición/calma | **Fable, extra** |
| A5 | UI general rediseñada alrededor de la presencia | Opus, alto |

Product-contracts (A1 en rojo): "ningún cambio de ritmo produce salto perceptible
(>1 frame)"; "los invariantes de identidad presentes en Q2"; "5 min sin bucles
predecibles". Cierre: tests §21 de doc 13 completos.
*(La multi-instancia de runtimes que A5 llevaba pegada se fue a §8b — no era AVCS.)*

### AVCS MVP2 "Organismo" (4 sesiones, doc 13 §17)

| Sesión | Alcance | Modelo/esfuerzo |
|---|---|---|
| O1 | disolución universal + paneles que SE FORMAN de partículas (13 §17) | **Fable, extra** |
| O2 | botones orgánicos + notificaciones-brote + contenido HTML esclavizado a la formación | Opus, alto |
| O3 | vida procedural (luciérnagas/semillas/mariposas; cooldowns ≥20 min; ≤2% partículas) | Opus, alto |
| O4 | memoria visual (madurez log de horas de uso, cambios <2%/semana) + persistencia | Opus, alto |

**Por qué el AVCS maduro sale del tramo activo** (decisión del usuario,
2026-08-05): Génesis está entregado y en uso diario desde V0.82/83, y se ha
seguido puliendo en el bloque PU (PU5a → PU5g: partículas por tier con
luminosidad medida, anillos que giran, ECG al hablar, bloom, apagón arreglado).
Lo que queda —4 ritmos, campos maduros, UI orgánica— **mejora una capacidad que
YA existe**, mientras que el Learner, MCP, Hermes y la red son capacidades que
NO existen. Con el organismo cognitivo a medias, 10 sesiones de frontend/GPU
competían por el sitio equivocado.

**Nota de continuidad**: el AVCS NO se congela mientras tanto. El pulido puntual
(PU5x) siguió siendo bienvenido durante todo el bloque de pulido y lo seguirá
siendo — lo aparcado es el salto de ARQUITECTURA visual, no los retoques.

### GSN + CIE
Doc 08 RFC-004/005. Plan de sesiones propio al llegar, sobre los contratos
revisados en O5 (V1.5).

## 11. Registro de decisiones de este plan

| Decisión | Resolución | Razón |
|---|---|---|
| ¿TIE v2 y v3 juntos? | v2 solo (V1.2); **v3 disuelto** en Learner/MEL/Hermes | v3 era una etiqueta sobre dependencias ajenas |
| ¿Hermes gradual o completo? | **Gradual con H0 GO/NO-GO** (V1.3) | viable (lib Python + memory providers enchufables + LLM custom endpoint→MEL) pero hay que interceptar 3 sistemas y aplicar las garantías de la auditoría; "de golpe" = repetir el error del Orquestrator |
| ¿Learner antes que Hermes? | Sí (V1.1) | máximo fan-out; Hermes necesita la LSL |
| ¿AVCS Génesis dónde? | **Ninguna parte — ya construido** en V0.82/83 (corrección 2026-07-22) | se asumió sin construir por una nota de CLAUDE.md mal interpretada; commits reales de 2026-07-10/12 lo desmienten (doc 03 §2) |
| ¿Playwright en instalador? | Descarga opcional post-install | 300 MB fuera del NSIS; consentimiento explícito |
| ¿Empaquetado backend? | venv embebido + Python portable | pyinstaller inviable con chromadb/torch |
| Tests | pirámide 4 capas; producto EN ROJO al abrir cada fase; evals desde V1.2 | la lección S4, sistematizada |
| **¿MVP-beta al principio o al final?** (2026-08-05) | **Al final (V1.5)** | no hay beta testers, y el instalador CADUCA: cada fase posterior añade dependencias, pantallas de onboarding y permisos que obligarían a rehacerlo. El tag `v1.0.0` ya está puesto, así que la versión no espera a nadie |
| **¿AVCS MVP1/MVP2 en el tramo?** (2026-08-05) | **No — a V2.0+** (§10) | Génesis está entregado y en uso diario; lo que queda MEJORA una capacidad que ya existe, frente a Learner/MCP/Hermes/red que son capacidades ausentes. El pulido puntual del AVCS sigue permitido |
| **¿Y la multi-instancia de runtimes?** (2026-08-05) | **Fase propia V1.4.5** (§8b) | estaba pegada a la sesión A5 del AVCS por convivencia, no por dependencia: es concurrencia de backend y depende de Hermes. Se habría ido a V2.0+ por error |
| ¿Desaparece V1.6? (2026-08-05) | **Sí** | sus 4 sesiones AVCS van a V2.0+ y la 5.ª (O5, Project Memory C2 + contratos GSN/CIE) sube a V1.5, que pasa a ser la fase de cierre |
| **¿La atribución de fallos con LLM o determinista?** (2026-08-06) | **Determinista en el punto del fallo** (L2b); el LLM solo analiza fallos YA atribuidos (L3/ML3) | el código en el punto del fallo SABE qué pasó; pedirle a un modelo que adivine la culpa viola la anti-contaminación (doc 15 §3.3) — y un modelo juzgando fallos de modelos es el bucle de retroalimentación exacto que se quiere evitar |
| **¿Torneo de variantes para TODA skill?** (2026-08-06) | **No — solo con ≥2 caminos observados o incumbente con patrón de fallo** (SE1) | un torneo universal frenaría la escalera y multiplicaría el coste sin ganancia: sin nada que comparar, comparar es teatro |
| **¿Puede Aithera aplicar mejoras a su propio sistema?** (2026-08-06) | **Jamás** — `system_improvement` no tiene applier (imposible por construcción); el panel exporta un informe para una sesión de desarrollo (ML3) | la versión honesta de "self-improving": detectar y documentar es de Aithera; cambiar código es de una sesión con tests/mutación/regresión |
| **¿Shadow runs con escrituras?** (2026-08-06) | **No — solo misiones 100% de lectura, OFF por defecto, doble capa** (whitelist del plan + `Authority.shadow`) (PE2) | una sombra que envía un email es un email enviado dos veces; el coste extra se enseña ANTES de activarlo |

---
*Plan 2026-07-20 (Fable 5, rol CTO+comité). Fuentes: CLAUDE.md (estado real),
docs 09/10/13/14/15/19/24/25/26, investigación Hermes (GitHub NousResearch/
hermes-agent, docs oficiales). Sustituye la tabla V1.1-V1.6 previa del roadmap.*
*Corrección 2026-07-22: AVCS Génesis (V0.82/83) se había construido de
verdad (commits 2026-07-10 a 07-12) cuando este plan se escribió — una nota
de CLAUDE.md del sprint W2b, mal interpretada, decía lo contrario. Retiradas
las sesiones AV1-AV2 de V1.1 (35→33 sesiones totales); sin más cambios de
alcance en el resto del plan. Detalle de la auditoría en doc 03 §2.*
***Reordenación 2026-08-05 (decisión del usuario, tras cerrar C·WEB-4 y el doc
32 entero)**: el MVP-beta (B1-B4) se aplaza de la cabeza del plan a V1.5; el
AVCS maduro (MVP1 A1-A5 + MVP2 O1-O4) sale del tramo a V2.0+; nace V1.4.5
(multi-instancia de runtimes, rescatada de la vieja A5); V1.6 desaparece como
fase y su sesión O5 sube a V1.5. **Ninguna sesión se ha borrado ni recortado** —
todas conservan su alcance, su modelo y sus tests, solo cambian de sitio. El
tramo activo pasa de 36 sesiones a 23-24 + 10 aparcadas. **Fase que se empieza
ahora: V1.1 (Learner operativo), sesión L1.***
***Ampliación 2026-08-06 (decisión del usuario, con L1-L2 ya ejecutadas)**: el
sistema de aprendizaje gana atribución de fallos (L2b, V1.1 — "un error vale
tanto como un éxito, pero solo si se sabe de quién es") y el análisis profundo
de V1.2 (ML3 Informe de Salud · SE1 Torneo de variantes · PE1 Erosión de
caminos · PE2 Exploración en paralelo — "los éxitos enseñan CÓMO; caminos
distintos se comparan y gana el que lo demuestra"). Tramo activo: 23-24 →
28-29 sesiones. Todo lo nuevo desemboca en el panel de L4 (pestañas como dato:
Propuestas/Salud/Historial en V1.1, +Caminos/+Informe en V1.2). Diseño
ejecutable completo en §5 (L2b) y §6 (ML3/SE1/PE1/PE2); registro de las 4
decisiones de diseño en §11.*
