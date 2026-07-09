# Material crudo JWIKI-021 — Anthropic Claude 4.x/5

> Material de investigación recolectado live 2026-07-09 contra GitHub
> API + raw SDK README + Anthropic models overview page + Anthropic
> pricing page + prompt caching page + Computer Use page.

## Hechos verificados con URL+fecha 2026-07-09

### SDK anthropic-sdk-python (GitHub API live)

- **F1. Stars**: 3.721 — Fuente: `api.github.com/repos/anthropics/anthropic-sdk-python` — Fecha: 2026-07-09
- **F2. Forks**: 765 — Fuente: GitHub API — Fecha: 2026-07-09
- **F3. Open issues**: 331 — Fuente: GitHub API — Fecha: 2026-07-09
- **F4. Licencia**: MIT — Fuente: GitHub API `license.spdx_id` — Fecha: 2026-07-09
- **F5. Lenguaje**: Python — Fuente: GitHub API `language` — Fecha: 2026-07-09
- **F6. Último push (pushed_at)**: 2026-07-08T19:40:23Z — Fuente: GitHub API — Fecha: 2026-07-09
- **F7. Default branch**: main — Fuente: GitHub API — Fecha: 2026-07-09
- **F8. Archived**: false — Fuente: GitHub API — Fecha: 2026-07-09
- **F9. Python requirement**: 3.9+ — Fuente: `raw.githubusercontent.com/anthropics/anthropic-sdk-python/main/README.md` — Fecha: 2026-07-09
- **F10. Install**: `pip install anthropic` — Fuente: README — Fecha: 2026-07-09
- **F11. Default example model**: `claude-opus-4-6` (en README, stale vs production jul 2026) — Fuente: README — Fecha: 2026-07-09
- **F12. Docs**: `platform.claude.com/docs/en/api/sdks/python` — Fuente: README — Fecha: 2026-07-09

### Familia Claude jul 2026 (Anthropic models overview oficial)

- **F13. Modelos activos jul 2026**: Claude Fable 5, Claude Opus 4.8, Claude Sonnet 5, Claude Haiku 4.5 — Fuente: `docs.anthropic.com/en/docs/about-claude/models/overview` — Fecha: 2026-07-09
- **F14. Claude Fable 5** ID `claude-fable-5` — "Next-generation intelligence for long-running agents" — "Anthropic's most capable widely released model" — Fuente: models overview — Fecha: 2026-07-09
- **F15. Claude Mythos 5** ID `claude-mythos-5` — "shares Claude Fable 5's specs and pricing and joins the invitation-only Claude Mythos Preview (claude-mythos-preview) within Project Glasswing" — Fuente: models overview — Fecha: 2026-07-09
- **F16. Claude Fable 5 GA**: 2026-06-09 — "generally available on the Claude API, Claude Platform on AWS, Amazon Bedrock, Google Cloud, and Microsoft Foundry" — Fuente: models overview — Fecha: 2026-07-09
- **F17. Claude Opus 4.8** ID `claude-opus-4-8` — "for complex agentic coding and enterprise work" — Fuente: models overview — Fecha: 2026-07-09
- **F18. Claude Sonnet 5** ID `claude-sonnet-5` — "best combination of speed and intelligence" — Fuente: models overview — Fecha: 2026-07-09
- **F19. Claude Haiku 4.5** ID `claude-haiku-4-5-20251001` — "fastest model with near-frontier intelligence" — Fuente: models overview — Fecha: 2026-07-09
- **F20. Context windows**: Fable 5 / Opus 4.8 / Sonnet 5 = **1M tokens**; Haiku 4.5 = **200K tokens** — Fuente: models overview — Fecha: 2026-07-09
- **F21. Max output**: Fable 5 / Opus 4.8 / Sonnet 5 = **128K tokens**; Haiku 4.5 = **64K tokens** — Fuente: models overview — Fecha: 2026-07-09
- **F22. Knowledge cutoff (reliable)**: Fable 5 / Opus 4.8 / Sonnet 5 = Jan 2026; Haiku 4.5 = Feb 2025 — Fuente: models overview — Fecha: 2026-07-09
- **F23. Training data cutoff**: Fable 5 / Opus 4.8 / Sonnet 5 = Jan 2026; Haiku 4.5 = Jul 2025 — Fuente: models overview — Fecha: 2026-07-09
- **F24. Extended thinking**: solo Haiku 4.5 (Yes); los demás NO — Fuente: models overview — Fecha: 2026-07-09
- **F25. Adaptive thinking**: Fable 5 / Opus 4.8 / Sonnet 5 = Yes (always on); Haiku 4.5 = No — Fuente: models overview — Fecha: 2026-07-09
- **F26. Effort parameter defaults**: Opus 4.8 = high (Claude API, Claude Code, claude.ai); Sonnet 5 = high (Claude API, Claude Code) — Fuente: models overview — Fecha: 2026-07-09
- **F27. Batch API**: Opus 4.8, Opus 4.7, Opus 4.6, Sonnet 5, Sonnet 4.6 soportan hasta 300K output via beta header `output-300k-2026-03-24` — Fuente: models overview — Fecha: 2026-07-09
- **F28. AWS Bedrock IDs**: `anthropic.claude-fable-5`, `anthropic.claude-opus-4-8`, `anthropic.claude-sonnet-5`, `anthropic.claude-haiku-4-5-20251001-v1:0` — Fuente: models overview — Fecha: 2026-07-09
- **F29. Google Cloud IDs**: `claude-fable-5`, `claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5@20251001` — Fuente: models overview — Fecha: 2026-07-09

### Pricing oficial (docs.anthropic.com/en/docs/about-claude/pricing, jul 2026)

- **F30. Claude Fable 5**: input $10/MTok, output $50/MTok, 5m cache write $12.50, 1h cache write $20, cache hit $1 — Fuente: pricing page — Fecha: 2026-07-09
- **F31. Claude Mythos 5** (limited availability): input $10/MTok, output $50/MTok — Fuente: pricing page — Fecha: 2026-07-09
- **F32. Claude Opus 4.8**: input $5/MTok, output $25/MTok, 5m cache write $6.25, 1h cache write $10, cache hit $0.50 — Fuente: pricing page — Fecha: 2026-07-09
- **F33. Claude Opus 4.7**: input $5/MTok, output $25/MTok (mismo que 4.8) — Fuente: pricing page — Fecha: 2026-07-09
- **F34. Claude Opus 4.6**: input $5/MTok, output $25/MTok (mismo que 4.7/4.8) — Fuente: pricing page — Fecha: 2026-07-09
- **F35. Claude Opus 4.5**: input $5/MTok, output $25/MTok (mismo que 4.6/4.7/4.8) — Fuente: pricing page — Fecha: 2026-07-09
- **F36. Claude Opus 4.1** (deprecated): input $15/MTok, output $75/MTok — Fuente: pricing page — Fecha: 2026-07-09
- **F37. Claude Sonnet 5 (intro pricing hasta 2026-08-31)**: input $2/MTok, output $10/MTok, 5m cache write $2.50, 1h cache write $4, cache hit $0.20 — Fuente: pricing page — Fecha: 2026-07-09
- **F38. Claude Sonnet 5 (standard desde 2026-09-01)**: input $3/MTok, output $15/MTok, 5m cache write $3.75, 1h cache write $6, cache hit $0.30 — Fuente: pricing page — Fecha: 2026-07-09
- **F39. Claude Sonnet 4.6**: input $3/MTok, output $15/MTok (mismo que Sonnet 5 standard) — Fuente: pricing page — Fecha: 2026-07-09
- **F40. Claude Haiku 4.5**: input $1/MTok, output $5/MTok, 5m cache write $1.25, 1h cache write $2, cache hit $0.10 — Fuente: pricing page — Fecha: 2026-07-09
- **F41. Cache multipliers**: 5m write = 1.25× base input; 1h write = 2× base input; cache hit = 0.1× base input — Fuente: pricing page — Fecha: 2026-07-09
- **F42. Cache break-even**: "caching pays off after just one cache read for the 5-minute duration (1.25x write), or after two cache reads for the 1-hour duration (2x write)" — Fuente: pricing page — Fecha: 2026-07-09
- **F43. Data residency multiplier**: specifying US-only inference (inference_geo) on Opus 4.6+ / Sonnet 4.6+ → 1.1× multiplier — Fuente: pricing page — Fecha: 2026-07-09

