# Tool Calling — Formato LLM

## Resumen

**Tool calling format** varía por proveedor. OpenAI usa `tools` array, Anthropic usa `tools` también pero con `input_schema`, Gemini usa `function_declarations`. Aithera abstrae con Pydantic.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## OpenAI format

```python
response = openai.chat.completions.create(
    model="gpt-5",
    messages=[...],
    tools=[{
        "type": "function",
        "function": {
            "name": "email.send",
            "description": "Send an email",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["to", "subject", "body"]
            }
        }
    }]
)

# Response
choice.message.tool_calls = [{
    "id": "call_123",
    "type": "function",
    "function": {
        "name": "email.send",
        "arguments": '{"to": "...", "subject": "...", "body": "..."}'
    }
}]
```

## Anthropic format

```python
response = anthropic.messages.create(
    model="claude-opus-4-8",
    messages=[...],
    tools=[{
        "name": "email_send",
        "description": "Send an email",
        "input_schema": {
            "type": "object",
            "properties": {...},
            "required": [...]
        }
    }]
)

# Response
response.content = [{
    "type": "tool_use",
    "id": "toolu_123",
    "name": "email_send",
    "input": {"to": "...", ...}
}]
```

## Gemini format

```python
response = genai.generate_content(
    model="gemini-3.5-pro",
    contents=[...],
    tools=[genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name="email_send",
                description="...",
                parameters=genai.protos.Schema(...)
            )
        ]
    )]
)

# Response
response.candidates[0].content.parts[0].function_call = {
    "name": "email_send",
    "args": {"to": "...", ...}
}
```

## Aithera abstraction (Pydantic → auto-convert)

```python
class ToolConverter:
    @staticmethod
    def to_openai(schema: dict) -> dict:
        return {
            "type": "function",
            "function": {
                "name": schema["title"],
                "description": schema["description"],
                "parameters": schema
            }
        }
    
    @staticmethod
    def to_anthropic(schema: dict) -> dict:
        return {
            "name": schema["title"],
            "description": schema["description"],
            "input_schema": schema
        }
    
    @staticmethod
    def to_gemini(schema: dict) -> dict:
        # Convert to genai.protos.Schema
        ...
```

## Para Aithera

- ✅ V0.5+: tool calling format per provider.
- ✅ V0.7.3: Pydantic abstraction.

## Referencias cruzadas

- [JWIKI-034 function-calling.md](../05_AI_PROVIDERS/function-calling.md)
- CLAUDE.md §10

## Fuentes

1. https://platform.openai.com/docs/guides/function-calling
2. https://docs.anthropic.com/en/docs/tool-use
3. https://ai.google.dev/gemini-api/docs/function-calling

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified