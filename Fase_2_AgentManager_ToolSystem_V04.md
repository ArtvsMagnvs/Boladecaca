# FASE 2 — V0.4: Agent Manager + Tool System
## Documento de implementación para Claude Code
**Versión objetivo**: Aithera V0.4.0
**Prerrequisito**: Aithera V0.3.0 completada
**Tiempo estimado**: 2-3 sesiones

---

## OBJETIVO DE ESTA FASE

Construir el sistema profesional de agentes y herramientas. Al final de esta fase, Aithera puede registrar agentes especializados, asignarles herramientas autorizadas, y ejecutar tareas de forma controlada.

---

## TAREA 1 — Rediseño del modelo Agent en la DB

### Cambios en `backend/app/db/database.py`

El modelo `Agent` actual es demasiado simple. Reemplazarlo con:

```python
class Agent(Base):
    __tablename__ = 'agents'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    agent_type = Column(String(50), default='generic')  # 'generic'|'claude_code'|'minimax'|'ollama'|'custom'
    description = Column(Text)
    system_prompt = Column(Text)
    allowed_tools = Column(Text)      # JSON list: ["filesystem", "git", "shell"]
    max_execution_time = Column(Integer, default=300)  # segundos
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
```

Añadir nueva tabla para log de ejecuciones:

```python
class AgentExecution(Base):
    __tablename__ = 'agent_executions'
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('agents.id'))
    task_description = Column(Text)
    status = Column(String(20), default='pending')  # 'pending'|'running'|'completed'|'failed'|'cancelled'
    result = Column(Text)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
```

Añadir a `_ensure_columns()` las nuevas columnas de `agents`:
```python
'agents': {
    'allowed_tools': "ALTER TABLE agents ADD COLUMN allowed_tools TEXT DEFAULT '[]'",
    'max_execution_time': "ALTER TABLE agents ADD COLUMN max_execution_time INTEGER DEFAULT 300",
},
```

---

## TAREA 2 — Tool System

### Crear `backend/app/tools/` (nuevo directorio)

**`backend/app/tools/base.py`** — Interfaz base para todas las herramientas:

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseTool(ABC):
    """Interfaz que deben implementar todas las herramientas de Aithera."""
    
    tool_id: str          # Identificador único: "filesystem", "git", "shell"
    name: str             # Nombre legible: "Filesystem Tool"
    description: str      # Descripción de qué hace la herramienta
    requires_confirmation: bool = False  # Si True, pide confirmación al usuario
    
    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una acción de la herramienta.
        
        Args:
            action: La acción a ejecutar (ej. "read_file", "list_dir")
            params: Parámetros de la acción
            
        Returns:
            Dict con: {"success": bool, "result": Any, "error": Optional[str]}
        """
        pass
    
    @abstractmethod
    def list_actions(self) -> list:
        """Devuelve lista de acciones disponibles con su descripción."""
        pass
    
    def validate_params(self, action: str, params: Dict[str, Any]) -> bool:
        """Valida que los parámetros sean correctos para la acción dada. Override si necesario."""
        return True
```

**`backend/app/tools/filesystem_tool.py`** — Herramienta de sistema de archivos:

Acciones disponibles:
- `read_file`: Lee el contenido de un archivo (parámetros: `path`)
- `write_file`: Escribe en un archivo (parámetros: `path`, `content`) — requiere confirmación
- `list_dir`: Lista el contenido de un directorio (parámetros: `path`)
- `create_dir`: Crea un directorio (parámetros: `path`) — requiere confirmación
- `delete_file`: Elimina un archivo (parámetros: `path`) — requiere confirmación
- `file_exists`: Comprueba si existe un archivo (parámetros: `path`)

**Restricciones de seguridad obligatorias**:
- No permitir rutas con `..` (path traversal)
- No permitir acceso a rutas del sistema (`C:\Windows`, `/etc`, `/sys`, etc.)
- Solo operar dentro de `%USERPROFILE%` o rutas explícitamente configuradas
- Registrar todas las operaciones en el log

**`backend/app/tools/shell_tool.py`** — Herramienta de ejecución de comandos:

Acciones disponibles:
- `run_command`: Ejecuta un comando de la whitelist (parámetros: `command`, `args`, `cwd`)

**Whitelist obligatoria** — SOLO estos comandos están permitidos:
```python
ALLOWED_COMMANDS = {
    "python": True,
    "pip": True,
    "git": True,
    "npm": True,
    "node": True,
    "uvicorn": True,
}
```

Nunca permitir: `rm`, `del`, `format`, `shutdown`, `regedit`, `cmd /c`, ni ejecución de strings dinámicos.

`requires_confirmation = True` por defecto en `ShellTool`.

**`backend/app/tools/git_tool.py`** — Herramienta de Git:

Acciones disponibles:
- `status`: `git status` en un repositorio (parámetros: `repo_path`)
- `log`: `git log --oneline -10` (parámetros: `repo_path`)
- `diff`: `git diff` (parámetros: `repo_path`)
- `commit`: `git commit -m` (parámetros: `repo_path`, `message`) — requiere confirmación
- `branch_list`: `git branch -a` (parámetros: `repo_path`)

### Crear `backend/app/tools/tool_manager.py` — Registro centralizado de herramientas:

```python
class ToolManager:
    """Registro centralizado de todas las herramientas disponibles en Aithera."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Registra las herramientas incluidas por defecto."""
        from .filesystem_tool import FilesystemTool
        from .shell_tool import ShellTool
        from .git_tool import GitTool
        
        self.register(FilesystemTool())
        self.register(ShellTool())
        self.register(GitTool())
    
    def register(self, tool: BaseTool):
        """Registra una herramienta. Permite añadir herramientas custom en el futuro."""
        self._tools[tool.tool_id] = tool
    
    def get_tool(self, tool_id: str) -> Optional[BaseTool]:
        return self._tools.get(tool_id)
    
    def list_tools(self) -> List[Dict]:
        return [{"id": t.tool_id, "name": t.name, "description": t.description, 
                 "requires_confirmation": t.requires_confirmation}
                for t in self._tools.values()]
    
    async def execute(self, tool_id: str, action: str, params: Dict) -> Dict:
        """Ejecuta una acción de una herramienta con logging automático."""
        tool = self.get_tool(tool_id)
        if not tool:
            return {"success": False, "error": f"Herramienta '{tool_id}' no encontrada"}
        return await tool.execute(action, params)

# Singleton global
tool_manager = ToolManager()
```

---

## TAREA 3 — Agent Manager

### Crear `backend/app/agents/agent_manager.py`:

```python
class AgentManager:
    """
    Gestiona el ciclo de vida de los agentes: registro, asignación de tareas,
    ejecución, cancelación y consulta de estado.
    
    Aithera es el orquestador. Los agentes son ejecutores.
    El AgentManager nunca toma decisiones de negocio — solo ejecuta lo que se le pide.
    """
    
    def __init__(self):
        self._running_tasks: Dict[int, asyncio.Task] = {}  # execution_id -> asyncio.Task
    
    async def execute_task(
        self,
        agent_id: int,
        task_description: str,
        context: Optional[Dict] = None,
        db: Session = None
    ) -> int:
        """
        Lanza la ejecución de una tarea para un agente.
        Devuelve el execution_id (para consultar estado después).
        La ejecución es asíncrona y no bloqueante.
        """
        # 1. Cargar el agente desde DB
        # 2. Validar que el agente está activo
        # 3. Crear registro AgentExecution en DB (status='pending')
        # 4. Lanzar asyncio.create_task con _run_task()
        # 5. Devolver execution_id
        pass
    
    async def _run_task(self, execution_id: int, agent: Agent, task: str, context: Dict):
        """
        Ejecuta la tarea real del agente. Interno.
        Actualiza el registro AgentExecution conforme avanza.
        """
        # 1. Actualizar status='running' en DB
        # 2. Construir el system prompt del agente con contexto inyectado
        # 3. Llamar a ai_manager.chat() con el task como mensaje
        # 4. Si el resultado indica uso de herramientas, ejecutarlas via tool_manager
        # 5. Actualizar status='completed'/'failed' en DB con el resultado
        pass
    
    async def cancel_task(self, execution_id: int) -> bool:
        """Cancela una tarea en ejecución."""
        task = self._running_tasks.get(execution_id)
        if task and not task.done():
            task.cancel()
            return True
        return False
    
    def get_status(self, execution_id: int, db: Session) -> Dict:
        """Consulta el estado de una ejecución."""
        # Leer AgentExecution de DB
        pass
    
    def get_result(self, execution_id: int, db: Session) -> Optional[str]:
        """Obtiene el resultado de una ejecución completada."""
        pass

# Singleton
agent_manager = AgentManager()
```

---

## TAREA 4 — Nuevos Endpoints de API

### Actualizar `backend/app/api/endpoints/agents.py`

Añadir endpoints nuevos sin romper los existentes:

**`POST /api/agents/{agent_id}/execute`**
```
Body: { "task": "descripción de la tarea", "context": {...} }
Response: { "execution_id": 123, "status": "pending" }
```

**`GET /api/agents/executions/{execution_id}`**
```
Response: { "id": 123, "agent_id": 1, "status": "running|completed|failed", 
            "result": "...", "started_at": "...", "completed_at": "..." }
```

**`DELETE /api/agents/executions/{execution_id}`**
```
Response: { "cancelled": true }
```

**`GET /api/tools/`**
```
Response: [{ "id": "filesystem", "name": "Filesystem Tool", "description": "...", "requires_confirmation": false }]
```

### Añadir router de tools en `backend/app/main.py`:
```python
from app.api.endpoints import tools
app.include_router(tools.router, prefix="/api")
```

---

## TAREA 5 — UI de Agentes en Frontend

### Actualizar `frontend/src/pages/Agents.tsx`

La UI de agentes debe permitir:

1. **Listar agentes** con su tipo, descripción, herramientas asignadas y estado activo/inactivo
2. **Crear agente** con formulario: nombre, tipo (dropdown), descripción, system_prompt, herramientas permitidas (checkboxes con la lista de `/api/tools/`), tiempo máximo
3. **Ejecutar tarea** en un agente: campo de texto para describir la tarea + botón "Ejecutar"
4. **Ver resultado**: panel que muestra el estado de la ejecución en tiempo real (polling a `/api/agents/executions/{id}` cada 2s)
5. **Cancelar ejecución** en curso

Los tipos de agente disponibles en el dropdown:
- `generic` — Usa el proveedor IA activo
- `minimax` — Fuerza uso de MiniMax
- `ollama` — Fuerza uso de Ollama (local)
- `claude_code` — Agente especial (Fase 8, deshabilitado por ahora)

---

## TAREA 6 — Actualizar schemas.py

Añadir/actualizar schemas para `Agent` y `AgentExecution`:

```python
class AgentCreate(BaseModel):
    name: str
    agent_type: str = "generic"
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    allowed_tools: List[str] = []  # lista de tool_ids
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
    agent_type: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    allowed_tools: List[str] = []
    max_execution_time: int
    is_active: bool
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

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

Nota: `allowed_tools` se serializa como JSON string en SQLite. Añadir un `@validator` en `AgentResponse` que deserialice el string JSON a lista Python.

---

## TAREA 7 — Instalar dependencias nuevas

`backend/requirements.txt` — no hay dependencias nuevas en esta fase. Todo es Python nativo (`asyncio`, `subprocess`, `json`).

---

## CRITERIOS DE ACEPTACIÓN

Esta fase está completa cuando:

1. ✅ `GET /api/tools/` devuelve la lista de herramientas registradas
2. ✅ Puedo crear un agente con herramientas asignadas desde la UI
3. ✅ `POST /api/agents/{id}/execute` crea una ejecución y devuelve `execution_id`
4. ✅ `GET /api/agents/executions/{id}` devuelve el estado actualizado
5. ✅ La ejecución de una tarea llama al AIManager y devuelve un resultado
6. ✅ `DELETE /api/agents/executions/{id}` cancela una tarea en curso
7. ✅ `FilesystemTool` rechaza rutas con `..` o rutas de sistema
8. ✅ `ShellTool` rechaza comandos no incluidos en la whitelist
9. ✅ Las ejecuciones quedan registradas en la tabla `agent_executions`
10. ✅ La UI de Agentes muestra el resultado de la ejecución en tiempo real

---

## ARCHIVOS CREADOS/MODIFICADOS EN ESTA FASE

**Nuevo directorio**: `backend/app/tools/`
- `backend/app/tools/__init__.py`
- `backend/app/tools/base.py`
- `backend/app/tools/filesystem_tool.py`
- `backend/app/tools/shell_tool.py`
- `backend/app/tools/git_tool.py`
- `backend/app/tools/tool_manager.py`

**Modificados**:
- `backend/app/db/database.py` — Nuevo modelo `AgentExecution`, actualizar `Agent`, actualizar `_ensure_columns()`
- `backend/app/db/schemas.py` — Actualizar `AgentCreate`, `AgentUpdate`, `AgentResponse`; añadir `AgentExecutionResponse`
- `backend/app/agents/agent_manager.py` — Nuevo (o en `backend/app/ai/`)
- `backend/app/api/endpoints/agents.py` — Añadir endpoints de ejecución
- `backend/app/api/endpoints/tools.py` — Nuevo router
- `backend/app/main.py` — Registrar router de tools, bump a v0.4.0
- `frontend/src/pages/Agents.tsx` — Reescribir con UI completa

---

*Al completar esta fase, Aithera V0.4.0 tiene un sistema de agentes real.*
*Siguiente: `Fase_3_Memory_ChromaDB_V05.md`*
