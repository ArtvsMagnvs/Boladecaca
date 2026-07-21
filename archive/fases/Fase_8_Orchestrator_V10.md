# FASE 7 — V1.0: Orchestrator + Claude Code como Agente Externo
## Documento de implementación para Claude Code
**Versión objetivo**: Aithera V1.0.0
**Prerrequisito**: Aithera V0.9.0 completada (Automation Engine funcionando)
**Sesiones**: 3

---

## CONCEPTO

El Orchestrator es la capa de inteligencia central de Aithera. Recibe mensajes en lenguaje natural, decide si responder directamente o usar herramientas/agentes, construye un plan, lo ejecuta paso a paso, y sintetiza la respuesta final.

Este módulo transforma Aithera de "un chat con acceso a herramientas" en "un sistema operativo de IA que razona antes de actuar".

---

## SESIÓN 1: Orchestrator core

**Tiempo estimado**: 3-4 horas
**Empieza con**: Aithera V0.9.0 funcionando

### Paso 1 — Migración Alembic: tabla de planes

```python
class OrchestrationPlan(Base):
    __tablename__ = 'orchestration_plans'
    id = Column(Integer, primary_key=True)
    user_message = Column(Text)
    intent = Column(String(100))       # 'chat'|'execute'|'query'|'compose'
    plan = Column(Text)                # JSON: lista de pasos
    status = Column(String(20), default='pending')
    # 'pending'|'awaiting_approval'|'approved'|'rejected'|'executing'|'completed'|'failed'
    result = Column(Text)
    requires_approval = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
```

Generar y aplicar:
```bash
alembic revision --autogenerate -m "add_orchestration_plans"
alembic upgrade head
```

### Paso 2 — Crear `backend/app/orchestrator/orchestrator.py`

```python
"""
Orchestrator — Motor de razonamiento central de Aithera.

Flujo:
  user_message → analyze_intent() → create_plan() → [approval si riesgo alto]
  → execute_plan() → synthesize_response() → string de respuesta

El Orchestrator NO es un agente en sí mismo. Es la lógica que decide qué agentes
y herramientas usar, en qué orden, con qué parámetros.
"""
import json
from typing import Dict, List, Optional

class Orchestrator:

    # Intenciones de bajo riesgo: responder directamente
    DIRECT_INTENTS = {'chat', 'query', 'explain', 'summarize'}

    # Intenciones de alto riesgo: requieren aprobación
    HIGH_RISK_INTENTS = {'execute', 'send_email', 'create_event', 'run_code'}

    async def process(self, user_message: str, conversation_id: Optional[int] = None) -> Dict:
        """
        Punto de entrada principal. Devuelve:
        {
            "plan_id": int,
            "status": "completed"|"awaiting_approval",
            "response": str | None,
        }
        """
        # 1. Construir contexto desde MemoryManager
        # 2. analyze_intent()
        # 3. Si intent en DIRECT_INTENTS: create_plan() + execute_plan() + synthesize()
        # 4. Si intent en HIGH_RISK_INTENTS: create_plan() + guardar + devolver awaiting_approval
        # 5. Guardar el intercambio en MemoryManager

    async def analyze_intent(self, message: str, context: str) -> Dict:
        """
        Usa AIManager para clasificar la intención.
        Devuelve: { "intent": str, "confidence": float, "entities": {} }
        """
        prompt = f"""Analiza este mensaje y clasifica la intención.
Responde SOLO con JSON válido:
{{
  "intent": "chat|query|execute|summarize|send_email|create_event|run_code",
  "confidence": 0.0-1.0,
  "entities": {{...datos relevantes extraídos...}}
}}

Contexto del usuario:
{context}

Mensaje:
{message}"""
        response = await ai_manager.chat(prompt)
        try:
            return json.loads(response)
        except Exception:
            return {"intent": "chat", "confidence": 0.5, "entities": {}}

    async def create_plan(self, intent: str, message: str, entities: Dict) -> List[Dict]:
        """
        Crea un plan de pasos para ejecutar la intención.
        Devuelve: [{ "step": int, "type": "tool"|"agent"|"llm", "tool_id": str, "action": str, "params": {} }]

        Ejemplo para intent='execute':
        [
          {"step": 1, "type": "tool", "tool_id": "filesystem", "action": "read_file", "params": {"path": "..."}},
          {"step": 2, "type": "llm", "action": "analyze", "params": {"prompt": "Analiza el contenido..."}},
          {"step": 3, "type": "tool", "tool_id": "shell", "action": "run", "params": {"command": "python", "args": [...]}}
        ]
        """

    async def execute_plan(self, plan: List[Dict], plan_id: int) -> List[Dict]:
        """
        Ejecuta los pasos del plan en orden.
        Cada paso: llama a ExecutionEngine / AIManager / AgentManager según step.type.
        Devuelve: lista de resultados por paso.
        """

    async def synthesize_response(self, original_message: str, plan_results: List[Dict]) -> str:
        """
        Genera la respuesta final en lenguaje natural combinando todos los resultados del plan.
        """

    async def approve_plan(self, plan_id: int) -> Dict:
        """Aprueba un plan pendiente y lo ejecuta."""

    async def reject_plan(self, plan_id: int, reason: str = "") -> Dict:
        """Rechaza un plan. Devuelve confirmación."""


orchestrator = Orchestrator()  # Singleton
```

### Paso 3 — Integrar en el lifespan de FastAPI

```python
# En backend/app/main.py, dentro del lifespan:
from app.orchestrator.orchestrator import orchestrator
log_info("startup", "Orchestrator listo")
```

El Orchestrator no necesita `start()`/`stop()` — es stateless entre requests. Solo el singleton se inicializa al importar.

### ✅ Checkpoint Sesión 1 — verificar antes de parar

- [ ] `alembic upgrade head` aplicó la tabla `orchestration_plans` sin errores
- [ ] El backend arranca sin errores con el import del Orchestrator
- [ ] `orchestrator.analyze_intent("envía un email a jefe@empresa.com", "")` devuelve `{"intent": "send_email", ...}`
- [ ] `orchestrator.analyze_intent("¿cuántos proyectos tengo activos?", "")` devuelve `{"intent": "query", ...}`
- [ ] `orchestrator.create_plan("query", "proyectos activos", {})` devuelve una lista de pasos válida

### 🛑 Para aquí

Commit: `feat: Orchestrator core — analyze_intent + create_plan + execute_plan`. La Sesión 2 añade ClaudeCodeAgent y endpoints.

---

## SESIÓN 2: ClaudeCodeAgent + endpoints

**Tiempo estimado**: 2-3 horas
**Empieza con**: Orchestrator core funcionando

### Paso 1 — Crear `backend/app/agents/claude_code_agent.py`

```python
"""
ClaudeCodeAgent — Agente especializado en programación.
Llama a Claude Code CLI como proceso externo.
Requiere que 'claude' esté instalado y en PATH.

Uso: tareas que requieren leer/editar código, crear archivos, ejecutar tests.
NO usar para tareas que ExecutionEngine puede resolver directamente.
"""
import asyncio
import subprocess
from typing import Optional

class ClaudeCodeAgent:

    async def is_available(self) -> bool:
        """Comprueba si 'claude' está disponible en el PATH."""
        try:
            result = await asyncio.create_subprocess_exec(
                'claude', '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            return result.returncode == 0
        except FileNotFoundError:
            return False

    async def execute_task(self, task: str, working_dir: Optional[str] = None,
                           max_turns: int = 5) -> Dict:
        """
        Ejecuta una tarea de programación con Claude Code CLI.
        Llama: claude -p "{task}" --output-format json --max-turns {max_turns}

        Devuelve:
        {
            "success": bool,
            "result": str,      # output de Claude Code
            "exit_code": int
        }
        """
        cmd = ['claude', '-p', task, '--output-format', 'json', '--max-turns', str(max_turns)]
        cwd = working_dir or os.environ.get('USERPROFILE', '.')

        try:
            result = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd
                ),
                timeout=300  # 5 minutos máximo
            )
            stdout, stderr = await result.communicate()
            return {
                "success": result.returncode == 0,
                "result": stdout.decode('utf-8', errors='replace'),
                "exit_code": result.returncode
            }
        except asyncio.TimeoutError:
            return {"success": False, "result": "Timeout (5 minutos)", "exit_code": -1}
        except FileNotFoundError:
            return {"success": False, "result": "Claude Code CLI no encontrado en PATH", "exit_code": -2}


claude_code_agent = ClaudeCodeAgent()  # Singleton
```

Registrar en `backend/app/main.py`:
```python
from app.agents.claude_code_agent import claude_code_agent
log_info("startup", f"ClaudeCodeAgent disponible: {await claude_code_agent.is_available()}")
```

### Paso 2 — Crear `backend/app/api/endpoints/orchestrator.py`

```
POST /api/orchestrator/process
    Body: { "message": "...", "conversation_id": int | null }
    Response: {
        "plan_id": int,
        "status": "completed"|"awaiting_approval",
        "response": str | null,
        "plan": [{ "step": int, "type": str, "action": str }] | null
    }

GET /api/orchestrator/plans
    Query: ?limit=20
    Response: lista de planes recientes

GET /api/orchestrator/plans/{plan_id}
    Response: plan completo con resultados de cada paso

POST /api/orchestrator/plans/{plan_id}/approve
    Response: { "executing": true, "plan_id": int }

POST /api/orchestrator/plans/{plan_id}/reject
    Body: { "reason": "..." }
    Response: { "rejected": true }

GET /api/orchestrator/claude-code/status
    Response: { "available": bool, "version": str | null }

POST /api/orchestrator/claude-code/execute
    Body: { "task": "...", "working_dir": "..." }
    Response: { "success": bool, "result": str }
    ⚠️ Este endpoint requiere autenticación web (X-Aithera-Token) o acceso local
```

Registrar en `backend/app/main.py`:
```python
from app.api.endpoints import orchestrator as orchestrator_router
app.include_router(orchestrator_router.router, prefix="/api")
```

### ✅ Checkpoint Sesión 2 — verificar antes de parar

- [ ] `GET /api/orchestrator/claude-code/status` responde `{ "available": true/false }`
- [ ] `POST /api/orchestrator/process` con mensaje simple devuelve respuesta directa (intent=chat)
- [ ] `POST /api/orchestrator/process` con "lista mis proyectos" devuelve datos de la BD
- [ ] `POST /api/orchestrator/process` con "envía un email a X" devuelve `status: "awaiting_approval"`
- [ ] `POST /api/orchestrator/plans/{id}/approve` ejecuta el plan aprobado
- [ ] El plan y sus resultados quedan guardados en `orchestration_plans`

### 🛑 Para aquí

Commit: `feat: ClaudeCodeAgent + endpoints del Orchestrator`. La Sesión 3 conecta el Orchestrator al Chat y crea la UI de aprobación.

---

## SESIÓN 3: Integración en Chat + UI de aprobación + Settings

**Tiempo estimado**: 2-3 horas
**Empieza con**: Orchestrator + endpoints funcionando

### Paso 1 — Integrar Orchestrator en el Chat

Modificar `backend/app/api/endpoints/chat.py`:

El endpoint `/api/chat/stream` ahora tiene dos modos controlados por un config flag `orchestrator_enabled` en la BD:

```python
from app.orchestrator.orchestrator import orchestrator

@router.post("/stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    config_row = db.query(Config).filter(Config.key == 'orchestrator_enabled').first()
    use_orchestrator = config_row and config_row.value == 'true'

    if use_orchestrator:
        # Modo Orchestrator: razona antes de responder
        result = await orchestrator.process(request.message)

        async def orchestrated_stream():
            if result['status'] == 'awaiting_approval':
                # Enviar al cliente el plan que espera aprobación
                payload = json.dumps({
                    "type": "plan_approval",
                    "plan_id": result['plan_id'],
                    "plan": result.get('plan', [])
                })
                yield f"data: {payload}\n\n"
            else:
                # Enviar la respuesta como stream simulado (chunks de ~50 chars)
                response = result.get('response', '')
                for i in range(0, len(response), 50):
                    yield f"data: {response[i:i+50]}\n\n"
                    await asyncio.sleep(0.02)
            yield "data: [DONE]\n\n"

        return StreamingResponse(orchestrated_stream(), media_type="text/event-stream")
    else:
        # Modo directo: comportamiento existente (con MemoryManager)
        # ... código existente sin cambios ...
```

### Paso 2 — UI de aprobación de plan en Chat.tsx

`frontend/src/pages/Chat.tsx` — detectar el evento SSE de tipo `plan_approval`:

```typescript
// Dentro del handler de chunks SSE:
if (chunk.startsWith('{') && chunk.includes('"type":"plan_approval"')) {
    const planData = JSON.parse(chunk);
    setPendingPlan(planData);  // useState
    return;
}
```

Cuando `pendingPlan !== null`, mostrar en el chat (justo debajo del último mensaje del usuario) un componente `PlanApprovalCard`:

```
┌─────────────────────────────────────────────────────┐
│ 🔍 Plan propuesto                                   │
│                                                     │
│  Paso 1: Leer email con ID abc123                  │
│  Paso 2: Generar respuesta con IA                  │
│  Paso 3: Enviar email → usuario@gmail.com          │
│                                                     │
│   [✓ Aprobar]    [✗ Rechazar]                      │
└─────────────────────────────────────────────────────┘
```

Al aprobar: `POST /api/orchestrator/plans/{plan_id}/approve` → la respuesta llega como nuevo mensaje del asistente.
Al rechazar: `POST /api/orchestrator/plans/{plan_id}/reject` → mensaje "Entendido, acción cancelada."

### Paso 3 — Sección Orchestrator en Settings

`frontend/src/pages/Settings.tsx` — añadir sección "Orchestrator":

- Toggle: "Activar Orchestrator" (llama `POST /api/config/` con `{ key: 'orchestrator_enabled', value: 'true'/'false' }`)
- Descripción: "Cuando está activo, Aithera razona antes de responder. Las acciones de alto riesgo (emails, código, archivos) requieren tu aprobación."
- Estado Claude Code: "✓ Claude Code disponible (v...)" o "✗ Claude Code no encontrado en PATH. Instala con: npm install -g @anthropic-ai/claude-code"
- Estadísticas: últimos 7 días — N planes ejecutados, N aprobados, N rechazados

### Bump de versión

- `backend/app/main.py`: `version="1.0.0"`
- `backend/app/core/config.py`: `VERSION = "1.0.0"`
- `frontend/package.json`: `"version": "1.0.0"`

### ✅ Checkpoint Sesión 3 — verificar antes de parar

- [ ] El toggle de Orchestrator en Settings activa/desactiva el modo
- [ ] Con Orchestrator OFF: el chat funciona exactamente igual que antes
- [ ] Con Orchestrator ON: un mensaje simple ("hola") responde directamente sin plan
- [ ] Con Orchestrator ON: "envía un email a X" muestra el PlanApprovalCard en el chat
- [ ] Aprobar el plan lo ejecuta y muestra la respuesta
- [ ] Rechazar el plan muestra "Entendido, acción cancelada."
- [ ] El historial de planes en `/api/orchestrator/plans` refleja las decisiones
- [ ] `GET /api/orchestrator/claude-code/status` aparece en Settings
- [ ] `GET /` devuelve `"version": "1.0.0"`

### 🛑 Para aquí

Aithera V1.0.0 completada. Commit: `feat: V1.0.0 — Orchestrator integrado en Chat + UI de aprobación`.

**Aithera AOS v1.0 está lista.**

---

## ARCHIVOS CREADOS/MODIFICADOS EN ESTA FASE

**Sesión 1**: `backend/app/db/database.py` (OrchestrationPlan), `backend/app/orchestrator/__init__.py`, `backend/app/orchestrator/orchestrator.py`, `backend/app/main.py` (import orchestrator), nueva migración Alembic

**Sesión 2**: `backend/app/agents/claude_code_agent.py`, `backend/app/api/endpoints/orchestrator.py`, `backend/app/main.py` (registrar router + log ClaudeCodeAgent)

**Sesión 3**: `backend/app/api/endpoints/chat.py` (modo Orchestrator), `frontend/src/pages/Chat.tsx` (PlanApprovalCard), `frontend/src/pages/Settings.tsx` (sección Orchestrator), versiones en main.py, config.py, package.json
