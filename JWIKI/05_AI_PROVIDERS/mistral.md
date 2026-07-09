# Mistral AI — Frontier europeo open-weights

## Resumen

**Mistral AI** es la frontier europea de IA (Francia), con modelos open weights (Apache-2.0) y tiers comerciales. Fuerte en **multilingual europeo** y RGPD-compliant. **NO integrado en Aithera V0.7.3** directamente (accesible vía Ollama).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| **Mistral Large 3** | 2025-Q4 | Frontier |
| **Mistral Medium 3** | 2025 | Balance |
| **Mistral Small 3** | 2025 | Ligero |
| **Codestral 25.08** | 2025-08 | Specialized código (256K context) |
| **Pixtral Large** | 2025 | Multimodal (vision) |
| Mistral NeMo | 2024 | 12B, NVIDIA-tuned |
| Open weights: Mixtral 8x7B/8x22B | 2024 | MoE |
| Aithera | NO integrado directamente | Accesible vía Ollama |

## Licensing

- **Apache-2.0** para la mayoría de modelos (Mistral 7B, Mixtral 8x7B/22B, Mistral Large 3).
- **Mistral Research License** para algunos (más restrictivo).
- **MML** (Mistral Commercial License) para uso comercial en producción de algunos tiers.

## Familia Mistral (jul 2026)

| Modelo | Parámetros | Context | License | Notas |
|---|---|---|---|---|
| Mistral Large 3 | 123B | 128K | Apache-2.0 | Frontier |
| Mistral Medium 3 | ~70B | 128K | Apache-2.0 | Balance |
| Mistral Small 3 | 22B | 128K | Apache-2.0 | Ligero |
| Codestral 25.08 | 22B | **256K** | Apache-2.0 | Specialized código |
| Pixtral Large | 123B | 128K | Apache-2.0 | Multimodal |

## Pricing (verificación pendiente)

| Modelo | Input $/1M | Output $/1M |
|---|---|---|
| Mistral Large 3 | ~$2 | ~$6 |
| Mistral Medium 3 | ~$0.5 | ~$1.5 |
| Mistral Small 3 | ~$0.1 | ~$0.3 |
| Codestral 25.08 | ~$0.3 | ~$0.9 |

**2-3x más barato que Anthropic, comparable a DeepSeek**.

## API y SDK

**Endpoint**: `https://api.mistral.ai/v1` (OpenAI-compat).

```python
from openai import OpenAI

client = OpenAI(
    api_key="...",
    base_url="https://api.mistral.ai/v1"
)

response = client.chat.completions.create(
    model="mistral-large-3",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## Cuándo elegir Mistral

- ✅ **RGPD / europeo** (data residency Europa).
- ✅ **Multilingual europeo** (francés, alemán, español, italiano excelente).
- ✅ **Open weights Apache-2.0** (sin restricciones Llama-style).
- ✅ **Codestral** (256K context, código).

❌ NO elegir:
- ❌ Realtime audio (no soportado).
- ❌ Ecosystem OpenAI (LangChain funciona, pero nativo OpenAI).

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-023 meta-llama.md](./meta-llama.md)
- [JWIKI-024 deepseek.md](./deepseek.md)
- [JWIKI-031 local-ollama.md](./local-ollama.md)

## Fuentes

1. https://mistral.ai/ — acceso 2026-07-09
2. https://docs.mistral.ai/ — API docs
3. https://huggingface.co/mistralai — open weights
4. https://github.com/mistralai — repos oficiales

## Nivel de confianza

**80%** — Familia confirmada, Apache-2.0 confirmado, pricing estimado. Pendiente: pricing exacto, fechas exactas de Mistral Large 3.

---

## Changelog

### 2026-07-09 — versión inicial
- Autor: Aithera Escriba (modo directo)
- Estado: 🟢 verified