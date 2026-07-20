# PROMPT_08 — COMITÉ INDEPENDIENTE DE AUDITORÍA TÉCNICA
# Aithera v0.9.5 → Pre-lanzamiento 1.0.0
# Para: Claude Fable 5 (máxima capacidad de razonamiento extendido)

---

## 0. INSTRUCCIONES DE USO DE ESTE PROMPT

Este prompt requiere una sesión de Fable 5 con **extended thinking activado al máximo**.
No resumas. No abrevies. No des respuestas parciales.
Lee este prompt completo antes de hacer absolutamente nada.
Cuando hayas terminado de leerlo, empieza por el paso 1 del §4.

---

## 1. TU ROL: COMITÉ INDEPENDIENTE DE AUDITORÍA

A partir de este momento eres un comité independiente formado simultáneamente por:

- **CTO** con 25 años de experiencia en sistemas distribuidos y productos de consumo masivo
- **Principal Software Architect** especializado en diseño de sistemas IA/agénticos
- **Experto en IA y sistemas multiagente** con foco en fiabilidad y comportamiento emergente
- **Staff Engineer especializado en rendimiento** (latencia, throughput, bloqueos)
- **Especialista en UX** con enfoque en confiabilidad del producto percibida por el usuario final
- **Experto en ciberseguridad** con experiencia en productos desktop con acceso al sistema operativo

Vuestro mandato es único: **determinar si Aithera está en condiciones reales de lanzarse como producto 1.0 de consumo**, e identificar todo lo que impide ese estándar.

**Reglas del comité:**
- No propongas mejoras cosméticas
- No valides decisiones simplemente porque "funcionan en tests"
- No seas amable con el código que lo merece
- Si una parte debe rehacerse completamente, dilo explícitamente
- Prioriza solo los problemas que degradan la experiencia de usuario real o que producirán bugs difíciles de depurar en producción
- Trata cada hallazgo como si tuvieras que defenderlo ante un inversor técnico

---

## 2. CONTEXTO DEL PROYECTO

**Aithera** es un asistente IA personal tipo Jarvis, aplicación desktop (Electron + React 18 + FastAPI + PostgreSQL), diseñado para un único usuario pero con aspiración de distribución pública en v1.0.

### Stack
- **Frontend**: React 18 + TypeScript + Vite + Electron 29 + Zustand + Tailwind
- **Backend**: FastAPI + SQLAlchemy 2.0 + Pydantic v2 + PostgreSQL (fallback SQLite)
- **Memoria**: ChromaDB + sentence-transformers (MOS)
- **IA**: 8 proveedores vía httpx (Anthropic, OpenAI, Gemini, MiniMax, DeepSeek, OpenRouter, Grok, Ollama)
- **Herramientas**: 14 tools registradas (91 acciones), incluyendo browser (Playwright), desktop (pyautogui+winocr), filesystem, shell, git, email, calendar, search, etc.

### Sistemas construidos (por orden cronológico, todos sobre `master`):
1. **V0.8**: Gateway multi-canal (OpenClaw pattern) + Telegram + DPAPI + CORS hardening
2. **V0.85 MOS**: Memory Operating System (ChromaDB, 5 MemoryTypes, MemoryRouter, ingesta async, summarizer nocturno, briefing, lifecycle/compactación)
3. **V0.87 WPMS**: Workspace & Project Management (milestones, kanban, drag&drop, agentes por proyecto, lienzo espacial con tarjetas flotantes)
4. **V0.9 AE**: Automation Engine (APScheduler, triggers, conditions, actions, ApprovalGate, permisos & autonomía A3b, trazas en MOS/Decision API)
5. **V1.0 TIE**: Task Intelligence Engine (classify → enrich → plan → TaskGraph DAG → execute → respond, gates HITL, kill-switch, checkpoint en disco, streaming de estado, UI de Misiones, pestañas de sesión, miniMarkdown)
6. **V1.0 MEL**: Model Execution Layer (capacidades, catálogo, políticas Economy/Quality/Custom, auto-catálogo E1b, override por tarea/proyecto, pantalla Inteligencia)
7. **V1.0 Tools**: Auditoría y capacitación de 14 tools, adjuntos email, 8 tools nuevas, lazy imports
8. **V1.0 Orquestador (R1-R7)**: Descomposición multi-objetivo, conductor concurrente, `tie/toolloop.py` (bucle real elegir→ejecutar→observar), `tools/aithera_tool.py` (Aithera se opera a sí misma), `tie/authority.py` (frontera de autoridad), checkpoints verificables, notificaciones, `tie/capabilities_map.py`, continuidad de sesión (`chat_messages.session_id`), perfil de usuario (`memory/profile.py`)

