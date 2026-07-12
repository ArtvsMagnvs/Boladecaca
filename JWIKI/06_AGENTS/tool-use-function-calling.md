# Tool Use / Function Calling — Detallado

## Resumen

**Function calling** (tool use) permite al LLM invocar funciones externas estructuradas. Mecanismo base para agents.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Schema

El LLM recibe `tools` array (function definitions), decide si llamar, devuelve `tool_call`:

```json
// Tool definition
{
    "type": "function",
    "function": {
        "name": "email.send",
        "description": "Send an email via Gmail",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email"},
                "subject": {"type": "string"},
                "body": {"type": "string"}
            },
            "required": ["to", "subject", "body"]
        }
    }
}

// Tool call response
{
    "id": "call_abc123",
    "type": "function",
    "function": {
        "name": "email.send",
        "arguments": "{\"to\": \"...\", \"subject\": \"...\", \"body\": \"...\"}"
    }
}
```

## Loop básico

```python
def agent_loop(query, tools, llm, max_iters=10):
    messages = [{"role": "user", "content": query}]
    
    for _ in range(max_iters):
        response = llm.chat(messages, tools=tools)
        msg = response.message
        messages.append(msg)
        
        if not msg.tool_calls:
            return msg.content  # Done
        
        for tc in msg.tool_calls:
            try:
                result = execute_tool(tc.name, tc.arguments)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result)
                })
            except Exception as e:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": f"Error: {e}"
                })
    
    return "Max iterations"
```

## Parallel tool calls

OpenAI/Anthropic soportan múltiples tool calls en 1 response:

```python
async def execute_parallel(tool_calls):
    tasks = [execute_tool_async(tc.name, tc.arguments) for tc in tool_calls]
    return await asyncio.gather(*tasks)
```

## Streaming

```python
async def stream_with_tools(messages, tools, llm):
    async for chunk in llm.stream_chat(messages, tools=tools):
        if chunk.tool_call_delta:
            # accumulate tool call
            ...
        else:
            yield chunk.content
```

## Aithera

Aithera V0.5+ implementa tool calling correctamente. 8 tools disponibles:
- filesystem, shell, git, powershell, email, calendar, voice, memory.

V1.0 Orchestrator añadirá:
- ✅ Parallel tool calls.
- ✅ Multi-tool composition.

## Referencias cruzadas

- [JWIKI-034 function-calling.md](../05_AI_PROVIDERS/function-calling.md)
- [JWIKI-112 tool-use-function-calling.md](./tool-use-function-calling.md)
- [JWIKI-201 tool-calling-llm-format.md](../12_TOOLING/tool-calling-llm-format.md)

## Fuentes

1. https://platform.openai.com/docs/guides/function-calling
2. https://docs.anthropic.com/en/docs/tool-use

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified