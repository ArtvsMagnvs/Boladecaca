# FASE 2 — V0.5: AgentManager + Execution Engine + ToolManager
## Documento de implementación para Claude Code
**Versión objetivo**: Aithera V0.5.0
**Prerrequisito**: Aithera V0.4.0 completada (PostgreSQL activo, Alembic inicializado)
**Sesiones**: 3

---

## PRINCIPIO FUNDAMENTAL DE SEGURIDAD

La IA sugiere. El Execution Engine valida. Aithera ejecuta.

La IA nunca genera un comando que se ejecute directamente. Siempre pasa por una herramienta registrada con whitelist y validación de parámetros.

---

## SESIÓN 1: Execution Engine + Herramientas

**Tiempo estimado**: 3-4 horas
**Empieza con**: Aithera V0.4.0 funcionando sobre PostgreSQL

### Paso 1 — Migración Alembic para el modelo Agent actualizado

El modelo `Agent` en `backend/app/db/database.py` necesita dos campos nuevos:

```python
class Agent(Base):
    __tablename__ = 'agents'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    agent_type = Column(String(50), default='generic')
    description = Column(Text)
    system_prompt = Column(Text)
    allowed_tools = Column(Text, default='[]')      # NUEVO: JSON list
    max_execution_time = Column(Integer, default=300) # NUEVO: segundos
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
```

Nueva tabla `AgentExecution`:

```python
class AgentExecution(Base):
    __tablename__ = 'agent_executions'
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('agents.id'), nullable=False)
    task_description = Column(Text)
    status = Column(String(20), default='pending')
    # 'pending'|'running'|'completed'|'failed'|'cancelled'
    result = Column(Text)
    error_message = Column(Text)
    tool_calls = Column(Text)  # JSON: registro de herramientas usadas
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
```

Generar y aplicar la migración:
```bash
cd backend
alembic revision --autogenerate -m "add_agent_fields_and_execution_table"
alembic upgrade head
```

### Paso 2 — Crear el directorio `backend/app/execution/`

**`base_tool.py`**: interfaz abstracta que deben implementar todas las herramientas.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTool(ABC):
    tool_id: str
    name: str
    description: str
    requires_confirmation: bool = False

    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict:
        """Siempre devuelve: {"success": bool, "result": Any, "error": str | None}"""
        pass

    @abstractmethod
    def list_actions(self) -> list:
        pass
```

**`filesystem_tool.py`**: acciones `read_file`, `write_file` (requiere confirmación), `list_dir`, `create_dir` (requiere confirmación), `delete_file` (requiere confirmación), `file_exists`.

Restricciones de seguridad obligatorias:
- Rutas permitidas: dentro de `%USERPROFILE%`
- Rutas bloqueadas: `C:\Windows`, `C:\Program Files`, `/etc`, `/sys`
- No se permite `..` en ningún path
- Tamaño máximo de lectura: 1MB

**`shell_tool.py`**: solo ejecuta comandos de la whitelist:

```python
ALLOWED_COMMANDS = {
    "python": {"max_timeout": 60},
    "pip":    {"max_timeout": 120},
    "git":    {"max_timeout": 30},
    "npm":    {"max_timeout": 120},
    "node":   {"max_timeout": 60},
    "uvicorn":{"max_timeout": 10},
}
```

`requires_confirmation = True` siempre. Nunca permitir cmd, bash, sh, ni strings con `&`, `|`, `;`.

**`git_tool.py`**: solo lectura sin confirmación (`status`, `log`, `diff`, `branch_list`). Con confirmación: `commit`, `add`.

**`powershell_tool.py`**: solo ejecuta scripts `.ps1` ubicados en `%USERPROFILE%/AitheraScripts/`. Nunca strings PowerShell arbitrarios.

**`engine.py`**: el ExecutionEngine central:

```python
class ExecutionEngine:
    async def execute(self, tool_id, action, params, allowed_tools=None, timeout=30) -> Dict:
        # 1. Verificar que la herramienta existe en el registro
        # 2. Verificar que el agente tiene acceso (allowed_tools)
        # 3. Validar parámetros: buscar "../", "C:\\Windows", etc.
        # 4. Ejecutar con asyncio.wait_for(timeout=timeout)
        # 5. Registrar en log en memoria (últimas 100 ejecuciones)
        # 6. Devolver resultado estructurado

execution_engine = ExecutionEngine()  # Singleton
```

**`__init__.py`**: registra todas las herramientas al importar:

```python
from app.execution.engine import register_tool
from app.execution.filesystem_tool import FilesystemTool
from app.execution.shell_tool import ShellTool
from app.execution.git_tool import GitTool
from app.execution.powershell_tool import PowerShellTool

register_tool(FilesystemTool())
register_tool(ShellTool())
register_tool(GitTool())
register_tool(PowerShellTool())
```

### Paso 3 — Registrar en `backend/app/main.py`

```python
import app.execution  # Registra las herramientas al importar
```

### ✅ Checkpoint Sesión 1 — verificar antes de parar

- [ ] `alembic upgrade head` aplicó la migración sin errores
- [ ] La tabla `agent_executions` existe en PostgreSQL
- [ ] Los campos `allowed_tools` y `max_execution_time` existen en la tabla `agents`
- [ ] El backend arranca sin errores con `import app.execution`
- [ ] `GET /api/tools/` (crear endpoint básico en esta sesión o verificar en Sesión 2) devuelve 4 herramientas

### 🛑 Para aquí

Commit: `feat: Execution Engine + 4 herramientas registradas`. La Sesión 2 implementa el AgentManager.

---

## SESIÓN 2: AgentManager + schemas + endpoints

**Tiempo estimado**: 2-3 horas
**Empieza con**: Sesión 1 completada, herramientas registradas

### Paso 1 — AgentManager

Crear `backend/app/agents/agent_manager.py`:

```python
class AgentManager:
    """
    Gestiona el ciclo de vida de los agentes.
    - execute_task(): lanza una tarea de forma asíncrona, devuelve execution_id
    - _run_task(): interno, llama a AIManager + ExecutionEngine según el plan
    - cancel_task(): cancela una tarea en curso
    - get_status(): consulta el estado de una ejecución
    """

    def __init__(self):
        self._running_tasks: Dict[int, asyncio.Task] = {}

    async def execute_task(self, agent_id, task_description, context=None) -> int:
        # 1. Cargar agente de DB
        # 2. Crear AgentExecution con status='pending'
        # 3. asyncio.create_task(_run_task(...))
        # 4. Devolver execution_id

    async def _run_task(self, execution_id, agent_id, task, context):
        # 1. Marcar status='running'
        # 2. Llamar ai_manager.chat() con prompt de planificación
        # 3. Parsear respuesta: ¿usa herramienta? → execution_engine.execute()
        # 4. Marcar status='completed'/'failed' con resultado

    async def cancel_task(self, execution_id) -> bool:
        # Cancelar asyncio.Task + marcar status='cancelled' en DB

    def get_status(self, execution_id) -> Dict:
        # Leer AgentExecution de DB y devolver como dict

agent_manager = AgentManager()  # Singleton
```

El prompt de planificación que usa `_run_task`:

```python
planning_prompt = f"""Tarea: {task}
Herramientas disponibles: {allowed_tools}

Si necesitas una herramienta, responde con JSON:
{{"use_tool": true, "tool_id": "filesystem", "action": "read_file", "params": {{"path": "..."}}}}

Si puedes responder directamente:
{{"use_tool": false, "response": "..."}}"""
```

### Paso 2 — Actualizar schemas.py

```python
class AgentCreate(BaseModel):
    name: str
    agent_type: str = "generic"
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    allowed_tools: List[str] = []
    max_execution_time: int = 300

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    agent_type: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    max_execution_time: Optional[int] = None
    is_active: Optional[bool] = None

class AgentResponse(BaseModel):
    id: int
    name: str
    agent_type: str = "generic"
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    allowed_tools: List[str] = []
    max_execution_time: int = 300
    is_active: bool = True
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

    @validator('allowed_tools', pre=True)
    def parse_allowed_tools(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v or '[]')
        return v or []

class AgentExecutionResponse(BaseModel):
    id: int
    agent_id: int
    task_description: str
    status: str
    result: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
```

### Paso 3 — Nuevos endpoints

**Añadir en `backend/app/api/endpoints/agents.py`** (sin quitar los existentes):

```
POST /api/agents/{id}/execute
    Body: { "task": "descripción", "context": {} }
    Response: { "execution_id": 123, "status": "pending" }

GET /api/agents/executions/{execution_id}
    Response: AgentExecutionResponse

DELETE /api/agents/executions/{execution_id}
    Response: { "cancelled": bool }