**Versión actual**: `0.9.5`. El siguiente y último milestone es **MVP-beta → 1.0.0** (instalador NSIS, auto-start, onboarding).

### Documentos de referencia disponibles en el repo:
- `CLAUDE.md` — fuente de verdad del proyecto (lee esto primero)
- `PLAN_MAESTRO_2026/` — documentos de diseño de cada sistema (docs 06-23)
- `backend/tests/` — suite pytest (~750+ tests)
- `backend/app/` — código del backend
- `frontend/src/` — código del frontend

---

## 3. EVIDENCIAS DE FALLOS YA CONOCIDOS (punto de partida, no límite)

Estos tres casos reales han sido reportados por el usuario. Son síntomas — vuestra tarea es encontrar las causas raíz y todos los fallos relacionados:

### FALLO A — Misión browser: YouTube + popup de cookies
**Escenario**: Usuario pide "abre YouTube y pon la canción de Melendi 'Caminando por la vida'".
**Síntomas observados**:
1. La misión aparece como "completada" pero no lo está
2. El sistema hace múltiples intentos de abrir YouTube aunque ya lo reportó como completado
3. Sospecha de bloqueo por timeout si el usuario tarda en conceder el permiso HITL
4. El popup de cookies/consentimiento de Google bloquea la interacción con la página real; la tool browser no lo detecta ni gestiona
5. No hay evidencia de que el TIE o el toolloop sepa recuperarse de un DOM inesperado (popup por encima del contenido objetivo)

**Preguntas del comité para investigar**:
- ¿`browser_tool.py` tiene gestión de overlays/popups? ¿Espera a que el DOM sea interactuable?
- ¿Qué ocurre en `tie/toolloop.py` cuando una tool devuelve `success=True` pero el resultado semántico es un fallo (p.ej. "no encontré la canción")?
- ¿El gate HITL tiene timeout? ¿Qué pasa con el estado del grafo si el usuario no responde en 5 minutos?
- ¿Cómo reporta el `responder.py` el estado cuando una misión queda en bucle?
- ¿El executor detecta que está re-ejecutando el mismo nodo sin progreso?

### FALLO B — Misión filesystem: no puede crear carpetas en el Escritorio
**Escenario**: Usuario pide "crea una carpeta en mi escritorio llamada AITHERA GAME".
**Síntomas observados**:
1. La tool filesystem no consiguió crear la carpeta ni ningún archivo en el Escritorio del usuario
2. El Orquestador abrió una web de Godot para informarse pero no ejecutó ninguna acción de escritura
3. No se creó la carpeta, no se creó documentación, no se creó el juego

**Preguntas del comité**:
- ¿`filesystem_tool.py` tiene whitelist que excluye el Escritorio? ¿Cuál es el `HOME` resuelto en el contexto real de Electron/Windows?
- ¿El path `~/Desktop` o `C:\Users\...\Desktop` está dentro de la whitelist permitida?
- ¿El toolloop intenta la acción y captura el error, o simplifica silenciosamente?
- ¿El planner genera correctamente `tool_call: filesystem.create_dir` o delega en shell y entonces la whitelist de shell tampoco lo permite?
- ¿Existe algún path de ejecución donde la tool dice `success=True` pero no ha hecho nada?

### FALLO C — TIE reinterpreta la misión completamente (alucinación de objetivo)
**Escenario**: Usuario pide exactamente crear un videojuego tipo Rey León en Godot.
**Síntomas observados**:
1. El TIE reinterpretó la misión como "diseñar estrategia de lanzamiento de un MMORPG indie con Open Tibia basado en las novelas de fantasía del usuario"
2. La información sobre "novelas de fantasía" parece venir del MOS (memoria personal del usuario), mezclada inadecuadamente con el objetivo real
3. La misión ejecutada fue completamente distinta a la solicitada

**Preguntas del comité**:
- ¿El `enricher.py` está inyectando contexto del MOS que contamina el objetivo en lugar de complementarlo?
- ¿El `planner.py` usa el contexto de memoria en el prompt de planificación de una forma que permite al LLM sustituir el objetivo original?
- ¿Existe alguna salvaguarda en `intents.py` o `pipeline.py` que compruebe que el plan generado es coherente con el `goal` original del Intent?
- ¿El `classify()` podría estar alterando el `goal` con información de contexto antes de pasarlo al planner?
- ¿Hay algún test que verifique que `planner.plan(goal=X)` produce un plan sobre X y no sobre algo relacionado con X?

### FALLO D — Sistema de permisos ignorado en modo autónomo
**Escenario**: El usuario tiene activado el perfil de autonomía "full" en Ajustes → Permisos.
**Síntomas observados**:
1. El TIE siguió pidiendo 5-6 confirmaciones al usuario durante una misión larga
2. El modo "full" debería auto-resolver todos los gates con rastro de auditoría, sin interacción humana

**Preguntas del comité**:
- ¿`permissions.py` está siendo consultado correctamente antes de `approval_gate.request_approval()`?
- ¿El gate de PLAN (`action_type="tie_plan"`) pasa por el mismo check de pre-autorización que los gates de nodo?
- ¿El gate de nodo del TIE (`action_type="tie.node"`) pasa por `is_pre_authorized()`?
- ¿La configuración de perfil "full" activa todos los permisos disponibles incluyendo `browser.use`, `computer.use` y `workspace.write`?
- ¿Hay algún lugar donde se crea un gate con un `kind` que NO está en el catálogo de permisos (y por tanto siempre falla-closed)?

---

## 4. METODOLOGÍA DE AUDITORÍA (ejecuta en este orden)

### PASO 1 — Lectura de fuente de verdad
Lee `CLAUDE.md` completo. Es el documento más actualizado del estado real del proyecto. Presta especial atención a:
- §1 (estado de cada sprint: lo que se dice que está hecho vs lo que ves en el código)
- §8 (las 14 tools y sus limitaciones conocidas)
- §16 (deuda técnica documentada — verifica si está realmente saldada o solo declarada)
- §21 (bloque Orquestador R1-R7 — los números de rendimiento prometidos)

### PASO 2 — Lectura de código crítico
Lee en profundidad (no superficialmente) estos módulos, en este orden:
1. `backend/app/tie/pipeline.py` — el flujo de entrada principal
2. `backend/app/tie/toolloop.py` — el bucle real de ejecución de tools (R1)
3. `backend/app/tie/executor.py` — el graph execution engine
4. `backend/app/tie/intents.py` + `enricher.py` + `planner.py` — la cadena de razonamiento
5. `backend/app/orchestrator/` — decomposer, conductor, consolidator
6. `backend/app/automation/approval.py` + `permissions.py` — el gate y los permisos
7. `backend/app/tools/browser_tool.py` + `desktop_tool.py` + `filesystem_tool.py` — las tools de mayor riesgo
8. `backend/app/mel/executor.py` + `decision.py` — el MEL
9. `backend/app/memory/ingestion.py` + `summarizer.py` + `lifecycle.py` + `profile.py` — el MOS
10. `backend/app/core/events.py` — el bus de eventos in-process
11. `frontend/src/store/useChatStore.ts` + `frontend/src/pages/Missions.tsx` — la UI de misiones

### PASO 3 — Ejecución de la suite de tests
```bash
cd backend
python -m pytest tests/ -v --tb=short 2>&1 | head -200
python -m pytest tests/ -v --tb=short 2>&1 | tail -50
```
Documenta: número de passed/failed/skipped, cualquier warning recurrente, tests que tardan más de 2s.

### PASO 4 — Auditoría de tests existentes
Para cada área crítica, verifica si los tests cubren los casos que importan:
- ¿Hay tests del toolloop que simulen una tool que devuelve `success=True` con un resultado semánticamente incorrecto?
- ¿Hay tests del planner que verifiquen que el plan generado es sobre el objetivo solicitado (no solo que es un DAG válido)?
- ¿Hay tests del enricher que verifiquen que no contamina el objetivo?
- ¿Hay tests de permisos que cubran el gate de PLAN + gate de nodo + perfil full?
- ¿Hay tests de browser_tool con páginas que tienen overlays/popups?
- ¿Hay tests de filesystem que intenten escribir en el Escritorio del usuario?
- ¿Hay tests e2e que verifiquen una misión completa de punta a punta con una tool real?

### PASO 5 — Búsqueda activa de patrones de riesgo
Ejecuta estos greps y analiza cada resultado:

```bash
# Patrones de silencio peligroso
grep -rn "except.*pass" backend/app/
grep -rn "except Exception" backend/app/ | grep -v "log\|logger\|raise\|print"

# Tools que podrían mentir sobre el éxito
grep -rn "success=True" backend/app/tools/
grep -rn "success.*True" backend/app/tools/ | grep -v "return\|assert"

# Estado compartido mutable entre misiones
grep -rn "global " backend/app/tie/ backend/app/orchestrator/
grep -rn "asyncio.create_task" backend/app/ | grep -v "test\|#"

# Gates sin kind registrado en el catálogo
grep -rn "request_approval" backend/app/ | grep -v "test\|#"
grep -rn "kind=" backend/app/automation/approval.py backend/app/tie/

# El enricher contaminando el goal
grep -rn "goal" backend/app/tie/planner.py backend/app/tie/enricher.py

# Imports que rompen la disciplina modular
grep -rn "from app.tie" backend/app/ | grep -v "tie/\|test\|__init__\|endpoints"
grep -rn "from app.mel" backend/app/ | grep -v "mel/\|test\|__init__\|endpoints\|registry"

# Timeouts hardcoded o ausentes en las tools
grep -rn "timeout" backend/app/tools/browser_tool.py backend/app/tools/desktop_tool.py

# Memory budget y lifecycle
grep -rn "MEMORY_BUDGET\|lifecycle\|purge\|prune" backend/app/memory/

# Condiciones de carrera en el conductor del Orquestador
grep -rn "asyncio.gather\|asyncio.wait\|asyncio.shield" backend/app/orchestrator/
```

### PASO 6 — Auditoría de arquitectura de alto nivel
Sin leer código nuevo, razona sobre estos riesgos sistémicos basándote en lo que has leído:

1. **Acoplamiento MOS ↔ TIE ↔ Orquestador**: ¿Hay ciclos de dependencia? ¿El enricher puede bloquear al planner? ¿El conductor puede bloquear al gateway?
2. **El bus de eventos in-process (`events.py`)**: ¿Qué ocurre si un handler lanza una excepción dentro de un `create_task`? ¿Los eventos se pierden entre reinicios? ¿Hay riesgo de memory leak con handlers que nunca se desuscriben?
3. **Estado del grafo en disco vs estado en memoria**: ¿Pueden divergir? ¿El `resume_pending()` puede corromper una misión en vuelo?
4. **El MEL como punto único de fallo**: Si el MEL decision engine falla, ¿el sistema degrada o colapsa? ¿Los 8 proveedores tienen todos el mismo path de fallback?
5. **La whitelist de filesystem en Windows**: ¿El `HOME` resuelto en Electron es el mismo que en el proceso FastAPI? ¿Son coherentes?
6. **Playwright en producción**: ¿El instalador NSIS incluye Chromium? ¿El usuario final tendrá que hacer `playwright install chromium` manualmente?
7. **Permisos del sistema operativo para `desktop_tool`**: ¿Pyautogui necesita permisos especiales en Windows 11? ¿Falla silenciosamente o con error claro?
8. **El perfil de usuario (`memory/profile.py`)**: ¿El destilado nocturno puede crear "hechos" erróneos que contaminen misiones futuras? ¿Hay mecanismo de corrección?
9. **Sessión de chat con `localStorage`**: ¿Qué ocurre cuando el store de Zustand crece indefinidamente con pestañas? ¿Hay límite?
10. **La tabla `orchestration_runs`**: ¿Tiene política de limpieza? ¿Puede crecer sin límite?

### PASO 7 — Revisión de la UX de misiones bajo estrés
Analiza los ficheros de frontend relacionados con misiones y evalúa:
- ¿Qué ve el usuario cuando una misión lleva 10 minutos sin progreso visible?
- ¿Qué ve cuando el gate HITL caduca (si caduca)?
- ¿Qué ve cuando el Orquestador descompone en 5 sub-objetivos y 3 fallan?
- ¿La UI de Misiones diferencia claramente entre "esperando permiso", "ejecutando", "completada parcialmente" y "fallida"?
- ¿Hay algún estado de misión que sea terminal pero la UI no lo muestre como tal?

---

## 5. CRITERIOS DE EVALUACIÓN

Para cada hallazgo, el comité evalúa:

### Arquitectura
- Decisiones de diseño equivocadas
- Módulos demasiado acoplados
- Responsabilidades mezcladas
- Complejidad innecesaria
- Flujos de ejecución confusos
- Violaciones de principios SOLID
- Posibles problemas de escalabilidad

### Fiabilidad
- Comportamientos impredecibles
- Condiciones de carrera
- Posibles bloqueos (deadlocks)
- Problemas de sincronización
- Errores de estado
- Recuperación ante fallos incompleta o ausente

### Calidad de código
- Código difícil de mantener
- Duplicación de lógica
- Inconsistencias entre módulos
- Deuda técnica no documentada
- Tests que no cubren los casos que importan en producción

### Seguridad y límites
- Whitelists que no cubren casos reales del usuario
- Permisos que se saltean o ignoran
- Tools que reportan éxito falsamente
- Datos del usuario expuestos a lógica que no debería verlos

### Experiencia de usuario
- Misiones que "completan" sin haber completado nada
- Feedback opaco o ausente durante ejecución larga
- Recuperación visible desde estados de error
- Gates HITL sin timeout definido

---

## 6. FORMATO DE ENTREGA

### Entrega 1 — INFORME EJECUTIVO (máx. 1 página)
Un párrafo por cada miembro del comité: su veredicto personal sobre si Aithera está listo para 1.0 y el problema más grave que ha encontrado.

### Entrega 2 — HALLAZGOS CRÍTICOS (severidad CRÍTICA y ALTA únicamente)
Para cada hallazgo:

```
## [CRÍTICO|ALTO] Título del problema

**Módulo(s)**: ruta/al/archivo.py
**Tipo**: [Arquitectura|Fiabilidad|Seguridad|UX|Tests]

**Descripción**:
Qué está mal, con referencias de código específicas (línea o función).

**Evidencia**:
Resultado de grep, test fallido, o razonamiento sobre por qué esto produce el fallo reportado.

**Impacto en producción**:
Qué experimenta el usuario. En qué condiciones falla. Con qué frecuencia.

**Veredicto**:
[Reparar | Refactorizar | Rediseñar completamente]

**Acción concreta**:
Qué hay que cambiar exactamente. Sin ambigüedades.
```

### Entrega 3 — PLAN DE ACCIÓN PRIORIZADO
Una tabla con todos los hallazgos ordenados por:
1. Severidad (CRÍTICO > ALTO > MEDIO)
2. Impacto en 1.0 (¿bloquea el lanzamiento?)
3. Esfuerzo estimado (horas de un senior developer)
4. Dependencias entre fixes

```
| # | Severidad | Módulo | Problema | Bloquea 1.0 | Esfuerzo | Depende de |
|---|-----------|--------|----------|-------------|----------|------------|
```

### Entrega 4 — DEUDA TÉCNICA HEREDADA
Lista de problemas de severidad MEDIA que no bloquean 1.0 pero que deben corregirse en 1.1. Formato libre pero estructurado por módulo.

### Entrega 5 — VEREDICTO FINAL
Una sección de no más de 500 palabras respondiendo a: **¿Está Aithera listo para ser lanzado como producto 1.0 de pago a usuarios reales?** Con condiciones específicas y no negociables para que la respuesta sea "sí".

---

## 7. RESTRICCIONES ABSOLUTAS

- **No repitas lo que ya está en CLAUDE.md** como si fuera un hallazgo. CLAUDE.md documenta el estado del proyecto, no es la auditoría.
- **No valides código que funciona en tests unitarios con mocks** como si funcionara en producción. Los tres fallos reportados en §3 pasaron todos los tests y fallaron en producción.
- **No propongas refactors si el problema es un bug concreto**. Un bug se arregla. Un diseño roto se rediseña.
- **No uses lenguaje diplomático** para describir problemas graves. "Podría mejorarse" no es útil. "Esto producirá fallos en producción bajo estas condiciones específicas" sí lo es.
- **No inventes código**. Todo hallazgo debe estar referenciado en código real del repositorio.
- **Si no encuentras evidencia de un problema**, dilo explícitamente. "No se ha encontrado evidencia de X" es un hallazgo válido.

---

## 8. CONTEXTO ADICIONAL PARA EL COMITÉ

Los tres fallos del §3 no son casos edge. Son las primeras cosas que un usuario nuevo intentará con Aithera:
- "Pon música en YouTube" → caso de uso básico de browser
- "Crea una carpeta y un proyecto en mi escritorio" → caso de uso básico de filesystem
- "Haz X" → el sistema hace Y → pérdida total de confianza del usuario

Un producto 1.0 de pago que falla en estos tres escenarios en su primera semana de uso no tendrá una segunda semana.

El comité tiene autoridad total para declarar que cualquier subsistema necesita ser rediseñado antes del lanzamiento. No hay decisiones sagradas. No hay trabajo previo que deba respetarse si está mal hecho.

**El objetivo no es proteger el trabajo ya realizado. El objetivo es que Aithera funcione.**

---

*Documento preparado para Claude Fable 5. Versión del proyecto en auditoría: 0.9.5 (tag v0.9.5).*
*Fallos reportados en producción: 4 (§3 A-D). Tests pasando en CI: ~750+.*
*La discrepancia entre los tests y los fallos en producción es en sí misma un hallazgo.*
