# Execution Engine Pattern — Aithera V0.5+

## Resumen

**Execution engine** de Aithera orquesta la ejecución de tools con whitelist + validación + timeout + audit. CLAUDE.md §1 "AgentManager + ExecutionEngine + ToolManager".

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Architecture

```
LLM (decide tool call)
  ↓
AgentManager.execute(agent_id, input)
  ↓
Loop: tool_calls = llm.chat(messages, tools=allowed)
  ↓
For each tool_call:
  ↓
ToolManager.execute(tool_name, args, agent)
  ↓
  1. Whitelist check (agent.allowed_tools)
  2. Schema validation
  3. Execute with timeout
  4. Audit log
  ↓
Result → messages.append({role: "tool", content: result})
  ↓
Until LLM responds without tool_calls
```

## Validation layers (CLAUDE.md §1)

1. **Whitelist**: agent.allowed_tools.
2. **Schema**: tool.validate_args (Pydantic).
3. **Path traversal**: filesystem check.
4. **Command injection**: shell check.
5. **Timeout**: max_execution_time.
6. **Audit**: agent_executions table.

## Implementation sketch

```python
# backend/app/agents/agent_manager.py
class AgentManager:
    async def execute(self, agent_id: int, input: str) -> AgentExecution:
        agent = await self.db.get_agent(agent_id)
        execution = AgentExecution(
            agent_id=agent_id, status="running", started_at=datetime.utcnow()
        )
        await self.db.add(execution)
        
        messages = [
            {"role": "system", "content": agent.description},
            {"role": "user", "content": input}
        ]
        
        try:
            for iteration in range(10):
                response = await self.ai.chat(
                    messages,
                    tools=[tool.schema for tool in agent.allowed_tools]
                )
                messages.append(response.message)
                
                if not response.tool_calls:
                    # Done
                    execution.result = response.content
                    execution.status = "completed"
                    break
                
                for tool_call in response.tool_calls:
                    # Execute via ToolManager
                    result = await self.tools.execute(
                        tool_call.name,
                        tool_call.arguments,
                        agent=agent
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result)
                    })
            
            execution.completed_at = datetime.utcnow()
            await self.db.update(execution)
            return execution
        
        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            await self.db.update(execution)
            raise
```

## Audit trail

Cada execution persiste:

```python
class AgentExecution(Base):
    agent_id: int
    status: str  # pending | running | completed | failed
    tool_calls: list  # [{tool, args, result, duration_ms}]
    result: str | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None
```

## Para Aithera

- ✅ V0.5+: execution engine.
- ✅ V0.7.3: validation 5 capas.
- ⏳ V0.85+: parallel tool calls.
- ⏳ V1.0+: stateful workflows.

## Referencias cruzadas

- [JWIKI-193 tool-manager-pattern.md](./tool-manager-pattern.md)
- CLAUDE.md §1

## Fuentes

1. CLAUDE.md §1

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified