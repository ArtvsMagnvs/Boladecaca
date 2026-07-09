# SDKs comparison — Oficial vs community

## Resumen

Comparativa de SDKs oficiales y community para los principales proveedores LLM.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Matriz SDKs

| Proveedor | SDK oficial | Lenguajes | Licencia | Notas |
|---|---|---|---|---|
| **OpenAI** | `openai/openai-python` | Python, JS, Go, Ruby, Java, .NET, Rust, Swift | Apache-2.0 | Gold standard, Stainless-generated |
| **Anthropic** | `anthropics/anthropic-sdk-python` | Python, JS, Go, Ruby, Java, PHP, C#, Rust, Swift | MIT | 3.713★ |
| **Google Gemini** | `google-gemini/generative-ai-python` | Python, JS, Go, Java, Swift, Dart (Flutter) | Apache-2.0 | 3.913★ |
| **DeepSeek** | NO oficial — usar OpenAI SDK | n/a | n/a | 100% OpenAI-compat |
| **Mistral** | `mistralai/client-python` | Python, JS | Apache-2.0 | También OpenAI-compat |
| **Qwen** | DashScope SDK | Python, JS | Alibaba license | OpenAI-compat mode |
| **Cohere** | `cohere-ai/cohere-python` | Python, JS, Java, Go | MIT/Custom | Formato propio |
| **xAI Grok** | NO oficial — usar OpenAI SDK | n/a | n/a | 100% OpenAI-compat |
| **Perplexity** | NO oficial — REST | n/a | n/a | Formato propio |
| **Ollama** | NO oficial server; Python lib | Python | MIT | OpenAI-compat |
| **OpenRouter** | OpenAI SDK | Multi | n/a | Aggregator |

## OpenAI Python SDK — el más usado

```python
from openai import OpenAI

client = OpenAI(
    api_key="...",
    base_url="https://api.openai.com/v1"  # o cualquier OpenAI-compat
)

response = client.chat.completions.create(
    model="gpt-5.5",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

**Para Aithera**: usar `OpenAI` (o `AsyncOpenAI`) para todos los proveedores OpenAI-compat (OpenAI, DeepSeek, Mistral, Qwen, Grok, Ollama, LM Studio). Solo Anthropic y Gemini necesitan SDK nativo.

## HTTPX (fallback universal)

Si un SDK falla, `httpx` siempre funciona:

```python
import httpx

response = await httpx.AsyncClient().post(
    "https://api.example.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {api_key}"},
    json={"model": "...", "messages": [...]}
)
```

## Stainless

OpenAI Python SDK es generado con **Stainless** desde el OpenAPI spec. Esto significa:
- API coverage siempre al día.
- Tipos perfectos.
- Auto-retry built-in.
- Misma DX para todos los SDKs OpenAI-compat.

## Para Aithera V0.7.3

Aithera usa:
- `openai` (Python SDK) — para OpenAI, DeepSeek, Mistral, Grok, Ollama, etc.
- `anthropic` (Python SDK) — para Claude.
- `google-generativeai` (Python SDK) — para Gemini.
- `openai-minimax` (custom, no existe) — usa `openai_compatible.py` con base_url MiniMax.

## Referencias cruzadas

- [JWIKI-020 openai.md](./openai.md)
- [JWIKI-021 anthropic.md](./anthropic.md)
- [JWIKI-022 gemini.md](./gemini.md)

## Fuentes

1. https://github.com/openai/openai-python — 31.121★, Apache-2.0
2. https://github.com/anthropics/anthropic-sdk-python — 3.713★, MIT
3. https://github.com/google-gemini/generative-ai-python — 3.913★, Apache-2.0

## Nivel de confianza

**90%** — SDKs bien establecidos.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified