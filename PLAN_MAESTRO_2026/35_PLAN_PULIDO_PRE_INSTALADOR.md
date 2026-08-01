# 35 — Plan de PULIDO pre-instalador (bloque PU)

> **Propósito**: los últimos ajustes de producto antes de montar el instalador
> (MVP-beta) y hacer el bump a `1.0.0`. Nace de la lista de 14 puntos del
> usuario (2026-07-30), agrupada en sesiones ejecutables con el mismo rigor que
> el bloque de auditoría (doc 34): diseño contrastado contra el código real,
> tests, verificación, cierre en docs. Aithera tiene que ser la estrella de los
> proyectos Jarvis — este bloque es el acabado.
>
> **Convención de sesiones**: `PU-n` (pulido, ejecutables) y `PI-x`
> (investigación → propuesta GO/NO-GO, sin tocar código de producción).
> Cada sesión sigue el protocolo del proyecto: leer `PRINCIPIOS_KARPATHY.md`,
> diseño → implementación → tests → mutación donde aplique → cierre en doc 35
> y CLAUDE.md.

---

## 0. Mapa: los 14 puntos del usuario → sesiones

| # usuario | Tema | Sesión |
|---|---|---|
| 1 | Briefing matutino completo + por voz | **PU4** |
| 2 | AVCS ocupa pantalla completa (queda vacío en modo chat/HUB sin UI) | **PU5** (motor) + **PU6** (layout) |
| 3 | Partículas Q1/Q2: menos partículas pero MÁS GRANDES (misma luminosidad/proporciones) | **PU5** |
| 4 | Modo "Hub sin UI" | **PU6** |
| 5 | Quitar sidebar izquierda → botones inferiores (diseño del usuario pendiente) | **PU6** |
| 6 | Modo claro profesional (nivel UI de Claude) | **PU7** |
| 7 | Autónomo = 100% autónomo, NUNCA pregunta NADA | **PU3** |
| 8 | Política de timeouts en aprobaciones (cuáles expiran, cuáles esperan) | **PU3** |
| 9 | Skills de agentes: que sean REALES (catálogo) y que se USEN | **PU2** |
| 10 | Voces mezcladas en el panel de Voz (Kokoro muestra voces de ElevenLabs) | **PU1** |
| 11 | Auditoría de prompts internos + mapa de inyección | **PU8** |
| 12 | Obscura como opción descargable 1-click | **PI-A** → **PU9** (si GO) |
| 13 | Configuración → Memoria: UI profesional + chat directo a memoria | **PU10** |
| 14 | Obsidian como frontend de la memoria (investigar, propuesta honesta) | **PI-B** |

**Orden recomendado de ejecución** (por dependencias y riesgo):

```
Tanda 1 (quick wins, independientes):   PU1 → PU2 → PU3
Tanda 2 (visual, en este orden):        PU5 → PU6 (requiere diseño del usuario) → PU7
Tanda 3 (funcional):                    PU4 → PU10
Tanda 4 (investigación + cierre):       PU8 · PI-A (→PU9 si GO) · PI-B
```

Justificación del orden: PU7 (modo claro) va DESPUÉS de PU6 porque el
rediseño del Hub crea superficies nuevas que habría que tematizar dos veces si
se hiciera antes. PU4 (briefing) va tras la tanda visual porque su entrega
visible (tarjeta + botón de voz) vivirá en el Hub rediseñado. PU8/PI-A/PI-B son
independientes de todo y pueden intercalarse cuando convenga (p. ej. mientras
el usuario prepara el diseño de botones para PU6).

---

## PU1 · Voces mezcladas en el panel de Voz

**Fallo reportado**: al seleccionar Kokoro en Ajustes → Voz, el listado ofrece
voces de ElevenLabs.

**Punto de partida en código** (`frontend/src/components/voice/VoicePanel.tsx`):
el panel maneja 3 proveedores (`edgetts | elevenlabs | kokoro`) con un mapa
`FALLBACK_VOICES` por proveedor y carga real vía `api.getKokoroVoices()` /
ElevenLabs / EdgeTTS. Hipótesis a verificar (en este orden): (a) el fallback
que se aplica cuando `getKokoroVoices()` falla o tarda usa la lista de otro
proveedor o una lista sin filtrar; (b) el estado `voices` no se limpia al
cambiar de pestaña de proveedor y quedan las del anterior (condición de
carrera: la respuesta lenta de ElevenLabs llega DESPUÉS de cambiar a Kokoro y
pisa el estado); (c) el backend (`/api/voice/...`) devuelve voces sin campo de
proveedor y el panel las mezcla.

**Trabajo**: reproducir → causa raíz → fix. Si es la carrera (b), el patrón del
proyecto es capturar el proveedor al inicio del efecto y descartar respuestas
de un proveedor que ya no es el activo (mismo principio que `sessionId`
capturado en `sendMessage`, fixes post-T4b). Añadir test o, si es puramente de
UI async, verificación en vivo documentada con los 3 proveedores.

**Cierre**: cambiar entre los 3 proveedores repetidamente (incluida red lenta)
nunca muestra voces de otro proveedor.
**Tamaño**: pequeña. **Modelo**: Sonnet, esfuerzo medio.

> **Cierre 2026-07-30 (Sonnet)**: causa raíz confirmada — hipótesis 1
> (carrera). `loadVoicesFor` no descartaba respuestas de peticiones
> superadas: al cambiar de pestaña antes de que la anterior respondiera,
> ganaba la que llegaba última (normalmente ElevenLabs, 2 llamadas HTTP
> encadenadas — status + voces —, más lenta que Kokoro/EdgeTTS), sin
> importar en qué pestaña estuviera el usuario. Fix en
> `frontend/src/components/voice/VoicePanel.tsx`: `loadRequestId` (ref,
> contador) numera cada llamada; `isStale()` se comprueba tras CADA `await`
> (status, lista de voces, y antes de escribir `voices`/`selectedVoice`) —
> una respuesta que ya no es la más reciente se descarta sin tocar el
> estado, incluida `setLoadingVoices(false)` en el `finally` (si no, una
> respuesta vieja podría apagar el "cargando" de la petición nueva).
> **Segunda vía del mismo bug, encontrada al leer el archivo completo (no
> solo el flujo de clic)**: el sondeo de instalación de Kokoro
> (`useEffect` de `kokoroInstalling`) recargaba sus voces al terminar
> `if (st.available) loadVoicesFor("kokoro")` SIN comprobar si el usuario
> seguía en esa pestaña — instalar Kokoro y cambiar a EdgeTTS mientras
> tanto reproducía el mismo síntoma por otro camino. Cerrado con
> `activeProviderRef` (ref sincronizada por efecto con `activeProvider`,
> necesaria porque el intervalo del sondeo captura un closure viejo) +
> guard `activeProviderRef.current === "kokoro"` antes de recargar.
> **Verificación**: `tsc --noEmit` limpio (RC=0, sin errores nuevos). No
> hay test automatizado de este archivo (es UI asíncrona pura, sin
> contrato de backend que testear) — **pendiente en Windows**: cambiar
> rápido entre las 3 pestañas varias veces seguidas (incluida red lenta si
> se puede simular) y confirmar que la lista mostrada siempre corresponde
> a la pestaña activa; instalar Kokoro, cambiar a otra pestaña ANTES de
> que termine la instalación, y confirmar que al terminar NO salta a
> mostrar voces de Kokoro si ya no estás en esa pestaña.

---

## PU2 · Skills reales en agentes (y que se usen)

**Fallo reportado**: "crea un agente con skills para X" asigna skills que no
existen en el catálogo.

**Punto de partida en código** (verificado): el catálogo real es
`frontend/src/data/skillsCatalog.json` (254 entradas / 17 categorías, estático,
generado de `msitarzewski/agency-agents`) y SOLO lo conoce el frontend
(`SkillPickerPopup.tsx`). El backend acepta strings libres en dos sitios:
`POST /api/agents` (`Agent.skills`, JSON) y
`app/tools/aithera_tool.py::create_agent` (`skills: lista de strings opcional`,
sin validación — línea ~341). Cuando el TIE crea un agente por chat, el LLM
inventa nombres con total libertad.

**Trabajo en 3 partes**:
1. **Catálogo en el backend como fuente de verdad**: mover (o copiar con test
   de sincronía) `skillsCatalog.json` a `backend/app/agents/skills_catalog.json`
   + accesor `skills_catalog()` (ids válidos, lazy). Endpoint
   `GET /api/agents/skills-catalog` para que el frontend consuma el MISMO
   archivo (fin de la duplicación).
2. **Validación con sugerencia**: en `POST /api/agents`, `PATCH` y en
   `aithera_tool.create_agent` — skill fuera de catálogo → se rechaza CON
   sugerencia (matching difuso por substring/distancia, mismo espíritu que
   `resolve_model_name` del MEL): el error devuelto al toolloop dice "no existe
   'growth-hacking-expert'; ¿querías 'growth-hacking'?" para que el modelo se
   corrija solo en la siguiente vuelta.
3. **Que las skills SE USEN — auditoría honesta primero**: hoy hay que
   verificar qué hace realmente `Agent.skills` en ejecución. Sospecha fundada:
   son etiquetas de UI que no llegan al prompt del agente. Si es así, el fix es
   quirúrgico: al ejecutar una misión de agente (`agent_manager._delegate_to_tie`
   → `AgentTask`), inyectar las skills en el system prompt del nodo (una línea
   por skill con su descripción del catálogo — el catálogo trae descripciones).
   Si resulta que ya se usan, documentarlo y cerrar solo 1-2.

**Cierre**: pedir por chat "crea un agente con skills de marketing" produce un
agente SOLO con skills del catálogo; un agente con skills asignadas las recibe
en su prompt de ejecución (verificable en el transcript/telemetría).
**Tamaño**: media. **Modelo**: Sonnet, esfuerzo alto.

> **Cierre 2026-07-30 (Sonnet)**: los DOS fallos confirmados y cerrados.
> **(1) Catálogo sin validar**: `backend/app/agents/skills_catalog.json`
> (copia exacta del JSON del frontend, 254/17) +
> `backend/app/agents/skills_catalog.py` (`skill_by_name` case-insensitive,
> `validate_skills` — canonicaliza mayúsculas y RECHAZA con `ValueError`
> listando sugerencias por substring/difflib, `descriptions_for` que omite en
> silencio lo desconocido). Enganchado en `agent_manager.create_agent`/
> `update_agent` — cubre TANTO `POST/PATCH /api/agents` COMO
> `aithera_tool.create_agent` (el camino del chat), porque los dos convergen
> en el mismo `AgentManager`; un solo punto de validación, cero duplicación.
> **Desviación deliberada del plan original** (punto 1: "endpoint
> `GET /api/agents/skills-catalog`"): NO se creó. `SkillPickerPopup.tsx`
> evita a propósito cualquier fetch en tiempo de ejecución (principio de
> autosuficiencia local, doc 09) — el frontend ya tiene su copia estática;
> el backend necesitaba la SUYA para validar en el momento de crear/editar,
> no para servírsela a nadie. Añadir un endpoint solo para que el frontend
> lo consultara habría sido infraestructura sin consumidor real. Riesgo
> aceptado: las dos copias del JSON pueden desincronizarse si el catálogo
> cambia — anotado como deuda menor, no bloqueante (ambas nacen del mismo
> `msitarzewski/agency-agents`, cambia poco). **(2) Skills que nunca llegaban
> a ejecución** (código muerto real, confirmado al trazar
> `_delegate_to_tie`): `agent.skills` se guardaba en BD pero jamás viajaba a
> ningún sitio. Fix reusando el canal YA EXISTENTE que sobrevive al
> checkpoint y llega a cada nodo — `Authority` (doc 23 R4) gana un campo
> `skills` NO-seguridad (nunca entra en `check()`/`is_unrestricted`,
> documentado explícitamente en el docstring para que nadie lo confunda con
> una frontera); `_run_execution`→`_delegate_to_tie`→`pipeline.
> submit_mission` lo pasan hasta `Authority(...)`; `executor._persona_block()`
> (nuevo) lee `graph.authority.skills`, resuelve sus descripciones del
> catálogo y antepone un bloque "Actúas como un agente con estas
> especialidades: …" al contexto de CADA nodo (antes del handoff de S5 y del
> contexto del MOS), con tope de 2000 chars. Se decidió NO añadir un campo
> nuevo a `TaskGraph` — `Authority` ya es el vehículo único que persiste en
> `orchestrator_traces.plan` y se reconstruye en cada nodo; duplicar el
> canal habría sido plomería redundante. Tests: `test_pu2_skills.py` (13 —
> 6 del catálogo puro, 4 de validación en creación/edición/aithera_tool, 3
> de inyección real en ejecución incl. round-trip del checkpoint). 2
> mutaciones confirmadas y restauradas (quitar la validación en
> `create_agent`, quitar `_persona_block` del contexto del nodo) — ambas
> detectadas por los tests. Regresión ejecutada en 3 tandas: 48 (pu2_skills +
> agent_execution + aithera_tool) + 60 (tie_executor + tie_planner +
> tie_handle + module_boundaries) + 34 (tie_e2e + audit_s11_grant +
> orchestrator + orchestrator_e2e) = **142 tests en verde**, sin ninguna
> regresión por el nuevo campo `Authority.skills`, el nuevo kwarg
> `submit_mission(..., skills=…)` ni el cambio de contexto del executor.
> **Pendiente en Windows**: (a) por chat, pedir "créame un agente con skills
> de Growth Hacking Expert" (nombre inventado a propósito) y confirmar que
> Aithera responde con el error y una sugerencia real del catálogo en vez de
> crear el agente; (b) crear un agente con una skill real (p. ej.
> "Anthropologist") desde Ajustes → Agentes y confirmar que se guarda bien;
> (c) lanzarle una tarea real a ese agente y, si hay acceso a los logs o a
> `[tie-perfil]`, comprobar que el prompt de la primera llamada del bucle de
> tool-use incluye el bloque "Actúas como un agente con estas
> especialidades" con la descripción real de esa skill — o, más simple,
> notar si la respuesta del agente refleja esa especialidad de forma
> perceptible frente a un agente sin skills con la misma tarea.

> **Extensión PU2 — 2026-07-30 (Sonnet)**: pregunta del usuario tras el
> cierre — "si le digo al chat 'skills de research y márketing', ¿las sabrá
> elegir solo, o tengo que saberme los nombres exactos?". Respuesta honesta
> con el código real delante: NO, tal como quedó cerrado el bloque anterior,
> `validate_skills` solo distinguía "nombre real" de "no existe" — un
> término suelto como "research" (que ni siquiera es una de las 17
> categorías del catálogo) o "marketing" (que SÍ es una categoría, con 36
> skills, pero el nombre de la categoría no es el nombre de ninguna skill)
> caían en la sugerencia por difflib de siempre, que compara distancia de
> edición y no encuentra nada útil para un término temático. **Fix**:
> `skills_catalog.py` gana dos capas nuevas entre "nombre exacto" y "typo
> por distancia de edición": `_match_category()` (¿el término ES una de las
> 17 categorías, con o sin acento — "márketing" normaliza a "marketing" vía
> `unicodedata`?) y `_keyword_candidates()` (¿el término aparece dentro del
> NOMBRE o la DESCRIPCIÓN de alguna skill real — cubre "research", que no es
> categoría pero sí está en 3 nombres de categorías distintas: UX
> Researcher, Investment Researcher, Trend Researcher?). Cuando cualquiera
> de las dos dispara, el error de `validate_skills` deja de decir solo "no
> existe" y pasa a listar hasta 8 candidatos REALES (orden alfabético,
> determinista, sin inventar un ranking de "relevancia" que el catálogo no
> ofrece) para que el modelo pueda reintentar con nombres concretos en la
> siguiente vuelta del bucle de tool-use — el mismo mecanismo de reintento
> ya usado en el resto del proyecto (planner, resolución de modelos del
> MEL), invisible para el usuario: él solo ve el agente creado un instante
> después, nunca el error intermedio. **Decisión deliberada**: ningún nivel
> SELECCIONA nada por su cuenta — nunca se adivina en silencio (mismo
> principio de todo el proyecto: A3b, A-1, S11); el modelo siempre tiene que
> confirmar con un nombre real antes de que el agente se cree. Verificado
> con las 254 skills reales: "marketing"/"márketing" → categoría, candidatos
> reales de las 36 de marketing; "research" → palabra clave, los 3
> "Researcher" reales entre los candidatos; "Growth Hacking Expert" (el
> typo de la sesión original) sigue cayendo en la sugerencia por
> substring/difflib de siempre, sin colisionar con las capas nuevas — no
> regresión. Tests: `test_pu2_skills.py` +6 (5 de las funciones puras, 1
> end-to-end real con `aithera_tool.create_agent` que prueba el círculo
> completo: categoría suelta → candidatos reales en el error → reintento con
> un nombre real de esos candidatos → agente creado). 2 mutaciones
> confirmadas y restauradas (neutralizar `_match_category` tumba 2 tests,
> neutralizar `_keyword_candidates` tumba 1). Regresión: **54 tests en
> verde** (test_pu2_skills + test_agent_execution + test_aithera_tool).
> **Pendiente en Windows**: por chat, pedir "créame un agente con skills de
> research y márketing" (tal cual, sin nombres exactos) y confirmar que el
> agente termina creado con nombres reales del catálogo (p. ej. algo como
> "Trend Researcher" + una skill real de marketing), sin que tengas que
> corregir nada tú mismo.

---

## PU3 · Autonomía 100% + política de timeouts de aprobación

**Decisión del usuario (cerrada, no ambigua)**: perfil Autónomo = NUNCA
pregunta NADA, sin excepciones. Si un agente necesita una tool que no tenía,
se le concede sola. Para preguntar ya están los otros perfiles.

**Parte A — auditoría de TODOS los puntos donde Aithera pregunta**. El estado
actual ya cubre mucho (`permissions.py::autonomy_is_full()` auto-aprueba
cualquier gate presente o futuro, verificado en S11: el gate de concesión se
auto-concede bajo `full`), pero la instrucción es "sin excepciones", así que la
sesión debe inventariar y decidir UNO A UNO:

| Punto que pregunta | Mecanismo | ¿Bajo Autónomo? |
|---|---|---|
| Gate del plan (`tie_plan`) | ApprovalGate | Auto (ya) — verificar |
| Gate de nodo (`tie.node`) | ApprovalGate | Auto (ya) — verificar |
| Gate de permiso de tool (`tie_tool_permission`) | ApprovalGate | Auto (ya) — verificar |
| Gate de concesión (`tool.grant.*`, S11) | ApprovalGate | Auto (ya, test verde) |
| Checkpoints verificables (R5) | ApprovalGate | Auto — verificar |
| Email send confirm (`/api/email/send`, contrato V0.7) | Flag `confirmed` | **Decidir**: el contrato HTTP está congelado por tests; la vía correcta es que el TIE/toolloop pase `confirmed=true` bajo Autónomo, sin tocar el endpoint |
| Pregunta de alcance del override de modelo ("¿tarea o proyecto?", E2b) | Respuesta de chat | **Decidir**: no es un permiso, es una ambigüedad real — propuesta: bajo Autónomo, default a `task` sin preguntar |
| Desktop tool ("SIEMPRE confirmación", §8) | Confirmación por acción | **Decidir**: es la tool de mayor riesgo físico (ratón/teclado reales); propuesta: bajo Autónomo también se auto-aprueba (la instrucción es "sin excepciones") pero se deja rastro SIEMPRE, y se documenta en la UI del perfil el alcance real de lo que se está activando |