### Prompt caching (docs.anthropic.com/en/docs/build-with-claude/prompt-caching)

- **F44. Prompt caching supported**: "Prompt caching (both automatic and explicit) is supported on all active Claude models" — Fuente: prompt caching page — Fecha: 2026-07-09
- **F45. Automatic caching**: "the simplest way to enable prompt caching. Instead of placing cache_control on individual content blocks, add a single cache_control field at the top level of your request body. The system automatically applies the cache breakpoint to the last cacheable block" — Fuente: prompt caching page — Fecha: 2026-07-09
- **F46. Default TTL**: 5-minute TTL via `cache_control: { type: "ephemeral" }` — Fuente: prompt caching page — Fecha: 2026-07-09
- **F47. 1-hour TTL**: `cache_control: { type: "ephemeral", ttl: "1h" }` — 2× base input price — Fuente: prompt caching page — Fecha: 2026-07-09
- **F48. Cache response fields**: `cache_creation_input_tokens` (write), `cache_read_input_tokens` (read, 90% discount), `input_tokens`, `output_tokens` — Fuente: prompt caching page (snippet oficial) — Fecha: 2026-07-09

### Computer Use (docs.anthropic.com/en/docs/agents-and-tools/computer-use)

- **F49. Computer use tool capabilities**: "screenshot capture, mouse control (click/drag/move), keyboard input, desktop automation" — Fuente: computer-use page — Fecha: 2026-07-09
- **F50. Computer use beta headers**: `computer-use-2025-11-24` para Sonnet 5, Opus 4.8, Opus 4.7, Opus 4.6, Sonnet 4.6, Opus 4.5 — Fuente: computer-use page — Fecha: 2026-07-09
- **F51. Computer use beta header legacy**: `computer-use-2025-01-24` para Sonnet 4.5, Haiku 4.5, Opus 4.1, Sonnet 4, Opus 4 — Fuente: computer-use page — Fecha: 2026-07-09
- **F52. System prompt overhead**: "computer use beta adds 466-499 tokens to the system prompt" — Fuente: computer-use page — Fecha: 2026-07-09
- **F53. Tool definition tokens**: "Claude 4.x models: 735 tokens" para la tool definition — Fuente: computer-use page — Fecha: 2026-07-09
- **F54. ZDR eligibility**: "This feature is eligible for Zero Data Retention (ZDR). When your organization has a ZDR arrangement, data sent through this feature is not stored after the API response is returned" — Fuente: computer-use page — Fecha: 2026-07-09
- **F55. Security recommendation**: "Using a dedicated virtual machine or container with minimal privileges to prevent direct system attacks or accidents" — Fuente: computer-use page — Fecha: 2026-07-09

### Estado en Aithera V0.7.3 (código real verificado)

- **F56. Archivo**: `backend/app/ai/providers/anthropic_provider.py` (104 líneas) — extiende `BaseAIProvider` (NO usa SDK anthropic) — Fuente: lectura directa — Fecha: 2026-07-09
- **F57. Default model** (línea 11, 16): `claude-sonnet-4-6` — **STALE** (Sonnet 4.6 NO existe en lineup oficial jul 2026; los reales son Sonnet 5, Opus 4.8, Fable 5, Haiku 4.5) — Fuente: lectura directa — Fecha: 2026-07-09
- **F58. URL API** (línea 13): `https://api.anthropic.com/v1/messages` — coincide con docs oficiales — Fuente: lectura directa — Fecha: 2026-07-09
- **F59. Headers** (líneas 35-39, 69-73): `x-api-key`, `anthropic-version: 2023-06-01`, `Content-Type: application/json` — Fuente: lectura directa — Fecha: 2026-07-09
- **F60. Max tokens payload** (línea 25): `max_tokens=4096` hardcoded — Fuente: lectura directa — Fecha: 2026-07-09
- **F61. HTTP client**: `httpx.AsyncClient(timeout=180.0)` directo (no SDK anthropic) — Fuente: lectura directa — Fecha: 2026-07-09
- **F62. SSE parser** (líneas 81-96): itera `data:` lines, filtra `content_block_delta` + `message_stop` — Fuente: lectura directa — Fecha: 2026-07-09
- **F63. Base class**: `BaseAIProvider` (en `app/ai/providers/base.py`) — NO usa `OpenAICompatibleProvider` (a diferencia de OpenAI/DeepSeek/OpenRouter/Grok) — Fuente: lectura directa — Fecha: 2026-07-09
- **F64. provider_name** (línea 19): `anthropic` — Fuente: lectura directa — Fecha: 2026-07-09
- **F65. health_check** (líneas 100-104): solo valida que `api_key` no esté vacío (no hace ping real) — Fuente: lectura directa — Fecha: 2026-07-09
- **F66. Encriptación API key**: cifrado con DPAPI Windows desde V0.8 (migración Alembic `d4e5f6a7b8c9_v08_encrypt_api_keys`) — Fuente: `backend/app/core/secrets.py` + CLAUDE.md §1 — Fecha: 2026-07-09

## Snippets de código extraídos (path:line)

### S1. `backend/app/ai/providers/anthropic_provider.py:1-21` (clase + init)

```python
# Anthropic AI Provider
import json
import httpx
from typing import Dict, Any, Optional, AsyncIterator
from .base import BaseAIProvider


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        super().__init__(api_key=api_key, model=model)
        self.api_url = "https://api.anthropic.com/v1/messages"

    def get_default_model(self) -> str:
        return "claude-sonnet-4-6"

    @property
    def provider_name(self) -> str:
        return "anthropic"
```

### S2. `backend/app/ai/providers/anthropic_provider.py:22-31` (_build_payload)

```python
def _build_payload(self, prompt: str, system_prompt: Optional[str], stream: bool) -> Dict[str, Any]:
    payload = {
        "model": self.model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
        "stream": stream
    }
    if system_prompt:
        payload["system"] = system_prompt
    return payload
```

### S3. `backend/app/ai/providers/anthropic_provider.py:33-65` (generate no-stream)

```python
async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """Generate response using Anthropic Claude."""
    headers = {
        "x-api-key": self.api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }

    payload = self._build_payload(prompt, system_prompt, stream=False)

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                self.api_url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            return {
                "response": data["content"][0]["text"],
                "model": self.model,
                "provider": self.provider_name,
                "tokens": data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
            }
    except Exception as e:
        return {
            "response": f"Error connecting to Anthropic: {str(e)}",
            "model": self.model,
            "provider": self.provider_name,
            "error": True
        }
```

### S4. `backend/app/ai/providers/anthropic_provider.py:67-98` (generate_stream SSE)

```python
async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncIterator[str]:
    """Generate response using Anthropic Claude, yielding incremental text chunks via SSE."""
    headers = {
        "x-api-key": self.api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }

    payload = self._build_payload(prompt, system_prompt, stream=True)

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", self.api_url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if not data_str:
                        continue
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    if data.get("type") == "content_block_delta":
                        chunk = data.get("delta", {}).get("text", "")
                        if chunk:
                            yield chunk
                    elif data.get("type") == "message_stop":
                        break
    except Exception as e:
        yield f"[Error conectando con Anthropic: {str(e)}]"
```

### S5. `backend/app/ai/providers/anthropic_provider.py:100-104` (health_check)

```python
async def health_check(self) -> bool:
    """Check if Anthropic API is accessible."""
    if not self.api_key:
        return False
    return True
```

### S6. Pseudocódigo SDK oficial (anthropic-sdk-python)

```python
# Ejemplo oficial Anthropic SDK (extraído de raw.githubusercontent.com/anthropics/anthropic-sdk-python/main/README.md)
import os
from anthropic import Anthropic

client = Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
)

message = client.messages.create(
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello, Claude"}],
    model="claude-opus-4-6",  # README example usa opus-4-6 (stale vs producción jul 2026)
)

print(message.content)
```

### S7. Pseudocódigo prompt caching (docs oficiales Anthropic)

```python
# Prompt caching automático (nuevo 2026)
from anthropic import Anthropic

client = Anthropic()

response = client.messages.create(
    model="claude-opus-4-8",
    max_tokens=1024,
    cache_control={"type": "ephemeral"},  # 5-min TTL automático
    system="You are a helpful assistant that remembers our conversation.",
    messages=[
        {"role": "user", "content": "My name is Alex. I work on machine learning."},
        {"role": "assistant", "content": "Nice to meet you, Alex!"},
        {"role": "user", "content": "What did I say I work on?"},
    ],
)

print(response.usage.model_dump_json())
# {"input_tokens": ..., "cache_creation_input_tokens": ..., "cache_read_input_tokens": ..., "output_tokens": ...}
```

## Conflictos materiales resueltos vs borrador previo

### CONFLICTO #1: Default model "claude-sonnet-4-6" — NO existe en lineup oficial jul 2026

- **Borrador previo**: `anthropic.md:5` y `anthropic_provider.py:11,16` declaran `claude-sonnet-4-6`
- **Realidad verificada (2026-07-09)**: lineup oficial Anthropic jul 2026 NO incluye `claude-sonnet-4-6`. Los reales son: `claude-fable-5`, `claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5-20251001`, más `claude-mythos-5` (preview)
- **Aplicado en doc**: doc refleja `claude-sonnet-5` como default recomendado (sweet spot coste/calidad, intro pricing $2/$10) o `claude-opus-4-8` para frontier
- **Pendiente cross-doc**: actualizar `anthropic_provider.py:11,16` default → `claude-opus-4-8` o `claude-sonnet-5`

### CONFLICTO #2: Pricing opus-4-8 — README dice ~$15/~$75, realidad es ~$5/~$25

- **Borrador previo**: `05_AI_PROVIDERS/README.md:71` (tabla Tier 1) dice Anthropic opus-4-8 ≈ $15/$75
- **Realidad verificada (2026-07-09)**: pricing page oficial Anthropic dice **$5/$25 por MTok** para Opus 4.8 (mismo que 4.7/4.6/4.5)
- **Aplicado en doc**: tabla pricing con valores verificados
- **Pendiente cross-doc**: actualizar `05_AI_PROVIDERS/README.md:71` opus-4-8 pricing $15/$75 → $5/$25

### CONFLICTO #3: Context window — Borrador dice 200K, realidad 1M para modelos frontier

- **Borrador previo**: `anthropic.md` tabla de versiones dice "Context: 200K" para todos los modelos
- **Realidad verificada (2026-07-09)**: Fable 5 / Opus 4.8 / Sonnet 5 = **1M tokens**; solo Haiku 4.5 = 200K
- **Aplicado en doc**: tabla con context real por modelo
- **Pendiente cross-doc**: actualizar `05_AI_PROVIDERS/README.md:71` "200K" → "1M" para fila Anthropic

### CONFLICTO #4: Mythos-5 declarado — README task brief lo lista como modelo production

- **Borrador previo / briefing**: claude-mythos-5 listado como modelo production de Anthropic
- **Realidad verificada (2026-07-09)**: Claude Mythos 5 es "limited availability" — invitation-only vía Project Glasswing, "offered separately for defensive cybersecurity workflows"
- **Aplicado en doc**: Mythos 5 marcado explícitamente como preview/invitation-only, no producción general

### CONFLICTO #5: claude-fable-5 — briefing dice "specialized", realidad es flagship

- **Borrador previo / briefing**: claude-fable-5 marcado como "Specialized"
- **Realidad verificada (2026-07-09)**: Claude Fable 5 = "Anthropic's most capable widely released model" — FLAGSHIP
- **Aplicado en doc**: Fable 5 como flagship (top de la familia, $10/$50)

## Fuentes Tier-1 (URL+fecha 2026-07-09)

1. https://api.github.com/repos/anthropics/anthropic-sdk-python — GitHub API live
2. https://github.com/anthropics/anthropic-sdk-python — repo oficial
3. https://raw.githubusercontent.com/anthropics/anthropic-sdk-python/main/README.md — README raw
4. https://docs.anthropic.com/en/docs/about-claude/models/overview — models overview oficial
5. https://docs.anthropic.com/en/docs/about-claude/pricing — pricing oficial
6. https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching — prompt caching docs
7. https://docs.anthropic.com/en/docs/agents-and-tools/computer-use — Computer Use docs
8. https://pypi.org/project/anthropic/ — PyPI metadata
9. https://platform.claude.com/docs/en/api/sdks/python — docs SDK Python (referenced from README)
10. backend/app/ai/providers/anthropic_provider.py — código Aithera V0.7.3 (104 líneas leído)
11. backend/app/core/secrets.py — DPAPI encryption V0.8
12. CLAUDE.md §1, §10 — guía Aithera