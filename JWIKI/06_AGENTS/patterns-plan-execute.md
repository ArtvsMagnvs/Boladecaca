# Tool Use y Function Calling en Agents

## Resumen

**Tool use** (function calling) es el mecanismo base que permite a los agents invocar tools externas. Es lo que Aithera V0.5 ya implementa en `ToolManager`.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Function calling

LLM recibe `tools` schema, decide si llamar, devuelve tool_call.

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"]
            }
        }
    }
]

response = llm.chat(messages, tools=tools)
# response.tool_calls = [{name: "get_weather", args: {location: "Madrid"}}]
```

## Agent loop básico

```python
def agent_loop(query, tools, llm, max_iters=10):
    messages = [{"role": "user", "content": query}]
    
    for _ in range(max_iters):
        response = llm.chat(messages, tools=tools)
        messages.append(response.message)
        
        if not response.tool_calls:
            return response.content
        
        for tool_call in response.tool_calls:
            try:
                result = execute_tool(tool_call.name, tool_call.arguments)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result)
                })
            except Exception as e:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": f"Error: {e}"
                })
    
    return "Max iters"
```

## Aithera ToolManager

8 tools registrados en `backend/app/tools/`:

| Tool | Función |
|---|---|
| `filesystem` | list_dir, read_file, write_file |
| `shell` | ejecutar comandos |
| `git` | git status, log, diff, commit |
| `powershell` | scripts PS |
| `email` | Gmail REST |
| `calendar` | Google Calendar |
| `voice` | TTS/STT |
| `memory` | ChromaDB search |

## Parallel tool calls

OpenAI/Anthropic soportan **parallel tool calls** (múltiples tools en una sola respuesta):

```python
# response.tool_calls = [
#   {name: "search_X"},
#   {name: "search_Y"},
#   {name: "search_Z"}
# ]
# Ejecutar en paralelo con asyncio.gather
```

## Tool validation

**Crítico** para evitar abuse:
- ✅ Whitelist de tools por agent (`allowed_tools`).
- ✅ JSON schema validation (Pydantic).
- ✅ Timeout (`max_execution_time`).
- ✅ Path traversal prevention.
- ❌ No shell sin whitelist (riesgo).

## MCP (Model Context Protocol)

MCP es un standard para tool calling cross-provider. Soportado por Anthropic, OpenAI (via proxy), Google ADK. Ver [JWIKI-113 mcp.md](../06_AGENTS/mcp.md).

## Para Aithera

Aithera V0.5+ implementa tool calling correctamente. V1.0 Orchestrator añadirá:
- Multi-tool parallel.
- Tool composition (chained tools).
- MCP integration.

## Referencias cruzadas

- [JWIKI-106 aithera-agent-manager.md](./aithera-agent-manager.md)
- [JWIKI-107 patterns-react.md](./patterns-react.md)
- [JWIKI-113 mcp.md](../06_AGENTS/mcp.md)
- [JWIKI-192 execution-engine-pattern.md](../12_TOOLING/execution-engine-pattern.md)

## Fuentes

1. https://platform.openai.com/docs/guides/function-calling
2. https://docs.anthropic.com/en/docs/tool-use
3. CLAUDE.md §1 (ToolManager 11KB)

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified