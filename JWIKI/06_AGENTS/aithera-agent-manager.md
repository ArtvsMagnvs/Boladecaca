# Aithera AgentManager — Custom agent framework

## Resumen

**AgentManager** es el framework de agents **custom de Aithera V0.5+**. Ver CLAUDE.md §1 ("AgentManager (15KB)"). NO usa LangGraph/CrewAI/AutoGen.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Ubicación

`backend/app/agents/agent_manager.py` (~15KB).

## Modelos

```python
# backend/app/db/database.py
class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_tools: Mapped[list] = mapped_column(JSON, default=list)  # ["web_search", "email_send", ...]
    max_execution_time: Mapped[int] = mapped_column(Integer, default=3600)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

class AgentExecution(Base):
    __tablename__ = "agent_executions"
    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    status: Mapped[str] = mapped_column(String(20))  # "pending" | "running" | "completed" | "failed"
    tool_calls: Mapped[list] = mapped_column(JSON, default=list)  # [{tool: "...", args: {...}}]
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

## API

```python
# Crear agent
POST /api/agents
Body: {
    "name": "Researcher",
    "description": "...",
    "allowed_tools": ["web_search", "memory_search"],
    "max_execution_time": 3600
}

# Listar agents
GET /api/agents

# Ejecutar agent
POST /api/agents/{id}/execute
Body: {
    "input": "Research X"
}

# Ver executions
GET /api/agents/{id}/executions
```

## AgentManager class (sketch)

```python
class AgentManager:
    def __init__(self, ai_manager, tool_manager, memory_manager):
        self.ai = ai_manager
        self.tools = tool_manager
        self.memory = memory_manager
    
    async def execute(self, agent_id: int, input: str) -> AgentExecution:
        agent = await self._load_agent(agent_id)
        execution = AgentExecution(agent_id=agent_id, status="running", started_at=datetime.utcnow())
        await self._save(execution)
        
        try:
            # Loop: call LLM, parse tool calls, execute, repeat
            context = await self.memory.search(input)
            messages = [
                {"role": "system", "content": agent.description},
                {"role": "user", "content": f"Context: {context}\n\nTask: {input}"}
            ]
            
            for iteration in range(10):  # max iterations
                response = await self.ai.chat(messages, tools=agent.allowed_tools)
                if response.tool_calls:
                    for tool_call in response.tool_calls:
                        if tool_call.name in agent.allowed_tools:
                            result = await self.tools.execute(tool_call.name, tool_call.args)
                            messages.append({"role": "tool", "content": str(result)})
                else:
                    # No more tool calls → done
                    execution.result = response.content
                    execution.status = "completed"
                    break
            
            execution.completed_at = datetime.utcnow()
            await self._save(execution)
            return execution
        
        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            await self._save(execution)
            raise
```

## Para Aithera V1.0

V1.0 Orchestrator reemplazará AgentManager con un Orchestrator más sofisticado (state machines, skills, multi-agent).

## Referencias cruzadas

- [JWIKI-101 README.md](./README.md)
- [JWIKI-105 custom-agent.md](./custom-agent.md)
- [JWIKI-117 agent-loops.md](./agent-loops.md)
- [JWIKI-055 orchestrator-pattern.md](../02_ARCHITECTURE/orchestrator-pattern.md)

## Fuentes

1. CLAUDE.md §1 (AgentManager 15KB)
2. `backend/app/agents/agent_manager.py` (código real)

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified