# 27 — Plan de Desarrollo V1.0 → V1.6 (dependencias, sesiones, modelos y tests)

> **Estatus**: plan ejecutivo definitivo del tramo V1.0→V1.6. Cada sesión queda
> especificada para que en las sesiones de trabajo NO se decida nada: alcance,
> diseño de referencia, tests obligatorios, criterio de cierre, y **modelo +
> esfuerzo asignado**. De V1.6 a V2.0 el trabajo es GSN + CIE (doc 08 RFC-004/005;
> se planificará al cerrar V1.6 con los contratos ya revisados en O5 de V1.6).
>
> **Punto de partida real** (CLAUDE.md, 2026-07-20): `v0.9.5` — TIE v1, MEL v1
> (E1-E2b), Tools (14/91), Orquestrator R1-R7, Corrección S1-S4 y Optimización
> O1-O3/V1-V3/VZ1-VZ5 CERRADOS. Suite 751+ tests. Falta para `1.0.0`: MVP-beta.

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
AVCS Génesis (Fase 0) ────→ nada del backend (frontend puro; estaba SIN construir)
AVCS MVP1/MVP2 ───────────→ AVCS Génesis
Web+PWA+PIN ──────────────→ nada (independiente; mejor tras estabilizar el núcleo)
GSN/CIE (V2.0) ───────────→ LSL madura + Skill Evolution + contratos revisados
```

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

## 2. Roadmap resultante (V1.0 → V1.6)

| Fase | Nombre | Sesiones | Por qué aquí |
|---|---|---|---|
| **V1.0 cierre** | MVP-beta (instalador + onboarding + verificación total) | 4 | sin dependencias; todo lo demás espera a que la beta exista |
| **V1.1** | Learner operativo | 4 | máximo fan-out de dependencias (AVCS Génesis YA entregado en V0.82/83 — corrección 2026-07-22, ver §1.3) |
| **V1.2** | MCP interop + TIE v2 + MEL Learning + Skill Evolution/AutomationLearner | 6 | consume model_stats (V1.1); MCP prepara a Hermes |
| **V1.3** | Hermes Runtime (H0 GO/NO-GO → H1-H4) | 5 | necesita LSL (V1.1) y aprovecha MCP (V1.2) |
| **V1.4** | Red (Web+PWA+PIN) + 2 canales (Discord/WhatsApp) + sandboxing Docker + voz data-driven + UX/memoria legible | 7 | independiente; mejor con el núcleo agéntico ya estable. +3 sesiones de la comparativa competitiva (doc 32 Anexo) |
| **V1.5** | AVCS MVP1 + Hub avanzado + multi-instancia runtimes | 5 | necesita Génesis (V1.1) y Hermes si GO (V1.3) |
| **V1.6** | AVCS MVP2 + Project Memory Capa 2 + puerta a GSN/CIE | 5 | cierra el organismo; revisa contratos de red para V2.0 |

Total: **36 sesiones** (35→33 tras la corrección 2026-07-22: AVCS Génesis ya
construido, se retiran las 2 sesiones AV1-AV2 de V1.1; 33→36 el 2026-07-24 al
añadir 3 sesiones a V1.4 desde la comparativa competitiva —W3 canales, S1
sandboxing, y la ampliación de U1 con memoria legible— ver doc 32 Anexo). Reparto
de modelos: Fable 5 ×12 (crítico), Opus 4.8 ×22, Sonnet ×2. Regla de asignación:
**Fable = contratos nuevos, concurrencia, seguridad, GPU delicado** (equivocarse ahí cuesta el doble de arreglar — aquí no
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

## 4. V1.0 cierre — MVP-beta (4 sesiones) → tag `v1.0.0`

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

## 5. V1.1 — Learner operativo (4 sesiones) → tag `v1.1.0`

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

### L1 — Contratos del Learner + LSL completa · **Fable 5, extra**
- Alcance: tabla `skills` + `skill_events` con linaje (docs 09 §1.1, 15 §6.2),
  migración desde el stub `mem_skill` (backfill mecánico), escalera de confianza
  (doc 15 §3: estados y transiciones por evidencia/HITL), API `app/learner/`
  (barrel + fronteras doc 16). **Escribe EN ROJO los product-contracts de la
  fase**: "una misión repetida 3+ veces produce una skill DRAFT"; "ninguna
  propuesta del Learner se aplica sin evidencia o aprobación"; "undo restaura
  el estado anterior"; "el Learner jamás escribe fuera de sus tablas/colecciones".
- Por qué Fable: estos contratos gobiernan V1.1→V2.0 (la GSN hereda LocalSkill).

### L2 — Mission Learning · **Opus, alto**
- Alcance: suscripción a `mission.completed` → job post-misión asíncrono (doc 15
  §4): agrega a `model_stats` (tabla compartida con MEL — doc 19 §9.2), registra
  decisiones/pins, propone skills candidatas (DRAFT + cuarentena). Capability
  `ANALYZE` vía MEL (nunca ai_manager).
- Tests: producto L1 en verde parcial + unit del agregador; verificación en vivo
  con 3 misiones reales.

### L3 — LLL análisis 2-5 · **Opus, alto**
- Alcance: patrones de error (mem_error), skills transferibles entre proyectos
  (WPMS tags), calidad de skills (quality_score/error_rate), briefing semanal de
  aprendizaje (doc 09 §2.2). Jobs APScheduler idle, micro-batch ≤50.
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

### L4 — Panel "Lo que Aithera ha aprendido" · **Opus, alto**
- Alcance: página/panel con propuestas (skill nueva, mejora, regla sugerida) +
  Aceptar/Editar/Rechazar/**Undo** + historial; línea en el briefing; badge
  discreto (patrón punto-ámbar del MEL). Los rechazos se registran (el Learner
  aprende de los "no").
- Cierre de fase: los 4 product-contracts de L1 verdes + evals: 2 misiones
  canónicas nuevas sobre aprendizaje.

*(AV1 "el motor" y AV2 "ritmos + producto" — retirados: ya entregados en
V0.82/83, ver nota de corrección arriba. Contenido histórico recuperable en
el git log de este doc si hiciera falta consultar el alcance original.)*

---

## 6. V1.2 — MCP + TIE v2 + MEL Learning (6 sesiones) → tag `v1.2.0`

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
- Cierre de fase: evals completas + suite Windows.

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

## 9. V1.5 — AVCS MVP1 + Hub avanzado (5 sesiones) → tag `v1.5.0`

| Sesión | Alcance (doc 13) | Modelo/esfuerzo |
|---|---|---|
| A1 | campos componibles íntegros + factor de sincronía S + 7 ritmos en el motor | **Fable, extra** |
| A2 | raíces/ramas maduras + mandalas de Comprensión + Error/Recuperación | Opus, alto |
| A3 | AudioReactor completo (bandas) + ritmo Acción (canalización elemental) | Opus, alto |
| A4 | PerformanceManager íntegro (escalera + invariantes) + tests de presencia/no-repetición/calma | **Fable, extra** |
| A5 | UI general rediseñada alrededor de la presencia + multi-instancia de runtimes por perfil (si H=GO) | Opus, alto |

Product-contracts (A1 en rojo): "ningún cambio de ritmo produce salto perceptible
(>1 frame)"; "los invariantes de identidad presentes en Q1"; "5 min sin bucles
predecibles". Cierre: tests §21 de doc 13 completos.

## 10. V1.6 — AVCS MVP2 + puerta a V2.0 (5 sesiones) → tag `v1.6.0`

| Sesión | Alcance | Modelo/esfuerzo |
|---|---|---|
| O1 | disolución universal + paneles que SE FORMAN de partículas (13 §17) | **Fable, extra** |
| O2 | botones orgánicos + notificaciones-brote + contenido HTML esclavizado a la formación | Opus, alto |
| O3 | vida procedural (luciérnagas/semillas/mariposas; cooldowns ≥20 min; ≤2% partículas) | Opus, alto |
| O4 | memoria visual (madurez log de horas de uso, cambios <2%/semana) + persistencia | Opus, alto |
| O5 | **Project Memory Capa 2 formal** (permisos por proyecto, 08 Capa 2) + **revisión de contratos GSN/CIE** (PortableSkill, PrivacyFilter, aislamiento RFC-001, GuardianRuntime) → handoff documentado a V2.0 | **Fable, extra** |

Cierre V1.6 = Aithera como organismo completo local. **V1.6→V2.0: GSN + CIE**
(plan de sesiones propio al llegar, sobre los contratos revisados en O5).

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

---
*Plan 2026-07-20 (Fable 5, rol CTO+comité). Fuentes: CLAUDE.md (estado real),
docs 09/10/13/14/15/19/24/25/26, investigación Hermes (GitHub NousResearch/
hermes-agent, docs oficiales). Sustituye la tabla V1.1-V1.6 previa del roadmap.*
*Corrección 2026-07-22: AVCS Génesis (V0.82/83) se había construido de
verdad (commits 2026-07-10 a 07-12) cuando este plan se escribió — una nota
de CLAUDE.md del sprint W2b, mal interpretada, decía lo contrario. Retiradas
las sesiones AV1-AV2 de V1.1 (35→33 sesiones totales); sin más cambios de
alcance en el resto del plan. Detalle de la auditoría en doc 03 §2.*
