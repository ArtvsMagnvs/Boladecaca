# Material crudo JWIKI-020 — OpenAI GPT 5.x

> Material de investigación reusado del subagente previo
> (subagent-summary-0-20260709_082630_718674.txt) que agotó tool calls
> antes de persistir. Recolectado live 2026-07-09 contra GitHub API +
> raw SDK README + OpenAI models page.

## Hechos verificados con URL+fecha 2026-07-09

### SDK openai-python (GitHub API live)

- F1. **Stars**: 31.121 — Fuente: `api.github.com/repos/openai/openai-python` — Fecha: 2026-07-09
- F2. **Forks**: 4.873 — Fuente: GitHub API — Fecha: 2026-07-09
- F3. **Open issues**: 561 — Fuente: GitHub API — Fecha: 2026-07-09
- F4. **Subscribers**: 372 — Fuente: GitHub API — Fecha: 2026-07-09
- F5. **Licencia**: Apache-2.0 (NO MIT) — Fuente: `LICENSE` file raw en GitHub — Fecha: 2026-07-09
- F6. **Lenguaje**: Python 3.9+ — Fuente: `pyproject.toml` classifiers — Fecha: 2026-07-09
- F7. **Último push (pushed_at)**: 2026-06-25 — Fuente: GitHub API — Fecha: 2026-07-09
- F8. **Code generator**: Stainless desde `openai/openai-openapi` — Fuente: README — Fecha: 2026-07-09
- F9. **HTTP backend default**: httpx (aiohttp opcional vía `DefaultAioHttpClient()`) — Fuente: README — Fecha: 2026-07-09
- F10. **Auto-retry**: códigos 408/409/429/5xx, 2 reintentos por default — Fuente: README — Fecha: 2026-07-09
- F11. **Streaming**: SSE + context manager `with_streaming_response.create()` — Fuente: README — Fecha: 2026-07-09
- F12. **Workload identity**: K8s service accounts, Azure managed identity, GCP ID tokens — Fuente: README — Fecha: 2026-07-09

### Familia GPT 5.x (developers.openai.com/api/docs/models, jul 2026)

- F13. **gpt-5.5** (flagship): input $5.00/MTok, output $30.00/MTok, context 1M, max output 128K, knowledge cutoff Dec 1 2025 — Fuente: OpenAI models page — Fecha: 2026-07-09
- F14. **gpt-5.4**: input $2.50/MTok, output $15.00/MTok, context 400K, max output 128K — Fuente: OpenAI models page — Fecha: 2026-07-09
- F15. **gpt-5.4-mini**: input $0.75/MTok, output $4.50/MTok, context 400K, max output 128K, knowledge cutoff Aug 31 2025 — Fuente: OpenAI models page — Fecha: 2026-07-09
- F16. **gpt-5.4-nano**: en "View more" (detalles completos no visibles en page) — Fuente: OpenAI models page — Fecha: 2026-07-09
- F17. **gpt-5.6 sol**: preview trusted partners (acceso restringido) — Fuente: OpenAI models page — Fecha: 2026-07-09
- F18. **gpt-image-2**: modelo especializado de generación de imágenes (DALL-E 3 successor) — Fuente: OpenAI models page — Fecha: 2026-07-09
- F19. **gpt-realtime-2.1**: reasoning + tool use, audio I/O — Fuente: OpenAI models page — Fecha: 2026-07-09
- F20. **gpt-realtime-2.1-mini**: coste-eficiente — Fuente: OpenAI models page — Fecha: 2026-07-09
- F21. **gpt-realtime-2**: reasoning + tool use — Fuente: OpenAI models page — Fecha: 2026-07-09
- F22. **gpt-realtime-translate**: speech-to-speech translation — Fuente: OpenAI models page — Fecha: 2026-07-09
- F23. **gpt-realtime-1.5**: mejor audio-in/audio-out (legacy) — Fuente: OpenAI models page — Fecha: 2026-07-09
- F24. **gpt-realtime-mini**: coste-eficiente (legacy) — Fuente: OpenAI models page — Fecha: 2026-07-09
- F25. **gpt-realtime-whisper**: streaming STT — Fuente: OpenAI models page — Fecha: 2026-07-09
- F26. **gpt-4o-mini-tts**: DEPRECATED — Fuente: OpenAI models page — Fecha: 2026-07-09
- F27. **gpt-5.5 soporta tools**: Functions, Web search, File search, Computer use — Fuente: OpenAI models page — Fecha: 2026-07-09
- F28. **gpt-5.5 reasoning levels**: none/low/medium/high/xhigh — Fuente: OpenAI models page — Fecha: 2026-07-09

### Estado en Aithera V0.7.3 (código real verificado)

- F29. `backend/app/ai/providers/openai_provider.py` tiene **10 líneas** — extiende `OpenAICompatibleProvider` — Fuente: lectura directa — Fecha: 2026-07-09
- F30. `default_model_name = "gpt-5"` (línea 9) — CONFLICTO #2 vs borrador "gpt-5.1" — Fuente: lectura directa — Fecha: 2026-07-09
- F31. `api_url = "https://api.openai.com/v1/chat/completions"` (línea 8) — usa Chat Completions, NO Responses API — Fuente: lectura directa — Fecha: 2026-07-09
- F32. `provider_id = "openai"` (línea 10) — Fuente: lectura directa — Fecha: 2026-07-09
- F33. `OpenAICompatibleProvider` base en `backend/app/ai/providers/openai_compatible.py:14-158` — reutilizada por 4 providers (OpenAI, DeepSeek, OpenRouter, Grok) — Fuente: lectura directa — Fecha: 2026-07-09
- F34. SDK openai-python en requirements del backend (instalado vía `pip install openai>=1.80`) — Fuente: requirements.txt — Fecha: 2026-07-09

## Snippets de código extraídos (path:line)

### S1. `backend/app/ai/providers/openai_provider.py:1-10`

```python
# OpenAI AI Provider
from .openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI API provider (Chat Completions, OpenAI-compatible by definition)."""

    api_url = "https://api.openai.com/v1/chat/completions"
    default_model_name = "gpt-5"
    provider_id = "openai"
```

### S2. `backend/app/ai/providers/openai_compatible.py:41-47` (headers)

```python
def _headers(self) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {self.api_key}",
        "Content-Type": "application/json",
    }
    headers.update(self.extra_headers)
    return headers
```

### S3. `backend/app/ai/providers/openai_compatible.py:49-54` (build messages)

```python
def _build_messages(self, prompt: str, system_prompt: Optional[str]):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return messages
```

### S4. `backend/app/ai/providers/openai_compatible.py:56-79` (generate)

```python
async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    payload = {
        "model": self.model,
        "messages": self._build_messages(prompt, system_prompt),
        self.max_tokens_param: self.max_tokens_value,
    }
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(self.api_url, json=payload, headers=self._headers())
            response.raise_for_status()
            data = response.json()
            return {
                "response": data["choices"][0]["message"]["content"],
                "model": self.model,
                "provider": self.provider_name,
                "tokens": data.get("usage", {}).get("total_tokens", 0),
            }
    except Exception as e:
        return {
            "response": f"Error connecting to {self.provider_name}: {str(e)}",
            "model": self.model,
            "provider": self.provider_name,
            "error": True,
        }
```

### S5. `backend/app/ai/providers/openai_compatible.py:81-110` (generate_stream SSE)

```python
async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncIterator[str]:
    payload = {
        "model": self.model,
        "messages": self._build_messages(prompt, system_prompt),
        self.max_tokens_param: self.max_tokens_value,
        "stream": True,
    }
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", self.api_url, json=payload, headers=self._headers()) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]" or not data_str:
                        if data_str == "[DONE]":
                            break
                        continue
                    try:
                        data = json.loads(data_str)
                    except json.DecodeError:
                        continue
                    choices = data.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    chunk = delta.get("content")
                    if chunk:
                        yield chunk
    except Exception as e:
        yield f"[Error conectando con {self.provider_name}: {str(e)}]"
```

### S6. `backend/app/ai/providers/openai_compatible.py:114-158` (health_check)

```python
async def health_check(self) -> bool:
    """HTTP 200 estricto + revisar cuerpo por error embebido."""
    if not self.api_key:
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self.api_url,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "ping"}],
                    self.max_tokens_param: 1,
                },
                headers=self._headers(),
            )
            if response.status_code != 200:
                return False
            try:
                data = response.json()
            except Exception:
                return True
            if isinstance(data, dict):
                if data.get("error"):
                    return False
                base_resp = data.get("base_resp")
                if isinstance(base_resp, dict) and base_resp.get("status_code", 0) != 0:
                    return False
            return True
    except Exception:
        return False
```

## Conflictos resueltos

### CONFLICTO #1: License SDK
- **Borrador previo**: openai.md decía SDK license = **MIT**
- **Realidad verificada**: SDK license = **Apache-2.0**
- **Fuente resolución**: `LICENSE` file raw en `github.com/openai/openai-python/blob/main/LICENSE`
- **Impacto**: POSITIVO para Aithera — Apache-2.0 incluye patent grant
  explícito (MIT no), más protección legal al usar SDK en software
  propietario.
- **Aplicado en doc**: línea de versión SDK cambiada a Apache-2.0,
  sección "SDK openai-python — datos verificados" añadida con tabla
  de 12 campos.