GET /api/agents/{id}/executions
    Response: lista últimas 20 ejecuciones del agente
```

**Crear `backend/app/api/endpoints/tools.py`**:

```
GET /api/tools/
    Response: lista de herramientas registradas con acciones

GET /api/tools/execution-log
    Response: últimas 100 ejecuciones del ExecutionEngine
```

**Registrar en `backend/app/main.py`**:
```python
from app.api.endpoints import tools as tools_router
app.include_router(tools_router.router, prefix="/api")
```

### ✅ Checkpoint Sesión 2 — verificar antes de parar

- [ ] `GET /api/tools/` devuelve las 4 herramientas registradas con sus acciones
- [ ] `POST /api/agents/{id}/execute` crea una ejecución y devuelve `execution_id`
- [ ] `GET /api/agents/executions/{id}` devuelve el estado
- [ ] Una tarea simple (sin herramienta) se completa con respuesta de la IA
- [ ] Una tarea con herramienta (ej: "lista el directorio de escritorio") llama a FilesystemTool
- [ ] ShellTool rechaza comandos fuera de la whitelist (probar con "rm -rf")
- [ ] FilesystemTool rechaza paths con ".."

### 🛑 Para aquí

Commit: `feat: AgentManager + endpoints de ejecución`. La Sesión 3 implementa la UI.

---

## SESIÓN 3: UI de Agentes completa

**Tiempo estimado**: 2-3 horas
**Empieza con**: backend de Sesión 2 funcionando, endpoints de ejecución probados

### Reescribir `frontend/src/pages/Agents.tsx`

La página tiene 3 secciones:

**1. Lista de agentes** — tabla con: nombre, tipo (`generic/minimax/ollama/claude_code`), herramientas asignadas (badges), estado activo/inactivo (toggle), botones (editar, ejecutar, eliminar).

**2. Formulario de agente** — modal con:
- Nombre, tipo (dropdown), descripción
- System prompt (textarea grande)
- Herramientas permitidas: checkboxes generados dinámicamente desde `GET /api/tools/`
- Tiempo máximo de ejecución (número en segundos)

**3. Panel de ejecución** — cuando el usuario pulsa "Ejecutar":
- Campo de texto para describir la tarea
- Botón "Lanzar tarea"
- Panel de estado: actualización automática cada 2s con `GET /api/agents/executions/{id}`
- Indicadores visuales: Pendiente → Ejecutando → Completado / Fallido
- Resultado formateado (detectar JSON y formatearlo, o texto plano)
- Botón "Cancelar" visible mientras status = 'running'

### Bump de versión

- `backend/app/main.py`: `version="0.5.0"`
- `backend/app/core/config.py`: `VERSION = "0.5.0"`
- `frontend/package.json`: `"version": "0.5.0"`

### ✅ Checkpoint Sesión 3 — verificar antes de parar

- [ ] Puedo crear un agente con herramientas asignadas desde la UI
- [ ] La lista de checkboxes de herramientas viene de `GET /api/tools/` (no está hardcodeada)
- [ ] Puedo lanzar una tarea y ver el estado actualizarse en tiempo real
- [ ] El resultado aparece cuando la tarea se completa
- [ ] El botón "Cancelar" funciona y marca la ejecución como 'cancelled'
- [ ] La versión en `GET /` es `"0.5.0"`

### 🛑 Para aquí

Aithera V0.5.0 completada. Commit: `feat: V0.5.0 — AgentManager + ExecutionEngine + UI de Agentes`.

**Siguiente fase**: `Fase_3_Memory_ChromaDB_V05.md`

---

## ARCHIVOS CREADOS/MODIFICADOS EN ESTA FASE

**Sesión 1**: `backend/app/db/database.py` (Agent + AgentExecution), `backend/app/execution/` (directorio completo: engine.py, base_tool.py, filesystem_tool.py, shell_tool.py, git_tool.py, powershell_tool.py, __init__.py), `backend/app/main.py` (import execution), nueva migración Alembic

**Sesión 2**: `backend/app/agents/agent_manager.py`, `backend/app/db/schemas.py`, `backend/app/api/endpoints/agents.py` (nuevos endpoints), `backend/app/api/endpoints/tools.py` (nuevo), `backend/app/main.py` (registrar router tools)

**Sesión 3**: `frontend/src/pages/Agents.tsx`, versiones en package.json, main.py, config.py