La regla de oro A3b se mantiene intacta: auto-aprobado NUNCA significa
silencioso — todo deja fila en `approvals`. Añadir al selector de perfil en
Ajustes un texto claro de consecuencias ("Autónomo: Aithera no te preguntará
nada, incluidas acciones sensibles como enviar emails o controlar el equipo").

**Parte B — matriz de timeouts (fuera de Autónomo)**. Hoy conviven dos
comportamientos (verificado): el gate de tool del toolloop espera
`approval_wait_s` (~120s) y EXPIRA (A-2/S1, `ApprovalGate.expire()`), mientras
el gate de plan/nodo del executor espera indefinidamente ("el nodo puede
esperar días", T3). Propuesta a ratificar en la sesión:

- **Espera eterna** (la misión queda en `waiting`, reanudable): gate del plan,
  gate de nodo, checkpoints — son pausas de misión, el estado vive en disco y
  no bloquean ningún hilo; expirároslos destruiría trabajo.
- **Expiran** (con expiración VISIBLE, nunca cadáver): gates dentro de un
  toolloop en vuelo (tool permission, tool grant) — ahí hay un bucle vivo
  esperando; propuesta: subir el default de 120s a algo más humano
  (p. ej. 10 min, `Settings.APPROVAL_TOOL_WAIT_S`) y, al expirar, que el nodo
  degrade con la advertencia de limitaciones de S11 en vez de fallar seco.
- Documentar la matriz en este doc al cerrar la sesión.

**Cierre**: con perfil Autónomo activo, una batería de misiones que toque
email + tools + plan sensible + concesión de tool termina SIN una sola
pregunta (y con todas las filas de auditoría en `approvals`); con perfil
manual, la matriz de timeouts se comporta como quedó ratificada.
**Tamaño**: media. **Modelo**: Sonnet, esfuerzo alto (la parte A es
inventario minucioso; hay tests de contrato que proteger).

> **Cierre 2026-07-30 (Sonnet)**: decisión FINAL del usuario, más simple y más
> estricta que la Parte B propuesta arriba — *"aquí en Claude las preguntas se
> quedan INDEFINIDAMENTE hasta que se responden. Creo que debería ser así"*.
> Se descarta por completo la matriz de timeouts propuesta (subir a 10 min,
> degradar con limitaciones al expirar): **ningún gate del toolloop caduca
> ya**, ni el de permiso de tool ni el de concesión (S11) — ambos esperan
> indefinidamente, sondeando cada 1s, hasta `approved`/`rejected` explícitos.
> La única salida sin respuesta es el kill-switch de la misión (T3), exactamente
> igual que ya funcionaba para los gates de plan/nodo/checkpoint (filas 1-3 y 5
> de la tabla de la Parte A: auditados y confirmados correctos SIN tocar
> código, ya cubiertos por `permission_service.autonomy_is_full()` vía
> `is_kind_pre_authorized()`).
>
> **Fila "Desktop tool"**: el usuario eligió *"Sin excepciones también aquí"* —
> confirmado que ya fluye por el mismo permiso `computer.use` sin caso especial;
> sin cambio de código, solo confirmación explícita de que no hay excepción.
>
> **Fila "Email send confirm"**: confirmado NO-ISSUE — `email.send_email` ya
> pasa por el ApprovalGate genérico del toolloop como cualquier acción sensible;
> el flag `confirmed:true` del endpoint HTTP `/api/email/send` es un contrato
> congelado (tests de contrato V0.7) usado solo por la UI del frontend
> directamente, ajeno al TIE/toolloop — no había nada que decidir aquí.
>
> **Fila "Alcance del override de modelo" (E2b)**: única fila que SÍ pedía
> código. `tie/pipeline.py::_resolve_explicit_model`, rama `scope ==
> "unspecified"`, gana un chequeo de `permission_service.autonomy_is_full()`
> ANTES de preguntar: bajo Autónomo asume `scope=task` sin preguntar y antepone
> una nota transparente a la respuesta de ese turno (nueva clave i18n
> `pipeline.model_scope_auto_task`, 4 idiomas) — nunca en silencio, coherente
> con la regla de oro de A3b. Fuera de Autónomo, sigue preguntando exactamente
> igual que antes (rama sin cambios).
>
> **Código tocado**: `app/tie/toolloop.py` (`_wait_gate` reescrito sin deadline;
> `_ask_permission`/`_ask_grant` pierden el parámetro `wait_s`; un rechazo de
> permiso ahora también se registra en `ToolLoopResult.limitations`, hueco real
> encontrado al implementar — antes solo se anotaba en el transcript y el
> responder nunca se enteraba de la limitación) · `app/tie/runtime.py` (deja de
> pasar `approval_wait_s`) · `app/core/config.py` (retirado
> `TIE_TOOL_APPROVAL_WAIT_S`) · `app/core/strings.py` (+1 clave ×4 idiomas) ·
> `app/tie/pipeline.py` (el chequeo de autonomía en `_resolve_explicit_model` +
> la nota antepuesta en `handle_stream`/`_run_pipeline`; deliberadamente NO
> aplicado a `submit_mission` ni al camino de misión compleja — alcance
> acotado al camino corto/directo donde vive la pregunta original).
>
> **Hallazgo real durante la implementación** (no un bug de producción, un
> test que quedó obsoleto por el cambio de diseño): dos tests existían
> específicamente para probar la EXPIRACIÓN (`test_tie_toolloop.py`'s
> `test_sin_respuesta_a_tiempo_expira_y_falla_honesto`,
> `test_product_contracts.py`'s Contrato 4
> `test_contrato_la_aprobacion_caducada_no_queda_pendiente`) — con la decisión
> nueva, ambos habrían colgado indefinidamente si se hubieran dejado tal cual
> (`await handle(...)`/`await toolloop.run(...)` esperando una respuesta que el
> test nunca da). Reescritos como el contrato contrario: se lanza la ejecución
> en segundo plano (`asyncio.create_task`), se confirma que NO decide nada por
> su cuenta mientras espera (disco intacto, `Approval` sigue `pending`, la task
> no está `done()`), y solo entonces se resuelve explícitamente (aprobando en
> uno, rechazando en el otro) para confirmar que retoma con normalidad. El
> Contrato 4 del archivo de contratos de producto se renombró a *"Si te
> pregunto, espero a que respondas — no me invento nada"*, más fiel al
> comportamiento real ya que "caducar" dejó de existir. De paso, las pruebas de
> este archivo pasan de 8/13 ejecutables en el presupuesto del sandbox (5
> exigían 120s reales de espera) a **13/13 en ~4s** — la propia decisión hizo
> la suite más rápida, no solo más simple.
>
> **Verificación**: 3 mutaciones quirúrgicas (neutralizar el bucle infinito de
> `_wait_gate`, neutralizar el `limitations.append` de un rechazo, neutralizar
> el chequeo de `autonomy_is_full()` en `_resolve_explicit_model`) — las tres
> detectadas por tests específicos, restauradas y verificadas byte-idénticas
> (`diff -q`). Regresión: 100 tests en verde en el subconjunto directo
> (toolloop/contratos/explicit_model/S11/S7·S8/orchestrator_chat/permissions) +
> 375 passed / 6 skipped en el subconjunto amplio (todo `test_tie_*`,
> `test_automation*`, `test_orchestrator*`, `test_audit_s*`,
> `test_agent_execution`), sin ninguna regresión atribuible a este cambio.
> **Pendiente en Windows**: (1) disparar una acción sensible (p. ej. pedirle al
> chat que envíe un email) con perfil Manual o Balanced, esperar bien pasados
> los 120s que antes hacían expirar la aprobación, y confirmar en Ajustes →
> Automatización que sigue `pending` (no `expired`) — luego aprobarla y
> confirmar que se ejecuta; (2) con perfil Autónomo activo, pedir algo que
> nombre un modelo sin decir alcance (p. ej. "usa Claude para esto") y
> confirmar que Aithera responde directamente con una nota tipo "uso Claude
> para esta petición… con Autónomo activo no te lo pregunto" en vez de
> detenerse a preguntar "¿solo esta vez o para siempre?".

---

## PU4 · Briefing 2.0 + briefing por voz

**Referencia investigada** (OpenJarvis "Morning Digest", docs oficiales): 5
bloques con narrativa hablada por TTS y persona — (1) qué pasó desde ayer,
(2) los 2-3 emails que de verdad requieren acción con resumen de una línea,
(3) agenda de las próximas 24h, (4) proyectos/trabajo (en su caso GitHub),
(5) un ítem de seguimiento. La clave no es la cantidad de datos sino la
SÍNTESIS priorizada + la entrega por voz.

**Punto de partida en código**: `app/memory/summarizer.py` (resumen nocturno
03:30, `gather_day_data`), `GET /api/memory/briefing` (ya devuelve: resumen,
urgentes pendientes, agenda del día, top remitentes y — desde W4 — el bloque
`workspace`: milestone activo + progreso, deadlines 7d, tareas alta prioridad,
bloqueos), tarjeta "Memoria" del Hub, regla AE `daily_briefing` (08:00,
Telegram), `voice/text_clean.py::clean_for_speech()`, pipeline TTS por frases
de `Chat.tsx` (VZ1). Casi todos los ingredientes EXISTEN — la sesión es de
composición, no de infraestructura.

**Trabajo**:
1. **Estructura nueva del briefing** (`app/memory/briefing.py` NUEVO o
   extensión del summarizer — decidir en sesión según tamaño): secciones
   ordenadas por accionabilidad: 🔴 urgente hoy (emails urgentes sin atender +
   deadlines de hoy + bloqueos) → 📅 agenda 24h → 📧 emails que piden acción
   (2-3, con resumen de 1 línea vía triaje YA calculado, cero LLM extra) →
   📁 proyectos (progreso, milestone activo, qué se movió ayer) → 📰 noticias
   (NUEVO: 2-3 titulares vía `search_tool` news, con los temas de interés del
   usuario — configurable en Ajustes, default: sin noticias si no hay
   proveedor de búsqueda configurado, degradación honesta) → ✅ resumen de
   ayer. La síntesis en lenguaje natural la hace el MEL (SUMMARIZE, política
   economy como el summarizer) con plantilla determinista de respaldo (patrón
   M3, obligatorio).
2. **Versión hablada**: el texto del briefing pasa por `clean_for_speech()` y
   se entrega con una narrativa pensada para voz (no leer la tarjeta:
   redactar 30-60s de locución, persona activa de `personalities.py`).
   Disparadores: botón ▶ en la tarjeta del Hub, y por chat/voz ("dame el
   briefing", "¿qué tengo hoy?") — añadir el patrón a `action_intent`/
   `capabilities_map` para que enrute determinista, sin planner.
3. **Endpoint aditivo** `GET /api/memory/briefing?spoken=true` (o campo
   `spoken_text` en la respuesta actual — decidir, contrato aditivo siempre) y
   ajuste de la regla AE `daily_briefing` para usar la estructura nueva.

**Decisión pendiente (usuario) — ✅ RESUELTA (2026-08-01)**: el usuario pidió
AMBOS, no uno u otro — "que el Briefing se active solo a las 8.15h... pero
también que lo pueda activar yo con un botón". Noticias: confirmado fuera de
alcance de esta sesión ("la selección de noticias la haremos después de
tener la base hecha").

**Cierre — ✅ HECHA (2026-08-01, Sonnet)**: implementado con dos diferencias
honestas respecto al plan original de arriba, ambas por instrucción directa
del usuario en esta misma sesión (no desviaciones silenciosas): (1) sin
bloque de noticias — deferido a una sesión futura, tal como se pidió; (2) sin
tarjeta en el Hub con botón ▶ — el Hub de PU6a ya no tiene tarjetas (Hub sin
UI), así que el disparador manual es el `BriefingButton` nuevo del dock,
junto a Modo Presencia, con icono propio de amanecer. Todo lo demás según
plan: `GET /api/memory/briefing` devuelve `spoken_text`/`spoken_source`
(aditivo) con datos reales; el botón del dock y el disparo automático de las
8:15 lo narran por la voz activa (`Chat.tsx::speak()`); "dame el briefing"/
"¿qué tengo hoy?" por chat y por voz responde sin LLM en la clasificación
(`quick_answers.try_answer_async`, enganchado en el TIE y en el Orquestador).
**La regla AE `daily_briefing` (Telegram 08:00) NO se tocó** — deliberado,
para minimizar riesgo; el usuario no lo pidió y el formato actual funciona.
Detalle completo, archivos tocados y pendientes de verificación en Windows:
`CLAUDE.md` §27.

**Extensión PU4b — ✅ HECHA (2026-08-01, Fable 5)**, tres encargos directos
del usuario sobre esta base: (1) pestaña **Ajustes → Briefing** — secciones
on/off, N horarios al día con job de PREPARACIÓN ~30 min antes de cada uno
(noticias + locución a cache, re-armado en caliente al guardar), temas de
noticias añadibles + fuentes bloqueadas/preferidas + prompt de intereses;
(2) **noticias reales** vía search_tool (SerpAPI→Brave) con filtro
determinista de dominios y curación MEL (economy) guiada por el prompt —
defaults: los 5 temas del usuario y su criterio anti-clickbait; solo
titular + resumen de 1 línea; (3) el **show visual sincronizado con la
voz** — `spoken_segments` deterministas con `focus` por paso; tarjetas de
email/calendario (días remarcados, el mencionado pulsando)/proyectos/tareas
en la esquina izquierda, y pantalla completa de noticias por columnas con
el titular locutado enmarcado, scroll e vídeo interactivos. De regalo
forzoso: fix de la regresión que dejó el chat clic-through (la entrega de
PU4 pisó el hotfix del `calc()`; ver CLAUDE.md §27 PU4b). 18 tests nuevos.
Detalle completo en `CLAUDE.md` §27.

**Hotfix noticias post-PU4b — ✅ HECHO (2026-08-01)**: el usuario probó el
módulo de noticias y reportó dos fallos concretos — resultados desactualizados
(un tema de geopolítica española trajo un debate viejo en vez del conflicto
real de ese día) y vídeos/documentales colándose como "noticia" ("noticias
son noticias, otra cosa es información"). Fix: ventana de actualidad por
tema (`freshness` d/w/m, Brave `freshness=`/SerpAPI `tbs=qdr:`) + bloqueo por
defecto de YouTube/Vimeo/Dailymotion + reglas explícitas de qué cuenta como
noticia en el prompt del curador LLM. Bug real corregido de paso: un "vacío
explícito" del curador (decidió que ningún candidato era noticia real) se
rellenaba igualmente con el respaldo determinista, anulando la regla justo
cuando debía aplicarse. 4 tests nuevos. Detalle completo en `CLAUDE.md` §27.

---

## PU5 · AVCS: equilibrio de partículas Q1/Q2 + escala a pantalla completa

**Regla previa e innegociable** (2 correcciones del usuario en el pasado): el
AVCS es la IDENTIDAD de Aithera — NUNCA se adapta al tema, escenario oscuro
fijo. Esta sesión toca DENSIDAD y ESCALA, jamás colores/diseño.

**Fallo 1 (punto 3)**: en los tiers Q1/Q2 (hardware modesto, del scanner de
`core/hardware.py`), la reducción del número de partículas hace que las líneas
y la forma del núcleo apenas se vean. **Principio del fix**: presupuesto de
LUMINOSIDAD constante, no de partículas — al bajar N, subir proporcionalmente
el tamaño de punto (`gl_PointSize`/size del shader) y/o la opacidad, de modo
que la energía visual total y las proporciones del diseño se conserven.
Aproximación concreta: definir por tier un par `(N, sizeFactor)` calibrado a
ojo con captura comparativa (Q4 como referencia), p. ej. si Q1 tiene N/4
partículas, su sizeFactor ≈ ×1.8-2.2 (la percepción de área no es lineal — se
calibra en vivo, no por fórmula). Verificación: capturas de los 4 tiers lado a
lado, mismo encuadre.

> ⚠️ **CORRECCIÓN (2026-07-30, tras implementarlo y que el usuario lo
> rechazara): la parte de "subir el TAMAÑO de punto" de este diseño es ERRÓNEA
> — no la implementes.** Cada partícula se pinta con un degradado radial que
> ocupa todo el radio del quad (`glow = smoothstep(0.5, 0.0, d)` en
> `render.frag.glsl`), así que agrandar `gl_PointSize` agranda el degradado en
> la misma proporción: el resultado es una MANCHA BORROSA, no "el mismo diseño
> más grande". Se probó con los factores de arriba y el AVCS se volvió
> progresivamente borroso al bajar de Q4 a Q1. La vía correcta —implementada y
> descrita en el cierre de esta sección— es subir **solo la opacidad**
> (`brightBoost`, canal alpha), que compensa la luz perdida sin tocar ni la
> geometría del punto ni el perfil del degradado: misma nitidez exacta. La
> mención a "y/o la opacidad" de este párrafo era la buena; la del tamaño, no.

**Fallo 2 (parte del punto 2)**: en modo chat/pantalla completa el núcleo
queda pequeño y la pantalla medio vacía. Fix: el contenedor de
`AitheraPresence`/`AICore.tsx` debe escalar el conjunto (cámara/FOV o scale
del grupo) según el viewport real del modo — en fullscreen-sin-UI el núcleo
debe ocupar la proporción protagonista (~60-70% de la altura), con las
partículas ambientales llenando el resto del lienzo. Parametrizar como
`presenceScale` por modo, no hardcodear.

**Cautela técnica**: `AICore.tsx` lleva shaders custom y arrastra la etiqueta
histórica "no tocar". Se toca SOLO: uniforms/props de densidad, tamaño y
escala. Cualquier cambio se verifica en vivo con los 4 tiers y en ambos temas
(el escenario oscuro fijo debe seguir pixel-idéntico en claro).

**Cierre**: Q1/Q2 se ven con el MISMO diseño y luminosidad aparente que Q4
(menos partículas, más grandes); en pantalla completa el núcleo ocupa el
protagonismo; FPS estable en el tier bajo (medir antes/después).
**Tamaño**: media. **Modelo**: Sonnet, esfuerzo alto (es calibración visual
iterativa más que código complejo).

> **Cierre 2026-07-30 (Sonnet) — Fallo 1 (partículas Q1-Q4). CUARTA versión.
> Las tres anteriores se entregaron mal.**
>
> **Historial de fallos (para que no se repitan):** (1) escalar `gl_PointSize`
> ×8 sin más → BORROSO, porque cada partícula es un degradado radial y agrandarla
> agranda la mancha. (2) compensar solo el BRILLO → no emborronaba pero no
> arreglaba nada. (3) redistribuir partículas hacia el logo → se perdían anillos
> y bandas, o sea medio diseño del AVCS. **El usuario lo dijo tres veces y con
> razón: "no es cuestión de distribuir los puntos, es que sean más grandes y
> luminosos sin que sean borrosos", y la luminosidad de Q1 debe ser la MISMA que
> la de Q4.**
>
> **Lo que faltaba: medir en vez de opinar.** Se construyó
> `frontend/scripts/avcs-preview/` (renderizador CPU con la geometría y la config
> REALES: proyección, `gl_PointSize`, perfil de glow, blending aditivo, DPR y —
> tras corregirlo— el clamp de `gl_FragColor` a [0,1] que hace WebGL). Con él se
> mide la **luminosidad total de la escena** (suma de energía del framebuffer),
> que es la métrica objetiva de "se ve igual de luminoso", y se calibra por
> bisección el tamaño/brillo de cada tier hasta igualar la de Q4.
>
> **El dato que cierra el debate**: con el clamp real, **el brillo NO puede
> sustituir al tamaño** — con un punto de solo ×2.0, ni subiéndolo ×30 se pasa
> del 36% de la luz de Q4, porque la opacidad satura en 1.0 y deja de sumar. La
> luz que aporta una partícula es área × opacidad; con 64× menos partículas, el
> ÁREA es la única palanca capaz de cerrar la diferencia. De ahí los factores
> grandes, que no son un capricho sino el resultado de la medición.
>
> **Configuración final** (todos verificados al 99-100% de la luz de Q4):
>
> | tier | partículas | tamaño | brillo | dureza de borde | luz vs Q4 |
> |---|---|---|---|---|---|
> | Q1 | 4 096 | ×4.00 | ×1.58 | 0.42 | **100.2%** |
> | Q2 | 16 384 | ×2.00 | ×1.60 | 0.42 | **99.9%** |
> | Q3 | 65 536 | ×1.45 | ×0.69 | 0.42 | **99.3%** |
> | Q4 | 262 144 | ×1.0 | ×1.0 | 0.0 | 100% (referencia intacta) |
>
> **Por qué NO sale borroso pese al ×4**: `edgeHardness` (nuevo uniform
> `uEdgeHardness`, umbral interior del `smoothstep` del fragment). Con 0.42 el
> punto es un DISCO SÓLIDO con un borde de antialiasing corto — un círculo
> grande y nítido, no una nube. En Q4 vale 0.0 → el degradado de siempre, sin
> tocar. Ésta es la pieza que faltaba en el intento nº1.
>
> **El diseño no se toca**: el reparto del pool vuelve a ser IDÉNTICO en los 4
> tiers (`lotus.ts` sin `logoScale`/`strokeTighten`; los anillos, bandas y
> starfield son parte del AVCS, no relleno). Q4 conserva sus cuatro factores
> neutros exactos, así que es bit a bit el de siempre.
>
> **Verificación**: `tsc --noEmit` limpio; luminosidad de los 4 tiers medida
> desde la config real del código (tabla de arriba); comparativa visual
> generada. **Pendiente en Windows**: recorrer Q4→Q3→Q2→Q1 y confirmar que los
> cuatro tienen la misma presencia luminosa, que ninguno se ve borroso y que Q4
> está intacto. Si algún tier pide retoque son 3 números por fila en
> `constants.ts`, y el previsualizador permite verlo antes de tocar la app.

> **Cierre PU5b 2026-07-31 (Sonnet) — 4 peticiones sobre el AVCS tras ver el
> resultado de PU5.** Todas verificadas con el previsualizador
> (`frontend/scripts/avcs-preview/`) salvo lo que depende de la simulación.
>
> **1 · Q1 ELIMINADO.** Decisión del usuario: *"no llega al mínimo visualmente
> bueno estéticamente y hoy la gente tiene ordenadores suficientes para Q2
> SEGURO"*. Con 4096 partículas, ni con el tamaño ×4 calibrado el resultado era
> presentable. Retirado de los 8 puntos donde vivía: `QualityTier` (el tipo pasa
> a `"Q2" | "Q3" | "Q4"`, así que TypeScript caza cualquier uso olvidado),
> `TIERS`, la escalera de `PerformanceManager` (nunca baja de Q2),
> `WelcomeOverlay`, `Settings`, las 3 claves ×4 idiomas de i18n, y
> `hardware.py` (donde Q2 pasa a rotularse "Mínimo" y es lo que se recomienda a
> cualquier equipo sin GPU dedicada). **Detalle que habría roto la app**:
> `useAppStore` valida el tier guardado en `localStorage` — un usuario con "Q1"
> persistido se habría quedado con un tier inexistente, así que se migra
> explícitamente a Q2.
>
> **2 · RAÍCES (tendrils) ELIMINADAS.** Eran las líneas doradas que sobresalían
> del contorno (`FRAC.tendrils`, ROLE.SUB, bloque 5 de `lotus.ts`). Fuera el
> bloque entero. Su cuota del pool (0.07) se reasigna: 0.04 a los anillos —que
> ganan definición, y es justo lo que pedía la petición 3— y el resto lo absorbe
> el campo de fondo. El **polvo interior** SÍ se mantiene: comparte rol pero
> está DENTRO de la silueta, no sobresale.
>
> **3 · ANILLOS QUE MANTIENEN LA FORMA (~90% rígidos, no 100%).** Se deformaban
> demasiado por DOS causas que actuaban juntas: (a) su `bind` era 0.45, la mitad
> que el del logo (0.93); (b) aunque el bind fuera alto, el *wander* lo aflojaba
> periódicamente hasta un 70% (`effBind = bind * (1 - 0.7*w)`), y con
> `wanderAllow(0.38) ≈ 0.83` los anillos vagaban casi tanto como el campo
> libre. Arreglado en los dos sitios: `RING_BIND` 0.45 → **0.88** (≈95% de la
> rigidez del logo) y el wander de los anillos ×0.12 en `computeForce`. Además
> su dispersión en Z baja de 0.1 a 0.028 para que se lean como una LÍNEA
> circular y no como un toro visto en perspectiva. Conservan el micro-jitter de
> radio (±1%): un círculo de compás perfecto no pegaría con el resto del AVCS.
>
> **4 · LOS ANILLOS GIRAN, cada uno en su plano.** Explícitamente distinto del
> anillo del núcleo, que usa `rotY` (eje Y) y por eso al alinearse con la vista
> se ve de canto y parece una línea. Los 5 anillos usan una rotación nueva en
> **Z** (`spinRing` en `fields.glsl`): ruedan sobre sí mismos manteniendo su
> posición, sin bascular nunca.
> · **Sentido alterno**: el más externo hacia la derecha (horario), el
>   siguiente a la izquierda, y así los 5 — `dir = mod(idx,2)<0.5 ? -1 : +1`.
> · **Velocidad progresiva**: los de fuera lentos, los de dentro rápidos —
>   `pow(RING_SPIN_RATIO=1.32, 4-idx)`, así el interior gira ~3× más que el
>   externo.
> · **Reposo tranquilo**: 0.055 rad/s en el externo = una vuelta cada ~114 s; el
>   más interno, una cada ~38 s. Presente pero contemplativo.
> · **CONFIGURABLE POR ESTADO** (lo pedido para más adelante):
>   `RHYTHM_RING_SPIN` en `constants.ts` da la velocidad de cada uno de los 7
>   ritmos; `RhythmEngine` la persigue con crossfade e integra el ÁNGULO
>   ACUMULADO, no una fase — así cambiar de estado acelera o frena de forma
>   continua, sin saltos de posición. Las animaciones finas de
>   escucha/habla/pensamiento son otra sesión; el mando ya está puesto.
>
> El índice de anillo se deriva del RADIO del ancla (`ringIndex`), sin gastar un
> canal del genoma (que está lleno: seed/rol/tamaño/brillo). Eso obliga a
> replicar radios y centro en el shader — hay comentario cruzado en `lotus.ts` y
> en `fields.glsl` advirtiéndolo.
>
> **Verificación**: `tsc --noEmit` limpio · **`glslcheck.cjs` NUEVO** (valida
> los shaders con los includes resueltos: un error de sintaxis en GLSL deja el
> AVCS en negro y no lo cazaba nada) · luminosidad remedida tras el cambio de
> reparto (Q3 100.1%, Q2 101.3% de Q4 — la calibración de PU5 aguanta) ·
> `hardware.py` probado con 3 perfiles de equipo (recomienda Q4/Q3/Q2) · grep
> confirmando que la única mención a "Q1" que queda es la migración deliberada.
> **Pendiente en Windows** (el previsualizador es ESTÁTICO y no simula
> dinámica): confirmar en la app que los anillos (a) mantienen la forma de
> círculo, (b) giran en su sitio sin bascular, (c) alternan sentido y (d) los
> interiores van más rápido; y que ya no hay selector de Q1 en Ajustes.

> **Cierre PU5c 2026-07-31 (Sonnet) — 5 peticiones más sobre el AVCS.**
>
> **1 · Anillos +50% de brillo** (`RING_BRIGHT` en `lotus.ts`). Se veían
> apagados frente al logo. `put()` clampa el brillo a 1, así que los nodos —que
> ya rozaban el techo— saturan; lo que sube de verdad es el cuerpo del anillo,
> que es lo que se percibía oscuro.
>
> **2 · Variedad de tamaños en los anillos** (`RING_NODE_FRACTION` 0.05 → 0.16).
> Un 16% de sus partículas son ahora "nodos": notablemente más grandes y
> brillantes, como ya ocurría en los contornos del logo. Antes los anillos se
> leían planos y uniformes porque solo un 5% destacaba.
>
> **3 · "Bloom" periódico de los anillos** (uniform nuevo `uRingBloom`). De vez
> en cuando se recogen hacia el núcleo y se vuelven a expandir hasta su sitio,
> repitiendo la animación de entrada. Detalles de diseño: es **Poisson, no
> periódico exacto** (media 38 s, `RING_BLOOM_INTERVAL_S`) para que no se vuelva
> previsible — mismo criterio que el latido del núcleo; la re-expansión la hace
> el DECAIMIENTO de la envolvente (no una animación aparte), con curva
> `pow(env,1.6)` para que salga rápido del centro y llegue despacio a su sitio;
> y hay **desfase por anillo** (`idx*0.07`) para que la expansión se lea como una
> onda del centro hacia fuera y no como un salto simultáneo. En reposo el
> uniform vale 0: coste cero cuando no está ocurriendo.
>
> **4 · ONDAS DE SINCRONÍA largas y ondeantes.** `BAND_REACH` 4.2 → **7.6**: se
> extienden bastante más allá del contenido garantizado en cuadro, así que
> cruzan la pantalla de lado a lado y mueren desvanecidas por el `edgeFalloff`
> del fragment en vez de cortarse en seco a media pantalla. Y ondean de verdad
> (`targetAnchor` en `fields.glsl`), con tres capas: una onda VIAJERA (el
> término `- uTime` hace que el patrón se desplace, así la banda "corre" en vez
> de vibrar en el sitio), un armónico más corto en sentido contrario (la S nunca
> se repite igual), y amplitud CRECIENTE hacia los extremos (nace contenida
> junto al núcleo y se abre al alejarse). El **origen también deriva**: un
> término lento sube y baja la banda cerca del núcleo, ponderado por
> `1 - smoothstep(0, 2.4, |x|)` para que solo afecte al arranque.
>
> **5 · Zoom y órbita con el ratón.** Arrastrar gira el AVCS; **al soltar vuelve
> solo al frente** (el objetivo se pone a 0 y el grupo lo persigue con un
> suavizado más lento que el del arrastre, así que el retorno se lee como un
> gesto y no como un resorte). La rueda hace zoom y ese SÍ persiste. Detalles:
> · La órbita es una rotación RÍGIDA del grupo (`object3D.rotation`), no toca la
>   simulación ni deforma nada.
> · Topes de ±40°/±25°: el AVCS es esencialmente plano (vive en XY), así que más
>   ángulo lo pondría de canto y perdería toda su lectura.
> · El fit-contain de la cámara pasa a calcularse con la distancia BASE en vez
>   de la actual — si no, al redimensionar la ventana el FOV se recalcularía con
>   la cámara ya acercada y "desharía" el zoom del usuario.
> · `pointerEvents` solo se activa donde el AVCS es visible (`/` y `/chat`), y
>   el contenedor vive al fondo (z-0): los paneles y controles de la UI van
>   encima y siguen recibiendo sus eventos primero, así que aquí solo llegan los
>   clics sobre zonas vacías.
>
> **Verificación**: `tsc --noEmit` limpio · `glslcheck.cjs` valida los shaders
> tras los cambios · luminosidad remedida (Q3 99.9%, Q2 100.2% de Q4 — el +50%
> de los anillos no descalibra el conjunto porque sube en los tres por igual) ·
> el previsualizador confirma anillos más brillantes y con nodos, y ondas
> cruzando de lado a lado. **Pendiente en Windows** (el previsualizador es
> ESTÁTICO — nada de lo animado se ve ahí): el bloom periódico de los anillos
> (esperar ~40 s), el ondeo de las bandas, y el zoom/giro con el ratón.

> **Cierre PU5d 2026-07-31 (Sonnet) — 4 ajustes + un BUG real encontrado.**
>
> **1 · Faros en los anillos (7%)**: tres escalones de tamaño en vez de dos —
> 7% de FAROS claramente mayores y a brillo pleno (no se atenúan con la
> modulación `thin` del anillo, para que se lean como puntos de luz sueltos),
> ~12% de nodos medios, y el resto polvo fino. Un solo `rand()` decide el
> escalón con rangos que no se solapan, así que las proporciones son exactas.
>
> **2 · Más de 2 ondas de sincronía a la vez — causa medida.** Las ondas nacían
> con un Poisson de media `RHYTHM_BREATH_PERIOD` (7 s en reposo) y cada una vive
> ~5,4 s (muere cuando su amplitud decae bajo 0.004). El número MEDIO de ondas
> vivas simultáneas era por tanto 5,4/7 ≈ **0,8**: casi siempre 0 ó 1, a veces
> 2, prácticamente nunca 3 — exactamente lo que se veía. Nuevo
> `WAVE_BIRTH_DIVISOR = 3`: la media de nacimiento baja a ~2,3 s y las
> simultáneas suben a ~2,3 de media, con ratos de 4-5 y ratos de una sola. Sigue
> siendo Poisson, así que es aleatorio y vivo, no un metrónomo. El techo lo
> sigue poniendo `maxWaves` del tier (5-6).
>
> **3 · Ondas que ondean de verdad.** La amplitud máxima pasa de 0.44 a **1.25**
> (antes la onda apenas se insinuaba) y la frecuencia espacial de 0.78 a 1.15 —
> con el alcance de 7.6 eso da ~1,4 ciclos por lado, o sea crestas y valles
> claros en vez de una curva perezosa. **La velocidad temporal NO cambia** (0.55
> y 0.31, las de antes): lo que faltaba era recorrido vertical, no ritmo. El
> ORIGEN cerca del núcleo pasa de 0.26 a 0.62 de recorrido y usa dos frecuencias
> inconmensurables (0.21 y 0.135) para que el arranque nunca repita el mismo
> vaivén.
>
> **4 · EL "APAGÓN" GLOBAL — era un bug real, con causa concreta.** Síntoma
> reportado: todo el AVCS bajaba de intensidad y luego volvía de golpe.
> Causa: en `render.vert.glsl`, una partícula alejada de su ancla perdía hasta
> el **65% de brillo y el 68% de tamaño** (`mix(0.35,...)` y `mix(0.32,...)`
> sobre `closeness`). Como la luz que aporta es área × opacidad, eso es caer a
> ~1/9 de su luz. Y hay DOS gestos que desplazan muchísimas partículas a la vez
> cada pocos segundos: el latido (`fPulse`, Poisson ~6,5 s) y cada onda de
> sincronía. De ahí el patrón exacto de "apagón → destello": no era un caso
> raro, era el comportamiento normal amplificado por dos eventos globales.
> Arreglo: suelos a **0.82** (brillo) y **0.70** (tamaño). La partícula que
> viaja sigue atenuándose un poco —el efecto de "se suelta y vuelve" se
> conserva— pero ya no puede arrastrar la luminosidad del conjunto. Nota: este
> arreglo era además **necesario** para el punto 2, porque más ondas
> simultáneas habrían agravado el apagón.
>
> **Verificación**: `tsc` limpio · `glslcheck` OK · luminosidad remedida
> (Q3 100.7%, Q2 99.3% de Q4) · el previsualizador muestra los faros ensartados
> en los anillos. **Pendiente en Windows**: que el apagón haya desaparecido
> (mirar un minuto seguido, que es cuando se notaba), el ondeo de las bandas, y
> contar si a veces hay 3-4 ondas a la vez.

---

## PU6 · Hub sin UI + botones inferiores (adiós sidebar)

**Lo que pide el usuario**: (4) un modo "Hub sin UI" — sin panel lateral, sin
tarjetas: solo el AVCS + lo mínimo; (5) sustituir la sidebar izquierda por una
botonera inferior ("botones guays" — **EL USUARIO ENVIARÁ EL DISEÑO cuando se
trabaje esta sesión**; no empezar sin él); (2) que el AVCS llene la pantalla
en ese modo (entregado por PU5, aquí se consume).

**Punto de partida en código**: `components/layout/` (`AppLayout`, `Sidebar`),
`Hub.tsx` (grid 3 columnas con paneles), `useAppStore.presenceMode` (ya existe
un concepto de modo de presencia persistido), F11 fullscreen de Electron.

**Trabajo**:
1. **Modo Hub sin UI**: un estado más de `presenceMode` (p. ej.
   `"immersive"`): oculta sidebar y paneles, AVCS a pantalla completa (escala
   de PU5), la etiqueta central y una entrada de chat/voz mínima flotante.
   Entrar/salir: botón en el Hub + tecla (propuesta: `Esc` sale, como el
   fullscreen actual) + por voz ("modo inmersivo" / "pantalla completa").
2. **Botonera inferior**: reemplaza la Sidebar como navegación principal en
   TODAS las páginas (no solo el Hub). Los ítems actuales de la Sidebar
   (Hub, Chat, Workspace, Misiones, Automatización, Calendario, Email,
   Agentes, Ajustes + indicador de modelo/estado del MEL) migran a botones
   inferiores según el diseño del usuario. La Sidebar se retira (tombstone o
   eliminación, según el patrón del proyecto). Cuidado con: el indicador
   `chatPrimary`/breaker (MEL-UI, §25) debe seguir visible en la botonera; el
   deep-link `location.state.tab` de Ajustes debe seguir funcionando.
3. **Paneles del Hub**: en el modo normal (con UI), el Hub conserva sus
   tarjetas (proyectos activos, tareas, agentes, eventos, chat reciente,
   email, memoria) — el punto 4 del usuario lista exactamente las que ya
   existen; se reorganizan alrededor de la botonera nueva según el diseño.

**Dependencias**: diseño de botones del usuario (bloqueante para empezar);
PU5 cerrada (escala del AVCS).
**Cierre**: navegación completa por botonera inferior en todas las páginas,
modo inmersivo entra/sale limpio (clic, tecla y voz), nada de la
funcionalidad actual se pierde (checklist de ítems de la Sidebar vieja),
`tsc`/build limpios + verificación en vivo en ambos temas.
**Tamaño**: grande. **Modelo**: Opus (rediseño de layout con muchas
interacciones), o Sonnet esfuerzo máximo si el diseño del usuario llega muy
cerrado.

---

## PU7 · Modo claro profesional

**Lo que pide el usuario**: el modo claro actual "se ve feo, hay cosas que no
cuadran y es incómodo" — el listón es una UI al nivel de la de Claude.

**Punto de partida**: variables CSS por tema en `styles/index.css`
(`:root,.dark` / `.light`), escala de grises ya establecida (lienzo 224,
tarjetas 238, NUNCA blanco puro ni el AVCS tocado — reglas previas del
usuario). El problema no es la infraestructura sino el ACABADO: contrastes,
jerarquía, estados hover/focus, bordes, sombras, y componentes que quedaron a
medias.

**Trabajo (pasada sistemática, no parches)**:
1. **Inventario visual**: recorrer TODAS las páginas y modales en claro con
   capturas, listando cada elemento roto/incómodo (texto con poco contraste,
   bordes que desaparecen, el borde azul eléctrico `.glass-surface` pensado
   para oscuro, badges/toggles/chips, tablas del miniMarkdown, scrollbars,
   estados de error/warning). El listado ES el contrato de la sesión.
2. **Sistema, no casos**: resolver en las VARIABLES (añadir las que falten:
   `--panel-border-light`, sombras por elevación, escala de acentos para
   claro) y no con overrides sueltos por componente. Criterios objetivos:
   contraste WCAG AA mínimo para texto normal (4.5:1), jerarquía por elevación
   (sombra+tono) en vez de por borde donde el borde ensucie.
3. **Referencia explícita**: paleta y sensación de la UI de Claude (fondos
   cálidos muy suaves, bordes casi invisibles, jerarquía por espaciado y
   tipografía) — adaptada a la identidad de Aithera (el acento azul se
   conserva; el AVCS ni se toca, escenario oscuro fijo).
4. Verificación final página a página con capturas antes/después, ambos temas.

**Nota**: si PU6 cambió el layout, esta sesión tematiza también la botonera
nueva — por eso va después.
**Cierre**: recorrido completo de la app en claro sin ningún elemento del
inventario pendiente; capturas archivadas en `test-lab/` como referencia.
**Tamaño**: grande. **Modelo**: Opus o Fable (criterio estético fino +
sistematicidad), esfuerzo alto.

---

## PU8 · Auditoría de prompts internos + mapa de inyección

**Lo que pide el usuario**: que los prompts internos estén MUY bien hechos, y
saber dónde hay inyección de prompts, cuántos puntos y por qué.

**Entrega doble**:
1. **Mapa completo de inyección** (documento nuevo, propuesta:
   `PLAN_MAESTRO_2026/36_MAPA_DE_PROMPTS.md`): inventario exhaustivo de cada
   punto donde Aithera construye/inyecta un prompt, con archivo, propósito,
   qué se inyecta dinámicamente y qué riesgo tiene. El censo conocido de
   partida (a completar con grep sistemático):
   `chat_service.DEFAULT_SYSTEM_PROMPT` + `build_system_prompt()` (memoria MOS
   + preferencias + workspace + idioma + personalidad), `personalities.py`
   (compone, nunca sustituye), `tie/intents.py` (clasificador),
   `tie/planner.py` (regla de oro de fidelidad + catálogo de tools),
   `tie/toolloop.py` (instrucción + transcript con ventana), `tie/responder.py`
   (`_SYSTEM_PROMPT`), `memory/summarizer.py`, `mel/research.py`,
   email (`ai_reply`/triaje/digest), `capabilities_map.py`,
   `core/language.py::language_directive`, las coletillas de grounding
   (deterministas, NO prompts — documentarlas como capa aparte).
2. **Los dos sentidos de "inyección"** — cubrir ambos honestamente:
   (a) inyección NUESTRA (los system prompts): revisar calidad uno a uno
   contra las mejores prácticas (instrucciones positivas, ejemplos donde
   ayuden, sin contradicciones entre capas — p. ej. verificar que la
   personalidad no pueda contradecir el "texto plano" ni la honestidad, regla
   que ya existe y hay que confirmar que se cumple);
   (b) inyección ADVERSARIA (prompt injection desde fuera): el texto externo
   (web/emails/documentos) entra en prompts vía toolloop/enricher — auditar
   qué defensas hay (sanitize de S9c es de caracteres, NO semántica) y
   proponer mitigación proporcionada (mínimo: delimitar el contenido externo
   en el prompt con marcas claras de "esto son DATOS, no instrucciones";
   evaluar si hace falta más antes del instalador — el bloque X del protocolo
   de campañas ya contemplaba tests adversariales que nunca se corrieron).
3. **Mejoras concretas**: los prompts que salgan flojos del inventario se
   reescriben EN LA MISMA SESIÓN si el cambio es quirúrgico (con test si el
   prompt tiene contrato testeable), o quedan listados con prioridad si son
   estructurales.

**Cierre**: doc 36 publicado con el mapa completo; mejoras quirúrgicas
aplicadas con su verificación; lista priorizada de lo estructural (si queda).
**Tamaño**: media-grande. **Modelo**: Fable u Opus (es criterio de diseño de
prompts, el punto fuerte del modelo grande), esfuerzo alto.

---

## PI-A · Investigación Obscura → decisión GO/NO-GO (→ PU9)

**Corrección honesta previa** (investigado 2026-07-30, repo oficial
`h4ckf0r0day/obscura`): **Obscura NO es un buscador web** — es un **navegador
headless** escrito en Rust para agentes IA y scraping: ejecuta JavaScript real
(V8), habla Chrome DevTools Protocol y es reemplazo drop-in de headless Chrome
para Playwright/Puppeteer, con modo *stealth* opcional y distribución Docker
(~57 MB) o build con cargo. No indexa ni busca nada: navega. Por tanto NO
encaja en "Conexiones → Buscador Web" junto a Brave/SerpAPI — encaja como
**motor alternativo del `browser_tool`** (que hoy usa Chrome/Chromium vía
Playwright).

**Por qué aun así es interesante para Aithera**: la limitación documentada
"Google bloquea el tráfico headless" (§8 de CLAUDE.md) es EXACTAMENTE el
problema que el modo stealth de Obscura ataca; y un motor de ~57 MB dedicado a
agentes podría ser más ligero/estable para misiones que el Chrome del usuario.

**La investigación debe responder** (sin tocar código de producción):
1. ¿Hay binario nativo para Windows en las releases, o solo Docker/cargo?
   (Docker en el equipo del usuario final es fricción REAL para un instalador
   1-click — si solo hay Docker, probablemente NO-GO para V1.0.)
2. ¿Playwright de Python se conecta limpio a Obscura vía CDP
   (`connect_over_cdp`)? Prueba de concepto real con 3-4 acciones del
   `browser_tool` (open_url, click, get_text, screenshot).
3. ¿El modo stealth pasa donde Chrome headless es bloqueado? (probar Google.)
4. ¿Qué pierde el usuario respecto al Chrome con perfil persistente actual?
   (cookies aprendidas, sesión de Google, `consent_learned.json` — el trabajo
   del 2026-07-23 NO se regala.)
5. Madurez/licencia/mantenimiento del proyecto (releases, issues, bus factor).

**Propuesta de encaje SI es GO (PU9)**: sección nueva en Conexiones →
**"Navegador para agentes"** (no "Buscador Web"), con la ficha que pide el
usuario (qué es, cómo funciona, tamaño de descarga, requisitos) y botón de
descarga+instalación 1-click con progreso — MISMO patrón ya construido tres
veces (Ollama, Kokoro, Codex: hilo con progreso + estados
idle/installing/done/failed + degradación honesta). `browser_tool` gana
`BROWSER_ENGINE=chrome|obscura` con Chrome como default y degradación
graciosa si Obscura no está.

**Si es NO-GO**: documentar por qué, y como alternativa al DESEO original del
usuario (buscador local descargable) evaluar en la misma nota si SearXNG u
otro metabuscador self-hosted merece una ficha futura (probablemente post-1.0).

**Cierre PI-A**: informe con las 5 respuestas + demo de conexión CDP si
aplica + recomendación GO/NO-GO con coste estimado de PU9.
**Tamaño**: media (investigación). **Modelo**: Sonnet, esfuerzo alto.

---

## PU10 · Configuración → Memoria: UI profesional + chat directo a memoria

**Lo que pide el usuario**: pestaña Memoria limpia y profesional donde (a) se
VEA la memoria, y (b) se pueda AÑADIR hablando con Aithera: "guarda esto en la
memoria: cuando me expliques algo técnico, usa lenguaje coloquial".

**Punto de partida en código**: `memory/profile.py` (hechos estables
destilados cada noche, ya visibles y borrables en Ajustes desde R6.5c),
`GET /api/memory/stats` (colecciones MOS + días cubiertos), `memory_tool`
(save/search/update/delete vía `memory_router`), el detector determinista
`_wants_to_persist` de NEW-7b (verbos de guardar). Los cimientos existen — la
sesión es de UX + un caso de intent nuevo.

**Trabajo**:
1. **UI de la pestaña**: tres zonas — (i) "Lo que Aithera sabe de ti" (hechos
   del perfil, editables/borrables, ya existe: pulir), (ii) "Estado de la
   memoria" (stats por tipo, última ingesta, próximo resumen — datos ya
   disponibles, presentarlos limpio), (iii) **mini-chat de memoria**: un input
   conversacional dentro de la pestaña que enruta DIRECTO a guardar/buscar en
   memoria (sin pasar por el pipeline completo del chat) — "guarda que…",
   "¿qué sabes de…?", "olvida lo de…".
2. **Instrucciones de comportamiento como memoria de primera clase**: los dos
   ejemplos del usuario son PREFERENCIAS DE COMPORTAMIENTO ("explícame en
   coloquial", "dame instrucciones detalladas sin asumir") — deben ir a la
   colección de preferencias que `build_system_prompt()` YA inyecta en cada
   turno (la vía `user_context`/perfil), no a `mem_personal` genérica donde
   solo saldrían por similitud. Verificar el camino completo: guardado por
   chat → visible en la pestaña → APLICADO en la siguiente respuesta.
3. **Desde el chat normal también**: "guarda esto en la memoria: X" en el chat
   principal debe funcionar igual (extender el detector de NEW-7b o
   `action_intent` con el caso "guardar instrucción/preferencia", enrutando a
   la misma función — un solo camino de escritura).

**Cierre**: los DOS ejemplos literales del usuario funcionan end-to-end
(se guardan, se ven en la pestaña, y la respuesta siguiente los respeta);
la pestaña queda visualmente al nivel de PU7.
**Tamaño**: media-grande. **Modelo**: Sonnet, esfuerzo alto.

> ✅ **PU10 EJECUTADA (2026-08-01, Sonnet)** — router determinista compartido
> `app/memory/quick_memory.py` (NUEVO, mismo espíritu que `tie/quick_answers.py`:
> SQL/ChromaDB directo, 0 LLM en el enrutado): `parse()` reconoce
> "guarda que…"/"¿qué sabes de…?"/"olvida lo de…" en DOS modos —
> `require_anchor=False` (mini-chat de Ajustes, el panel entero ya es sobre
> memoria) admite las formas "bare"; `require_anchor=True` (chat principal)
> exige mención EXPLÍCITA a "la memoria" ("guarda esto en la memoria: X"),
> para no confundirse con `action_intent._wants_to_persist` (NEW-7b, que
> guarda un ARCHIVO, no una preferencia — verificado con test dedicado: ni
> "guárdame un resumen de tres líneas" ni "olvida lo que dije antes" a media
> charla disparan esto). **GUARDAR SIEMPRE escribe en `user_context`**
> (`memory_manager.store_user_context`), NUNCA en `mem_personal` genérica —
> la decisión explícita del §2: es la colección que `chat_service.
> build_system_prompt()` YA inyecta en cada turno, así que lo guardado se
> APLICA de verdad en la siguiente respuesta (verificado con un test que
> guarda una preferencia y comprueba que aparece dentro de un
> `build_system_prompt()` real). Buscar combina `user_context` +
> `mem_personal` (`memory_router.search`); olvidar borra por coincidencia de
> substring — único → borra, ninguna → lo dice, varias → lista sin borrar
> (nunca ambigüedad silenciosa). **Un solo camino de escritura** (§3): el
> chat principal engancha `quick_memory.try_answer_async` en los MISMOS dos
> puntos que PU4 usó para el briefing (`tie/pipeline.py::handle_stream` +
> `_run_pipeline`, `orchestrator/__init__.py::handle_stream` — el
> orquestador tiene su propio precheck síncrono antes del TIE), expuesto vía
> `app.tie.quick_memory_answer_async` en el barrel (frontera de módulo:
> `app.orchestrator` nunca importa `app.memory` directo, doc 16). **Backend**:
> `POST /api/memory/quick` (`endpoints/memory.py`) para el mini-chat de
> Ajustes, sin ancla; 14 claves i18n nuevas `quick.memory.*` en
> `core/strings.py` ×4 idiomas. **Frontend**: `MemoryQuickChat.tsx` (NUEVO,
> `components/settings/`) — panel de burbujas simple, sin persistir mensajes
> entre sesiones, con `onChanged` que refresca las listas de arriba
> (perfil/preferencias) tras un guardado/olvido con éxito; montado en
> `Settings.tsx` justo DESPUÉS de las stats y ANTES del formulario manual de
> añadir preferencia — la vía conversacional pasa a ser la principal, el
> formulario sigue disponible como alternativa. `api.quickMemory()` +
> `QuickMemoryResult` en `lib/api.ts`; 5 claves i18n `settings.memoria.
> quickchat.*` ×4 idiomas (`i18n/locales/*.json`, orden alfabético
> respetado). **Tests**: `tests/test_quick_memory.py` (NUEVO, 42 — parseo
> puro con/sin ancla en los 3 tres verbos incl. el no-choque con NEW-7b,
> ejecución real contra ChromaDB con limpieza por test —save/dedup/search/
> forget único/ninguno/ambiguo—, el round-trip completo hasta
> `build_system_prompt()`, y el enganche real en `orchestrator.handle_stream`/
> `tie.handle_stream` verificando que NO llaman al clasificador). Suite
> (sandbox, sin chromadb/sentence-transformers instalados): 28 tests puros en
> verde de inmediato + 14 se saltan por diseño (mismo patrón que el resto de
> tests de memoria del proyecto, `pytest.mark.skipif(not memory_router.
> healthy, ...)`); regresión de 155+122 tests de los módulos tocados (tie/
> orchestrator/memory/module_boundaries/automation/grounding/telemetry) en
> verde, 0 rotos. `tsc --noEmit` limpio; `vite build` transformó los 865
> módulos sin error (cortado por el límite del sandbox antes de escribir los
> chunks, mismo patrón ya documentado en PU6a). **Pendiente en Windows**:
> con chromadb/sentence-transformers reales, correr `test_quick_memory.py`
> completo (las 14 clases que aquí se saltan); y en vivo — pedir por el
> mini-chat de Ajustes "guarda que cuando me expliques algo técnico usa
> lenguaje coloquial", confirmar que aparece en la lista de preferencias, y
> que la siguiente pregunta técnica en el chat normal responde en tono
> coloquial; repetir con "olvida lo de..." y confirmar el borrado; y desde el
> chat PRINCIPAL probar "guarda esto en la memoria: dame instrucciones
> detalladas sin asumir" y confirmar que NO pasa por "analizando" (sin
> clasificador) y queda guardado igual.

> ✅ **PU10-visual EJECUTADA (2026-08-02, Sonnet)** — petición directa del
> usuario tras cerrar el PU10 funcional: "es la memoria de Aithera, quiero
> que sea bonito, intuitivo y moderno" (el pulido de las 3 zonas quedó
> pendiente en la primera pasada). `components/settings/MemoriaPanel.tsx`
> (NUEVO): la pestaña Memoria pasa de bloque inline dentro de `Settings.tsx`
> a panel AUTÓNOMO — mismo patrón que `BriefingPanel.tsx` (posee su propio
> estado/carga, `Settings.tsx` solo lo monta con `<MemoriaPanel />`).
> Reorganización 100% VISUAL, cero cambios de endpoint/comportamiento: los
> 4 bloques que antes vivían apilados y separados por una simple línea
> (`border-t`) pasan a tarjetas `glass-surface rounded-2xl p-4` con cabecera
> propia (icono + título + descripción), siguiendo el mismo lenguaje que
> `BriefingPanel`/PU4b. Iconografía nueva propia del panel (núcleo
> concéntrico para la cabecera, burbuja/marcador/documento para las 3
> estadísticas, chispa para "Resumen"/"Perfil", flecha circular para
> refrescar) — mismo vocabulario fino de `DockIcons.tsx` (stroke 1.1-1.4,
> `currentColor`) pero vive aquí porque son iconos INFORMATIVOS, no de
> navegación. Cambios concretos: cabecera con icono+subtítulo (antes solo un
> `<h3>`); el formulario manual de añadir preferencia pasa de SIEMPRE visible
> a PLEGADO por defecto tras un botón "+ Añadir preferencia" (revelación
> progresiva — reduce el ruido visual sin perder la función); las filas de
> preferencias/perfil ganan una insignia de categoría y un botón de borrar
> circular consistente (antes un botón "Eliminar" de texto suelto); estados
> vacíos con caja de borde punteado en vez de una línea de texto perdida;
> "Borrar historial de conversaciones" se separa en su propia franja
> `signal-warn` (zona sensible diferenciada, patrón ya usado en otras partes
> de la app para acciones irreversibles); el mensaje de feedback pasa de
> texto suelto a una franja `signal-ok`/`signal-error` con fondo. El
> mini-chat (`MemoryQuickChat.tsx`, MODIFICADO) gana burbujas con el MISMO
> estilo que `ChatBubble` del chat principal (`bg-accent/20`/`bg-base-700/50`,
> `rounded-xl`), 3 chips de ejemplo clicables cuando la conversación está
> vacía (rellenan el input, nunca envían solos — el usuario conserva el
> control) para que la frase exacta no haya que adivinarla, e indicador de
> "escribiendo" (3 puntos con `animate-bounce`) mientras se resuelve.
> **Estado movido, no duplicado**: `memStats`/`contextItems`/`profileFacts`/
> `newCtx*`/`memMessage` y sus 5 handlers (`loadMemory`/`handleAddContext`/
> `handleDeleteContext`/`handleDeleteProfileFact`/`handleClearConversations`)
> se retiran de `Settings.tsx` (con su `loadMemory()` del `useEffect` de
> montaje) y pasan a vivir DENTRO de `MemoriaPanel.tsx` — el import de los
> tipos `MemoryStats`/`ContextItem`/`ProfileFact` en `Settings.tsx` se limpia
> por quedar sin uso. 8 claves i18n nuevas ×4 idiomas (`settings.memoria.
> panelTitle`, `.panelSubtitle`, `.summary.title`, `.clearHistoryHint`,
> `.quickchat.chip1/2/3`, `.quickchat.tryHint`), insertadas en orden
> alfabético en los 4 `i18n/locales/*.json` — paridad verificada
> programáticamente (1256 claves en los 4 idiomas). Sin cambios de backend,
> sin tests nuevos (es una reorganización visual sobre endpoints ya
> cubiertos por `test_quick_memory.py`). Verificado en el sandbox:
> `tsc --noEmit` limpio (rc=0, 15s) y `vite build` COMPLETO sin errores
> (867 módulos, `Settings-DBbovIwo.js` 108.89 kB — a diferencia de PU6a, esta
> vez el build terminó dentro del límite del sandbox). **Pendiente en
> Windows**: vistazo visual real de la pestaña Memoria (las 3 tarjetas +
> mini-chat + zona sensible), confirmar que los chips de ejemplo rellenan el
> input sin enviarlo, y que expandir/colapsar el formulario manual funciona.

---

## PI-B · Obsidian como frontend de la memoria — investigación + propuesta honesta

**Lo que pide el usuario**: valorar si Obsidian puede ser el "frontend" de la
memoria de Aithera (además de su sistema de notas), con evaluación
beneficio/coste SIN compromiso — "si no nos sirve, no nos sirve".

**Hechos de partida que inclinan la balanza** (del código real): Obsidian es,
en esencia, una carpeta local de Markdown con enlaces `[[wikilink]]` — y
Aithera YA tiene un vault Markdown: `lifecycle.py` archiva al vault
(`vault.append_archive_entries`) antes de podar. La distancia entre "lo que
hay" y "un vault que Obsidian abre bonito" es mucho más corta de lo que
parece.

**La investigación debe responder**:
1. **Como frontend (lectura)** — la opción barata: ¿basta con (a) apuntar el
   vault de Aithera a una carpeta que el usuario abre con Obsidian, y (b)
   enriquecer lo que se escribe (resúmenes diarios, decisiones, hechos del
   perfil, cierres de milestone) con frontmatter YAML + wikilinks entre
   entidades (proyecto ↔ decisión ↔ día) para que el graph view de Obsidian
   sea útil de verdad? Coste estimado a validar: pequeño (formato de
   escritura, cero dependencias nuevas).
2. **Como fuente (lectura inversa)**: ¿ingestar las notas del usuario en
   Obsidian hacia `mem_personal`/documents? Técnicamente trivial (es Markdown
   en disco + el job de ingesta M2 ya existe como patrón), pero abre preguntas
   de volumen/ruido — evaluar con límites (carpetas elegidas, no el vault
   entero).
3. **Como backend de memoria** — casi seguro NO y hay que decirlo claro:
   la memoria de Aithera es semántica (ChromaDB, embeddings, dedup, tipos,
   presupuesto de latencia de 300ms en el camino del chat); Markdown plano no
   puede sustituir eso sin reconstruir el MOS. La propuesta debe descartarlo
   explícitamente salvo hallazgo sorprendente.
4. **Sincronía y conflictos**: si Aithera escribe y el usuario edita en
   Obsidian, ¿qué pasa? (Propuesta conservadora: Aithera escribe en una
   subcarpeta propia append-only; las notas del usuario son de solo-lectura
   para Aithera salvo la ingesta opcional del punto 2.)

**Entrega**: propuesta de 1-2 páginas con recomendación clara para V1.0
(intuición a validar: GO a la opción 1 por coste ínfimo/beneficio visible;
opción 2 como opcional post-1.0; opción 3 descartada) + estimación de la
sesión de implementación si es GO.
**Tamaño**: pequeña-media (investigación). **Modelo**: Sonnet, esfuerzo alto.

---

## Resumen ejecutivo del bloque

| Sesión | Contenido | Tamaño | Modelo sugerido | Bloqueada por |
|---|---|---|---|---|
| **PU1** | Voces mezcladas (bug) ✅ hecha 2026-07-30 | S | Sonnet | — |
| **PU2** | Skills reales + que se usen ✅ hecha 2026-07-30 | M | Sonnet | — |
| **PU3** | Autónomo 100% + sin timeouts en gates ✅ hecha 2026-07-30 | M | Sonnet | — |
| **PU5** | AVCS partículas ✅ Fallo 1 hecho 2026-07-30 (3 intentos; Fallo 2 escala pendiente) | M | Sonnet | — |
| **PU6** | Hub sin UI + botonera inferior | L | Opus | **Diseño del usuario** + PU5 |
| **PU7** | Modo claro profesional | L | Opus/Fable | PU6 |
| **PU4** | Briefing 2.0 + voz ✅ hecha 2026-08-01 | M-L | Sonnet/Opus | mejor tras PU6 |
| **PU10** | Memoria: UI + chat directo | M-L | Sonnet | mejor tras PU7 |
| **PU8** | Auditoría de prompts (→ doc 36) | M-L | Fable/Opus | — |
| **PI-A** | Investigación Obscura (GO/NO-GO) | M | Sonnet | — |
| **PU9** | Obscura 1-click (solo si GO) | M | Sonnet | PI-A = GO |
| **PI-B** | Investigación Obsidian (propuesta) | S-M | Sonnet | — |

**Decisiones que quedan en manos del usuario** (recopiladas):
1. PU6: enviar el diseño de la botonera inferior antes de esa sesión.
2. ✅ PU4 resuelta 2026-08-01: el usuario pidió AMBOS (auto a las 8:15 +
   botón manual junto a Modo Presencia) — hecha así, ver CLAUDE.md §27.
   Selección de noticias sigue deliberadamente fuera de alcance.
3. PU3: ratificar la matriz de timeouts propuesta y el alcance de Autónomo
   sobre `desktop_tool` (la propuesta es "sin excepciones", como pediste,
   con rastro siempre).
4. PI-A / PI-B: GO/NO-GO tras leer las propuestas.

**Después de este bloque**: MVP-beta (instalador NSIS, auto-start del backend,
onboarding final) → bump a `1.0.0`. Ese plan es aparte (doc 03 §5 O5).

**Fix Workspace (fuera de plan) — ✅ HECHO (2026-08-02)**: dos peticiones
directas del usuario sobre la pantalla de Proyectos, no previstas en los 14
puntos de este documento. (1) **Apilado de ventanas**: las tarjetas de agente
quedaban por debajo de las de proyecto y no se podían subir — causa raíz un
`zIndex` NaN persistido en `localStorage` (una entrada sin el campo envenenaba
el contador para siempre) que dejaba la tarjeta en `z-index: auto`; y, por
diseño, un offset fijo de +100.000 hacía imposible lo contrario (mandar el
agente detrás al clicar el proyecto). Ahora hay saneado en la frontera de
lectura y un contador de apilado ÚNICO compartido por proyectos y agentes:
se intercalan por orden de uso, como ventanas de escritorio. (2) **Chat del
orquestador por proyecto**: `Agent.role="orchestrator"` (W2e) y el enrutado
de `submit_mission` (R4) existían desde hacía versiones, pero nada creaba
nunca un agente con ese rol — la ruta estaba escrita y muerta.
`ensure_orchestrator` + `POST /api/projects/{id}/orchestrator` la
materializan, y el chat vive abajo de la `ProjectCard` reusando los endpoints
de agente (de regalo: historial persistido en `agent_executions`). Su alcance
lo impone `Authority` —proyecto + carpeta + tools—, no un prompt. 10 tests
nuevos + 2 mutaciones; regresión 1337 passed. Detalle en CLAUDE.md §27.

---

*Creado: 2026-07-30, a partir de la lista de 14 puntos del usuario tras el
cierre del bloque de auditoría global del runtime (doc 34, S1-S11).*
*Referencias investigadas: OpenJarvis Morning Digest (docs oficiales),
`h4ckf0r0day/obscura` (README + releases).*
