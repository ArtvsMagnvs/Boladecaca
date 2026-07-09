# Function Calling por proveedor — Estado jul 2026

## Resumen

**Function calling** (tool use) permite que los LLMs invoquen funciones externas estructuradas. Es el patrón base para **agentes**. Cada proveedor tiene su formato y nivel de soporte. Este doc es la **matriz horizontal** complementaria a JWIKI-020..033.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Matriz comparativa

| Proveedor | Soporte | Formato | Streaming tools | Parallel tools |
|---|---|---|---|---|
| **OpenAI** | ✅ nativo, gold standard | OpenAI tools | ✅ | ✅ (parallel tool calls) |
| **Anthropic** | ✅ nativo | tool_use blocks | ✅ | ✅ |
| **Google Gemini** | ✅ nativo | functionDeclarations | ✅ | ✅ |
| **DeepSeek** | ✅ OpenAI-compat | OpenAI tools | ✅ | ✅ |
| **Mistral** | ✅ nativo, OpenAI-compat | OpenAI tools | ✅ | ✅ |
| **Qwen** | ✅ OpenAI-compat (DashScope) | OpenAI tools | ✅ | ✅ |
| **Cohere** | ✅ nativo, formato propio | tools (custom) | ❌ | ❌ |
| **xAI Grok** | ✅ OpenAI-compat | OpenAI tools | ✅ | ✅ |
| **Perplexity** | ⚠️ limitado | search-only | ❌ | ❌ |
| **MiniMax** | ⚠️ limitado (verificar) | OpenAI-compat parcial | ❌ | ❌ |
| **Ollama** | ✅ OpenAI-compat | OpenAI tools | ✅ | ✅ |
| **LM Studio** | ✅ OpenAI-compat | OpenAI tools | ✅ | ✅ |

## Formato OpenAI (estándar de facto)

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get the current weather for a location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {"type": "string"}
          },
          "required": ["location"]
        }
      }
    }
  ]
}
```

## Formato Anthropic (tool_use)

```json
{
  "tools": [
    {
      "name": "get_weather",
      "description": "Get the current weather for a location",
      "input_schema": {
        "type": "object",
        "properties": {
          "location": {"type": "string"}
        },
        "required": ["location"]
      }
    }
  ]
}
```

**Diferencia clave**: Anthropic usa `input_schema` en vez de `parameters`. Conceptualmente idéntico.

## Formato Google Gemini (functionDeclarations)

```json
{
  "tools": [
    {
      "functionDeclarations": [
        {
          "name": "get_weather",
          "description": "Get the current weather for a location",
          "parameters": {
            "type": "object",
            "properties": {
              "location": {"type": "STRING"}  // ← MAYÚSCULAS en Gemini
            },
            "required": ["location"]
          }
        }
      ]
    }
  ]
}
```

**Diferencia clave**: tipos en MAYÚSCULAS (STRING, NUMBER, BOOLEAN, OBJECT, ARRAY).

## Parallel tool calls

OpenAI introdujo **parallel tool calls**: el LLM puede devolver múltiples tool calls en una sola respuesta (el agente los ejecuta en paralelo).

```json
{
  "choices": [{
    "message": {
      "tool_calls": [
        {"id": "1", "function": {"name": "get_weather", "arguments": "{...}"}},
        {"id": "2", "function": {"name": "get_news", "arguments": "{...}"}}
      ]
    }
  }]
}
```

## Streaming con tools

OpenAI soporta tools en stream:
- Chunks normales hasta que el LLM decide invocar tool.
- Luego chunk con `tool_calls` array.

## Para Aithera V0.5 ToolManager

Aithera ya tiene `ToolManager` + 8 tools en `backend/app/tools/`. Formato usado: **OpenAI tools** (estándar). Compatible con todos los proveedores OpenAI-compat.

## Limitaciones comunes

- **MiniMax**: máximo 2048 tokens output → tools con muchos parámetros pueden truncarse.
- **Cohere**: solo 1 tool call por turno (no parallel).
- **Perplexity**: tools no soportados, solo search.

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-020 openai.md](./openai.md)
- [JWIKI-021 anthropic.md](./anthropic.md)
- [JWIKI-022 gemini.md](./gemini.md)
- [JWIKI-192 execution-engine-pattern.md](../12_TOOLING/execution-engine-pattern.md) — ToolManager en Aithera

## Fuentes

1. https://platform.openai.com/docs/guides/function-calling — OpenAI tools
2. https://docs.anthropic.com/en/docs/tool-use — Anthropic tool_use
3. https://ai.google.dev/gemini-api/docs/function-calling — Gemini
4. https://docs.cohere.com/docs/tool-use — Cohere

## Nivel de confianza

**90%** — Matriz consolidada de docs verificados individuales.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified