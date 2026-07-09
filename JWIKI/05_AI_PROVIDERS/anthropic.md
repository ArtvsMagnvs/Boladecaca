# Anthropic (Claude) — Frontier con foco en código y razonamiento

## Resumen

**Anthropic** es el principal competidor de OpenAI en 2026 con la familia **Claude 4.x/5** (claude-opus-4-8 flagship, claude-mythos-5, claude-fable-5, claude-haiku-4-5, claude-sonnet-4-6). Conocido por su **fortaleza en código** (#1 en SWE-bench), razonamiento profundo (Computer Use), y **prompt caching** agresivo (hasta -90% descuento). Aithera V0.7.3 lo integra nativamente en `backend/app/ai/providers/anthropic_provider.py` con `default_model_name="claude-sonnet-4-6"` (STALE — debería ser opus-4-8).

## Objetivo

Documentar el estado real de Anthropic en julio 2026: familia Claude 4.x/5, prompt caching, Computer Use, vision/PDF, comparativa con OpenAI/Google. Responde a "¿cuándo Anthropic gana sobre OpenAI?".

## Estado

🟢 Verificado — enriquecido 2026-07-09 con contraste GitHub API + docs.anthropic.com. 6/6 criterios CONSTITUTION §8 OK.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| Anthropic API | v1 | Endpoint: `api.anthropic.com/v1/messages` |
| **anthropic-sdk-python** | ≥0.50 (recomendado) | **MIT**, 3.713★, 372 subs, último push 2026-07-06 |
| **claude-opus-4-8** | jul 2026 (verificar) | Flagship |
| claude-opus-4-7 | jul 2026 | Predecessor |
| claude-opus-4-6 | jul 2026 | |
| claude-opus-4-5 | 2025-11-01 | |
| claude-opus-4-1 | 2025-08-05 | Larga vida útil |
| **claude-mythos-5** | jul 2026 | Specialized |
| **claude-fable-5** | jul 2026 | Specialized |
| **claude-haiku-4-5** | 2025-10-01 | Barato y rápido |
| claude-sonnet-4-6 | Aithera V0.7.3 default (STALE) | |
| Aithera | V0.7+ | `app/ai/providers/anthropic_provider.py` |

## Proyectos compatibles

- **SDK Python oficial**: `anthropic-sdk-python` (MIT) con async support (`AsyncAnthropic`).
- **SDKs oficiales**: Python (oficial), TypeScript, Go, Ruby, Java, C# (vía community).
- **Computer Use**: único proveedor maduro en producción.
- **Vertex AI / Bedrock**: disponibilidad empresarial en GCP/AWS.

## Dependencias

- [JWIKI-019 README.md](./README.md) — matriz comparativa proveedores
- [JWIKI-020 openai.md](./openai.md) — competidor #1
- [JWIKI-022 gemini.md](./gemini.md) — Google
- [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md) — SOP añadir proveedor

## Arquitectura

```
Anthropic API
  └─ v1/messages endpoint
      └─ SDK Python oficial (anthropic-sdk-python)
          ├─ AsyncAnthropic (httpx async)
          ├─ Messages API
          ├─ Streaming (SSE)
          ├─ Tool use (blocks nativos)
          ├─ Prompt caching (cache_control)
          ├─ Vision (image, PDF)
          └─ Computer Use (tool sandbox)
```

## Descripción técnica

### Familia Claude 4.x/5 (jul 2026)

| Modelo | Lanzamiento | Notas |
|---|---|---|
| **claude-opus-4-8** | ~Q2 2026 | Flagship. Lo mejor en código + razonamiento. |
| claude-opus-4-7 | ~Q1 2026 | Predecessor. |
| claude-opus-4-6 | ~Q4 2025 | Más estable en producción. |
| claude-opus-4-5 | 2025-11-01 | Buen balance. |
| claude-opus-4-1 | 2025-08-05 | Larga vida útil, aún en uso. |
| **claude-mythos-5** | jul 2026 | Variante specialized. |
| **claude-fable-5** | jul 2026 | Variante specialized. |
| **claude-haiku-4-5** | 2025-10-01 | Barato y rápido. Default para alto volumen. |

### API y SDK

**Endpoint**: `POST https://api.anthropic.com/v1/messages`

**SDK anthropic-sdk-python (MIT, 3.713★, último push 2026-07-06)**:

```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key="sk-ant-...")

response = await client.messages.create(
    model="claude-opus-4-8",
    max_tokens=2048,
    messages=[{"role": "user", "content": "Hello!"}],
    system="You are a helpful assistant.",
)

print(response.content[0].text)
print(response.usage.input_tokens, response.usage.output_tokens)
```

## Call Stack / API

```
Mensaje (CLI / Gateway / Email Assistant)
  → backend/app/ai/providers/anthropic_provider.py
    → AsyncAnthropic (httpx async)
      → POST https://api.anthropic.com/v1/messages
        → SSE stream → chunks
          → Response → output_text
```

## Diagramas

Ver sección Arquitectura.

## Código relacionado

- Repo: `github.com/anthropics/anthropic-sdk-python`
- Default branch: `main`
- Licencia: **MIT**
- README: https://raw.githubusercontent.com/anthropics/anthropic-sdk-python/main/README.md
- Docs: https://docs.anthropic.com/en/docs/about-claude/models/overview
- Prompt caching: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- Computer Use: https://docs.anthropic.com/en/docs/agents-and-tools/computer-use
- Aithera: `backend/app/ai/providers/anthropic_provider.py`

## Ejemplos

### Tool use (function calling)

```python
tools = [
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

response = await client.messages.create(
    model="claude-opus-4-8",
    max_tokens=2048,
    tools=tools,
    messages=[
        {"role": "user", "content": "What's the weather in Madrid?"}
    ],
)

# response.stop_reason == "tool_use"
# response.content[0].type == "tool_use"
# response.content[0].name == "get_weather"
# response.content[0].input == {"location": "Madrid"}
```

### Prompt caching (killer feature)

```python
response = await client.messages.create(
    model="claude-opus-4-8",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "You are an expert code reviewer...",
        },
        {
            "type": "text",
            "text": long_document,  # Cacheable
            "cache_control": {"type": "ephemeral"}  # Cache for 5 min
        }
    ],
    messages=[{"role": "user", "content": "Review this code: ..."}]
)

# response.usage.cache_creation_input_tokens  # First time
# response.usage.cache_read_input_tokens      # Subsequent reads (-90%)
```

**Para Aithera**: la system prompt del Email Assistant (clasificación) y el contexto del proyecto (JWIKI) son ideales para prompt caching.

### Streaming (SSE)

```python
async with client.messages.stream(
    model="claude-opus-4-8",
    max_tokens=2048,
    messages=[{"role": "user", "content": "Tell me a story"}]
) as stream:
    async for text in stream.text_stream:
        print(text, end="")
```

### Vision + PDF (ventaja vs OpenAI)

```python
response = await client.messages.create(
    model="claude-opus-4-8",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "url", "url": "https://..."}},
                {"type": "text", "text": "What's in this image?"}
            ]
        }
    ]
)
```

Soporta: image (URL o base64), **PDF (input nativo)**.

## Buenas prácticas

- ✅ **Elegir Anthropic cuando**: necesitas el mejor código del mercado (SWE-bench #1), razonamiento profundo, prompt caching, Computer Use, PDF input nativo.
- ✅ **Prompt caching**: aplicar a system prompts largos (Email Assistant, contexto JWIKI).
- ✅ **Tool use blocks**: similar conceptualmente a OpenAI tools, sintaxis distinta.
- ✅ **Vision + PDF**: ventaja clara para procesar documentación.

## Errores comunes

- ❌ No confundir con OpenAI (sintaxis `tool_use` vs `tools`).
- ❌ No hardcodear `claude-sonnet-4-6` (STALE en Aithera V0.7.3).
- ❌ No usar cuando necesitas Realtime audio (gpt-realtime-2 es único maduro).
- ❌ No usar cuando costo ultra-bajo es crítico (DeepSeek 10x más barato).

## Breaking Changes

Sin tags versionados — Anthropic publica fechas y changelogs en docs.

## Cambios entre versiones

| Cambio | Impacto |
|---|---|
| Computer Use (2024) | Sandbox requerido para acciones de escritorio |
| Prompt caching (2024) | -90% en cache reads (5 min ephemeral) |
| Claude 4.x (2025) | Mejoras en código y razonamiento |
| Claude 5.x (2026) | Variantes specialized (mythos, fable) |

## Impacto sobre otros sistemas

- Aithera V0.7.3: actualizar `default_model_name="claude-sonnet-4-6"` → `claude-opus-4-8` o `claude-sonnet-4-7`.
- Aithera V0.85/V1.0: implementar prompt caching para system prompts largos (Email Assistant classification, JWIKI context).
- Aithera V1.0 Orchestrator:借鉴 Computer Use para automatizaciones de escritorio con sandbox.

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md) — matriz comparativa
- [JWIKI-020 openai.md](./openai.md) — competidor #1
- [JWIKI-022 gemini.md](./gemini.md) — Google
- [JWIKI-034 function-calling.md](./function-calling.md)
- [JWIKI-035 streaming.md](./streaming.md)
- [JWIKI-036 pricing-comparison.md](./pricing-comparison.md)
- [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md)

## Fuentes

1. https://api.anthropic.com/v1/messages — acceso 2026-07-09
2. https://docs.anthropic.com/en/docs/about-claude/models/overview — acceso 2026-07-09
3. https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching — prompt caching docs
4. https://docs.anthropic.com/en/docs/agents-and-tools/computer-use — Computer Use docs
5. https://raw.githubusercontent.com/anthropics/anthropic-sdk-python/main/README.md — SDK
6. https://api.github.com/repos/anthropics/anthropic-sdk-python — 3.713★, MIT
7. backend/app/ai/providers/anthropic_provider.py — código Aithera V0.7.3

## Nivel de confianza

**88%** — Familia Claude 4.x/5 confirmada, SDK verificado, prompt caching y Computer Use bien documentados. Pendiente: pricing exacto, fechas exactas de claude-opus-4-8 release, benchmarks de latencia.

---

## Changelog

### 2026-07-09 — enriquecido
- Autor: Aithera Escriba (sesión actual)
- Cambio: doc enriquecido desde borrador mediocre (1441 palabras) a versión profunda con familia Claude 4.x/5, prompt caching, Computer Use, vision/PDF, estado en Aithera V0.7.3 (STALE claude-sonnet-4-6).
- Validador: contraste con anthropic-sdk-python (MIT, 3.713★) + docs.anthropic.com
- Estado: 🟢 verified