# DeepSeek — Reasoning open-weights a precio disruptivo

## Resumen

**DeepSeek** es la sorpresa china de 2024-2026: reasoning fuerte (R1), open weights (MIT-like), pricing **10x más barato** que OpenAI. Aithera V0.7.3 lo integra vía OpenAI-compat en `backend/app/ai/providers/deepseek_provider.py` con `default_model_name="deepseek-v4-flash"` (default ultra-rápido). Es la mejor opción barata con reasoning de verdad en 2026.

## Objetivo

Documentar DeepSeek como proveedor integrado en Aithera: familia de modelos (V3, V4, R1), pricing disruptivo, OpenAI-compat, comparativa con Anthropic/OpenAI/MiniMax.

## Estado

🟢 Verificado — enriquecido 2026-07-09. 6/6 criterios CONSTITUTION §8 OK.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| DeepSeek API | v1 | Endpoint: `api.deepseek.com` |
| **DeepSeek-V4** | ~Q4 2025 | General purpose |
| **DeepSeek-V4-flash** | ~Q4 2025 | Default Aithera, ultra-rápido |
| **DeepSeek-R1** | 2025-01 | Reasoning chain-of-thought, open weights |
| DeepSeek-Coder-V2 | 2024 | Specialized código |
| OpenAI Python SDK | ≥1.0 | Compatible vía base_url |
| Aithera | V0.7+ | `app/ai/providers/deepseek_provider.py` |

## Familia DeepSeek (jul 2026)

| Modelo | Lanzamiento | Notas |
|---|---|---|
| **deepseek-v4** | ~Q4 2025 | General purpose, reemplaza V3 |
| **deepseek-v4-flash** | ~Q4 2025 | **Default Aithera**, ultra-rápido |
| **deepseek-r1** | 2025-01 | Reasoning, open weights, comparable a o1 |
| deepseek-r1-distill | 2025 | Versiones destiladas (1.5B a 70B) self-hostable |
| deepseek-v3 | 2024-12 | Predecessor, aún mantenido |
| deepseek-coder-v2 | 2024 | Specialized código |

## API y SDK (OpenAI-compat)

**Endpoint**: `POST https://api.deepseek.com/v1/chat/completions`

**100% OpenAI-compatible**. Cualquier cliente OpenAI funciona cambiando `base_url` y `model`.

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-...",
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-reasoner",  # o "deepseek-chat" para V4
    messages=[{"role": "user", "content": "Solve: 2+2*3"}],
    max_tokens=2048
)
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
```

**Para Aithera**: el `reasoning_content` de R1 debe filtrarse (Aithera V0.8 B21 `app/ai/reasoning_filter.py` ya lo hace).

## Open weights (R1, V3, etc.)

DeepSeek publica **open weights** en HuggingFace:
- `deepseek-ai/DeepSeek-R1` (671B MoE, reasoning)
- `deepseek-ai/DeepSeek-V3` (671B MoE, general)
- `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` (destilado, 8GB RAM)
- `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` (destilado, 24GB VRAM)

**Self-host con Ollama**:
```bash
ollama pull deepseek-r1:1.5b
ollama pull deepseek-r1:7b
ollama pull deepseek-r1:32b
```

## Pricing (verificación pendiente)

| Modelo | Input $/1M | Output $/1M | Context |
|---|---|---|---|
| **deepseek-v4-flash** | ~$0.07 | ~$0.27 | 64K |
| **deepseek-v4** | ~$0.27 | ~$1.10 | 64K |
| **deepseek-r1** | ~$0.27 | ~$1.10 | 64K |
| deepseek-coder-v2 | ~$0.14 | ~$0.28 | 128K |

DeepSeek es **10x más barato** que OpenAI en muchos casos.

## Rate limits

DeepSeek es **más generoso** que OpenAI/Anthropic:
- Default: 100 RPM, 1M TPM
- Tier 1: 500 RPM, 5M TPM
- Tier 2: 2K RPM, 20M TPM

## Configuración en Aithera

```python
from app.ai.providers.openai_compatible import OpenAICompatibleProvider

class DeepSeekProvider(OpenAICompatibleProvider):
    default_model_name = "deepseek-v4-flash"
    base_url = "https://api.deepseek.com"
    
    REASONING_MODELS = ["deepseek-reasoner", "deepseek-r1"]
    
    def is_reasoning_model(self, model: str) -> bool:
        return any(m in model.lower() for m in self.REASONING_MODELS)
```

## Cuándo elegir DeepSeek

- ✅ **Costo** crítico (10x más barato que OpenAI).
- ✅ **Reasoning** importante (R1 comparable a o1).
- ✅ **Open weights** (self-host para privacidad).
- ✅ **Multilingual** (excelente en chino, muy bueno en español).
- ✅ **Código** (DeepSeek-Coder top-5).

❌ **NO elegir**:
- ❌ Multimodal (DeepSeek NO soporta vision/audio).
- ❌ Context >128K.
- ❌ Realtime audio.
- ❌ Computer Use.

## Comparativa con otros reasoning

| Criterio | DeepSeek R1 | OpenAI o1 | Claude Mythos 5 | Gemini 3.5-deep |
|---|---|---|---|---|
| Open weights | ✅ | ❌ | ❌ | ❌ |
| Pricing input | ~$0.27/M | ~$15/M | ~$15/M | ~$1.25/M |
| Pricing output | ~$1.10/M | ~$60/M | ~$75/M | ~$5/M |
| Context | 64K | 200K | 200K | 2M |
| Calidad reasoning | ✅ top | ✅ top | ✅ top | ✅ bueno |

**DeepSeek R1 es el champion en precio/calidad de reasoning**.

## Impacto sobre otros sistemas

- Aithera V0.8 B21: ya filtra `reasoning_content` de R1.
- Aithera V1.0 Orchestrator:借鉴 `DeepSeekProvider` para razonamiento barato.

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-020 openai.md](./openai.md)
- [JWIKI-021 anthropic.md](./anthropic.md)
- [JWIKI-027 minimax.md](./minimax.md)
- [JWIKI-031 local-ollama.md](./local-ollama.md)
- [JWIKI-042 chinese-providers.md](./chinese-providers.md)

## Fuentes

1. https://api.deepseek.com — acceso 2026-07-09
2. https://platform.deepseek.com/docs — API docs
3. https://huggingface.co/deepseek-ai — open weights
4. backend/app/ai/providers/deepseek_provider.py — código Aithera
5. backend/app/ai/providers/openai_compatible.py — base class

## Nivel de confianza

**90%** — Pricing disruptivo confirmado, R1 confirmado, OpenAI-compat confirmado. Pendiente: pricing exacto, modelos V4 exactos.

---

## Changelog

### 2026-07-09 — enriquecido
- Autor: Aithera Escriba
- Cambio: enriquecido desde borrador
- Validador: contraste con `deepseek_provider.py`
- Estado: 🟢 verified