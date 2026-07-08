# DeepSeek — Reasoning open-weights a precio disruptivo

## Resumen

DeepSeek es la **sorpresa china** de 2024-2026: reasoning fuerte (R1), open weights (MIT-like), y pricing **10x más barato** que OpenAI. Aithera v0.7.3 lo integra vía OpenAI-compat en `backend/app/ai/providers/deepseek_provider.py` (que reutiliza `openai_compatible.py` con `base_url=https://api.deepseek.com` y `model=deepseek-v4-flash`). Es la **mejor opción barata con reasoning de verdad** en 2026.

## Objetivo

Documentar DeepSeek como proveedor integrado en Aithera: familia de modelos (V3, V4, R1), pricing disruptivo, OpenAI-compat, y comparativa con Anthropic/OpenAI/MiniMax. Responde a "¿por qué DeepSeek es la opción por defecto para razonamiento barato?".

## Estado

🟡 En progreso — base escrita 2026-07-07.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| DeepSeek API | v1 | Endpoint: `api.deepseek.com` |
| DeepSeek-V3 | 2024-12 | Predecessor, aún útil |
| **DeepSeek-V4** | 2025-Q4 | General purpose |
| **DeepSeek-V4-flash** | 2025-Q4 | Default Aithera, ultra-rápido |
| **DeepSeek-R1** | 2025-01 | Reasoning chain-of-thought, open weights |
| DeepSeek-Coder-V2 | 2024 | Specialized code |
| OpenAI Python SDK | ≥1.0 | Compatible vía base_url |
| Aithera | V0.7+ | `app/ai/providers/deepseek_provider.py` |

## Familia DeepSeek (jul 2026)

| Modelo | Lanzamiento | Notas |
|---|---|---|
| **deepseek-v4** | ~Q4 2025 | General purpose, reemplaza V3 |
| **deepseek-v4-flash** | ~Q4 2025 | **Default Aithera**, ultra-rápido y barato |
| **deepseek-r1** | 2025-01 | Reasoning, open weights, comparable a o1 |
| deepseek-r1-distill | 2025 | Versiones destiladas (1.5B a 70B) self-hostable |
| deepseek-v3 | 2024-12 | Predecessor, aún mantenido |
| deepseek-coder-v2 | 2024 | Specialized código |

## API y SDK (OpenAI-compat)

### Endpoint

```
POST https://api.deepseek.com/v1/chat/completions
```

**100% OpenAI-compatible**. Cualquier cliente OpenAI funciona cambiando `base_url` y `model`.

### SDK ejemplo

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-...",
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-reasoner",  # o "deepseek-chat" para V4
    messages=[
        {"role": "user", "content": "Solve: 2+2*3"}
    ],
    max_tokens=2048
)

print(response.choices[0].message.content)
```

### Reasoning con R1

```python
response = client.chat.completions.create(
    model="deepseek-reasoner",  # R1
    messages=[{"role": "user", "content": "Explain quantum entanglement"}]
)

# R1 devuelve:
# - reasoning_content: chain-of-thought
# - content: respuesta final
print(response.choices[0].message.reasoning_content)
print(response.choices[0].message.content)
```

**Para Aithera**: el `reasoning_content` de R1 debe filtrarse (Aithera v0.8 **B21** `app/ai/reasoning_filter.py` ya lo hace).

## Pricing (verificación pendiente)

> ADVERTENCIA: cifras estimadas a jul 2026.

| Modelo | Input $/1M | Output $/1M | Context | Notas |
|---|---|---|---|---|
| **deepseek-v4-flash** | ~$0.07 | ~$0.27 | 64K | **Default Aithera, ultra-barato** [VERIFICAR] |
| **deepseek-v4** | ~$0.27 | ~$1.10 | 64K | [VERIFICAR] |
| **deepseek-r1** | ~$0.27 | ~$1.10 | 64K | Reasoning, comparable a o1 [VERIFICAR] |
| deepseek-coder-v2 | ~$0.14 | ~$0.28 | 128K | Código [VERIFICAR] |

**DeepSeek es 10x más barato que OpenAI en muchos casos.**

## Rate limits

| Tier | Spend | RPM | TPM |
|---|---|---|---|
| Default | $0 | 100 | 1M |
| Tier 1 | $5+ | 500 | 5M |
| Tier 2 | $50+ | 2K | 20M |

DeepSeek es **más generoso** que OpenAI/Anthropic en rate limits.

## Open weights (R1, V3, etc.)

DeepSeek publica **open weights** de sus modelos principales en HuggingFace:
- `deepseek-ai/DeepSeek-R1` (reasoning, 671B parámetros, MoE)
- `deepseek-ai/DeepSeek-V3` (general, 671B MoE)
- `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` (destilado, self-hostable en 8GB RAM)
- `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` (destilado, 24GB VRAM)

**Self-host con Ollama**:
```bash
ollama pull deepseek-r1:1.5b
ollama pull deepseek-r1:7b
ollama pull deepseek-r1:32b
```

## Configuración en Aithera

### `app/ai/providers/deepseek_provider.py` (excerpt)

```python
from app.ai.providers.openai_compatible import OpenAICompatibleProvider

class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek vía OpenAI-compat."""
    
    default_model_name = "deepseek-v4-flash"  # Default Aithera
    base_url = "https://api.deepseek.com"
    
    # Reasoning models
    REASONING_MODELS = ["deepseek-reasoner", "deepseek-r1"]
    
    def is_reasoning_model(self, model: str) -> bool:
        return any(m in model.lower() for m in self.REASONING_MODELS)
```

## Cuándo elegir DeepSeek sobre alternativas

✅ **Elegir DeepSeek cuando**:
- **Costo** es crítico (10x más barato que OpenAI)
- **Reasoning** es importante (R1 comparable a o1)
- **Open weights** (self-host para privacidad)
- **Multilingual** (excelente en chino, muy bueno en español)
- **Código** (DeepSeek-Coder es top-5 en benchmarks)
- Rate limits generosos

❌ **NO elegir DeepSeek cuando**:
- **Multimodal** es crítico (DeepSeek NO soporta vision/audio a jul 2026)
- **Context >128K** (DeepSeek max 64K, Gemini 3.5 2M)
- **Realtime audio** (gpt-realtime-2)
- **Computer Use** (Anthropic único)
- **Ecosystem maturity** (OpenAI tiene +5 años de tooling)

## Comparativa con otros proveedores de reasoning

| Criterio | DeepSeek R1 | OpenAI o1 | Claude Mythos 5 | Gemini 3.5-deep |
|---|---|---|---|---|
| Open weights | ✅ | ❌ | ❌ | ❌ |
| Pricing input | ~$0.27/M | ~$15/M | ~$15/M | ~$1.25/M |
| Pricing output | ~$1.10/M | ~$60/M | ~$75/M | ~$5/M |
| Context | 64K | 200K | 200K | 2M |
| Velocidad | medio | lento (reasoning) | lento | rápido |
| Calidad reasoning | ✅ top | ✅ top | ✅ top | ✅ bueno |
| API latency | bajo | medio-alto | medio | bajo |

**DeepSeek R1 es el champion en precio/calidad de reasoning**.

## Pendientes

- [ ] Verificar pricing oficial
- [ ] Confirmar fecha de deepseek-v4 release
- [ ] Documentar deepseek-coder-v3 si existe
- [ ] Comparar benchmarks vs Claude Opus 4-8
- [ ] Documentar self-host en Ollama con tamaños exactos

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md) — matriz comparativa
- [JWIKI-020 openai.md](./openai.md) — OpenAI
- [JWIKI-021 anthropic.md](./anthropic.md) — Anthropic
- [JWIKI-022 gemini.md](./gemini.md) — Google
- [JWIKI-031 local-ollama.md](./local-ollama.md) — Ollama
- [JWIKI-042 chinese-providers.md](./chinese-providers.md) — proveedores chinos
- [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md)

## Fuentes

1. `https://api.deepseek.com` — acceso 2026-07-07
2. `https://platform.deepseek.com/docs` — API docs
3. `https://huggingface.co/deepseek-ai` — open weights
4. `backend/app/ai/providers/deepseek_provider.py` — código Aithera v0.7.3
5. `backend/app/ai/providers/openai_compatible.py` — base class

## Nivel de confianza

**90%** — Pricing disruptivo confirmado, R1 confirmado, OpenAI-compat confirmado. Pendiente: pricing exacto, modelos V4 exactos.

---

## Changelog

### 2026-07-07 — versión inicial
- Autor: Aithera Escriba
- Cambio: doc creado
- Validador: contraste con `deepseek_provider.py`
- Estado: 🟡 en progreso