### CONFLICTO #2: Default model en Aithera
- **Borrador previo**: openai.md (línea 5), CLAUDE.md §10 y
  README JWIKI-019 todos dicen default `gpt-5.1`
- **Realidad verificada**: `backend/app/ai/providers/openai_provider.py:9`
  tiene `default_model_name = "gpt-5"`
- **Resolución**: doc openai.md ahora refleja la realidad (`"gpt-5"`).
  Pendiente cross-doc: actualizar CLAUDE.md §10 y README.md JWIKI-019
  (no en este tick, son 4 docs a editar en operación posterior).
- **Recomendación**: actualizar a `"gpt-5.5"` (frontier) o
  `"gpt-5.4-mini"` (sweet spot coste/calidad) en próxima iteración.

### CONFLICTO #3: Pricing gpt-5.4 output
- **Borrador previo**: README.md `05_AI_PROVIDERS/README.md:374` dice
  gpt-5.4 output `~$10.00`
- **Realidad verificada**: OpenAI models page dice **$15.00/MTok**
- **Resolución**: doc openai.md refleja el precio real. Pendiente
  cross-doc: actualizar README.md JWIKI-019 fila 374 (no en este tick).

## Diferencias entre versiones

### SDK openai-python

| Versión | Highlight | Fecha aprox |
|---|---|---|
| 1.0 | Re-escrito desde v0.x, async first | 2024-08 |
| 1.50+ | Responses API support | 2025-02 |
| 1.80+ | gpt-5 family support | 2026-Q1 |
| Latest | httpx por default, Stainless regeneration automática | 2026-07 |

### Familia GPT

| Modelo | Lanzamiento | Notas |
|---|---|---|
| gpt-5.5 | ~Q2 2026 | Frontier flagship jul 2026 |
| gpt-5.4 | Q1 2026 | 3 variantes (5.4/mini/nano) |
| gpt-realtime-2.1 | Q2 2026 | Audio bidireccional |
| gpt-image-2 | Q2 2026 | DALL-E 3 successor |
| gpt-oss | Q3 2026 | Open weights, primer OSS de OpenAI |

## Pendientes de validación

- [x] Verificar license SDK (MIT vs Apache-2.0) — **RESUELTO** Apache-2.0
- [x] Verificar default model en código (gpt-5.1 vs gpt-5) — **RESUELTO** gpt-5
- [x] Verificar pricing gpt-5.4 output (~$10 vs $15) — **RESUELTO** $15
- [ ] Pricing exacto de gpt-5.4-nano (en "View more", no visible en page principal)
- [ ] Fecha exacta de release de gpt-5.5 (no pública en docs)
- [ ] Confirmar gpt-oss model name exacto y HF repo
- [ ] Evaluar `gpt-oss` para self-host en V1.0+
- [ ] Benchmarks SWE-bench gpt-5.5 vs Claude Opus 4.8
- [ ] Documentar Responses API en detalle (JWIKI dedicado futuro)
- [ ] Probar `parallel_tool_calls` en producción Aithera

## Fuentes Tier-1 con URL+fecha 2026-07-09

1. `https://api.github.com/repos/openai/openai-python` — stars/forks/issues/license
2. `https://github.com/openai/openai-python/blob/main/LICENSE` — verificación Apache-2.0
3. `https://github.com/openai/openai-python/blob/main/README.md` — httpx default, retry, streaming
4. `https://github.com/openai/openai-python/blob/main/pyproject.toml` — Python 3.9+ classifiers
5. `https://developers.openai.com/api/docs/models` — familia GPT 5.x + pricing
6. `https://openai.com/api/pricing/` — pricing general
7. `https://platform.openai.com/docs/guides/function-calling` — tool use spec
8. `https://platform.openai.com/docs/guides/streaming-responses` — SSE streaming
9. `https://platform.openai.com/docs/guides/realtime` — Realtime API WebSocket
10. `https://platform.openai.com/docs/api-reference/responses` — Responses API
11. `https://github.com/openai/openai-openapi` — OpenAPI spec → Stainless generator
12. `https://api.openai.com/v1/chat/completions` — endpoint Aithera
13. `backend/app/ai/providers/openai_provider.py` — código Aithera V0.7.3 (10 líneas)
14. `backend/app/ai/providers/openai_compatible.py` — base reutilizada
15. `JWIKI/00_INDEX/CONSTITUTION.md §8` — 6 criterios validación
16. JWIKI-020 subagent summary — `AppData\Local\hermes\cache\delegation\subagent-summary-0-20260709_082630_718674.txt` (research 25 hechos, 3 conflictos)

---

*Material crudo JWIKI-020 — recuperado y persistido 2026-07-09 por
orquestador JWIKI single-team tras subagente previo agotar tool calls.*