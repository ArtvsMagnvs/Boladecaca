# Database Schemas - Pydantic models
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator


class AIStatusResponse(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    healthy: bool = False
    # FIX V0.3 (Fase 1 Estabilizacion Hub V03 + fallback automatico): cuando
    # el proveedor primario falla por red/key/5xx, AIManager pasa
    # transparentemente a Ollama. Estos dos campos permiten a la UI avisar al
    # usuario ("IA: Ollama (fallback de MiniMax)") sin tener que adivinar.
    fallback_active: bool = False
    primary_provider: Optional[str] = None


class ConfigCreate(BaseModel):
    key: str
    value: str


class ConfigUpdate(BaseModel):
    key: str
    value: str


class ConfigResponse(BaseModel):
    id: int
    key: str
    value: str

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "active"
    progress: float = 0.0
    priority: str = "medium"
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    # V0.87 (WPMS W1, doc 18 §3.3) — todos opcionales (contrato retrocompatible).
    repo_path: Optional[str] = None
    current_version: Optional[str] = None
    target_version: Optional[str] = None
    start_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    docs: Optional[List[dict]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[float] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    # V0.87 (WPMS W1)
    repo_path: Optional[str] = None
    current_version: Optional[str] = None
    target_version: Optional[str] = None
    start_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    docs: Optional[List[dict]] = None
    archived_at: Optional[datetime] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    status: str
    progress: float
    priority: str = "medium"
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    # V0.87 (WPMS W1)
    repo_path: Optional[str] = None
    current_version: Optional[str] = None
    target_version: Optional[str] = None
    start_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    docs: Optional[List[dict]] = None
    archived_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "pending"
    priority: str = "medium"
    project_id: Optional[int] = None
    due_date: Optional[datetime] = None
    assignee: Optional[str] = None
    # V0.87 (WPMS W1, doc 18 §3.5) — todos opcionales (contrato retrocompatible).
    milestone_id: Optional[int] = None
    checklist: Optional[List[dict]] = None
    depends_on: Optional[List[int]] = None
    estimate: Optional[str] = None
    order_index: Optional[int] = None
    links: Optional[dict] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    project_id: Optional[int] = None
    due_date: Optional[datetime] = None
    assignee: Optional[str] = None
    # V0.87 (WPMS W1)
    milestone_id: Optional[int] = None
    checklist: Optional[List[dict]] = None
    depends_on: Optional[List[int]] = None
    estimate: Optional[str] = None
    order_index: Optional[int] = None
    links: Optional[dict] = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    project_id: Optional[int] = None
    due_date: Optional[datetime] = None
    assignee: Optional[str] = None
    # V0.87 (WPMS W1)
    milestone_id: Optional[int] = None
    checklist: Optional[List[dict]] = None
    depends_on: Optional[List[int]] = None
    estimate: Optional[str] = None
    order_index: Optional[int] = None
    closed_at: Optional[datetime] = None
    links: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# V0.87 (WPMS W1, doc 18 §3.4) — Milestone: el eje de version. progress NO es
# campo del modelo (se calcula); en la respuesta se adjunta calculado por §8.
class MilestoneCreate(BaseModel):
    project_id: int
    name: str
    version: Optional[str] = None
    description: Optional[str] = None
    status: str = "planned"  # planned|active|done|archived
    target_date: Optional[datetime] = None
    order_index: Optional[int] = None


class MilestoneUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    target_date: Optional[datetime] = None
    order_index: Optional[int] = None


class MilestoneResponse(BaseModel):
    id: int
    project_id: Optional[int] = None
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    status: str
    target_date: Optional[datetime] = None
    order_index: int = 0
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # calculado (no columna) — done/total/ratio de sus tareas (doc 18 §8)
    progress: Optional[dict] = None

    class Config:
        from_attributes = True


# FIX V0.2: alineados con el modelo CalendarEvent de la DB (start_date, end_date,
# all_day, color) y con la interfaz TypeScript del frontend (api.ts).
class CalendarEventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    all_day: bool = False
    color: Optional[str] = "#00d4ff"


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    all_day: Optional[bool] = None
    color: Optional[str] = None


class CalendarEventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    all_day: bool = False
    color: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    message: str
    response: Optional[str] = None


class ConversationResponse(BaseModel):
    id: int
    message: str
    response: Optional[str] = None
    timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentCreate(BaseModel):
    """V0.5 (Fase 2 AgentManager + ExecutionEngine): payload para crear
    un agente. allowed_tools es la whitelist de tool_id que el agente
    podra invocar (ej. ["filesystem", "shell"]); max_execution_time es
    el timeout duro en segundos (default 300 = 5 minutos)."""
    name: str
    agent_type: str = "generic"
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    allowed_tools: List[str] = []
    max_execution_time: int = 300
    is_active: bool = True


class AgentUpdate(BaseModel):
    """V0.5: payload parcial para actualizar un agente."""
    name: Optional[str] = None
    agent_type: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    max_execution_time: Optional[int] = None
    is_active: Optional[bool] = None


class AgentResponse(BaseModel):
    """V0.5: respuesta completa. allowed_tools se deserializa del JSON
    string almacenado en BD para que el frontend reciba siempre una lista.

    allowed_tools / max_execution_time / updated_at son Optional para
    mantener compatibilidad con agentes antiguos creados en V0.3 que no
    tenian estas columnas (BD con datos pre-existentes). El AgentManager
    ya pone defaults al crear agentes nuevos."""
    id: int
    name: str
    agent_type: str = "generic"
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    max_execution_time: Optional[int] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @field_validator("allowed_tools", mode="before")
    @classmethod
    def _parse_allowed_tools(cls, v):
        """V0.5: allowed_tools se guarda como JSON string en BD (TEXT)
        para no anadir tipos nativos. Al serializar a la API, lo
        convertimos de vuelta a List[str]. Si es None o vacio, devolvemos []."""
        if v is None or v == "":
            return []
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except (ValueError, TypeError):
                return []
        if isinstance(v, list):
            return v
        return []


class AgentExecutionCreate(BaseModel):
    """V0.5: payload para lanzar una tarea sobre un agente."""
    task: str
    context: Optional[dict] = None


class AgentExecutionResponse(BaseModel):
    """V0.5: estado de una ejecucion (lo que el frontend va sondeando
    cada 2s mientras la tarea corre)."""
    id: int
    agent_id: int
    task_description: Optional[str] = None
    status: str  # 'pending'|'running'|'completed'|'failed'|'cancelled'
    result: Optional[str] = None
    error_message: Optional[str] = None
    tool_calls: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    model: Optional[str] = None
    tokens: Optional[int] = None


# --- Fase 2: Sistema de IA multi-proveedor ---

class AIProviderConfigCreate(BaseModel):
    provider: str
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class AIProviderConfigUpdate(BaseModel):
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class AIProviderConfigResponse(BaseModel):
    """
    Respuesta segura: nunca devuelve la API key en texto plano, solo si
    existe una configurada (has_api_key) y, si la hay, sus ultimos 4
    caracteres para que el usuario pueda reconocerla en la UI.
    """
    provider: str
    label: str
    model: Optional[str] = None
    base_url: Optional[str] = None
    has_api_key: bool = False
    api_key_preview: Optional[str] = None
    is_active: bool = False
    is_configured: bool = False
    requires_key: bool = True
    available_models: List[str] = []


class AITestConnectionResponse(BaseModel):
    provider: str
    healthy: bool
    message: str
