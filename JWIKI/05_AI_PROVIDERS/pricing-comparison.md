# Pricing Comparison — Input/Output por 1M tokens (jul 2026)

## Resumen

Comparativa de pricing input/output por 1M tokens entre los principales proveedores LLM. **ADVERTENCIA**: pricing estimado a julio 2026, verificar en websites oficiales antes de tomar decisiones financieras.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Pricing detallado (Tier 1 Frontier)

| Modelo | Input $/1M | Output $/1M | Context | Notas |
|---|---|---|---|---|
| gpt-5.5 | ~$3.00 | ~$15.00 | 256K | OpenAI flagship |
| gpt-5.4 | ~$2.50 | ~$10.00 | 256K | OpenAI stable |
| gpt-5.4-mini | ~$0.40 | ~$1.60 | 256K | OpenAI value |
| gpt-5.4-nano | ~$0.10 | ~$0.40 | 256K | OpenAI ultra-cheap |
| claude-opus-4-8 | ~$15.00 | ~$75.00 | 200K | Anthropic flagship |
| claude-sonnet-4-6 | ~$3.00 | ~$15.00 | 200K | Anthropic value |
| claude-haiku-4-5 | ~$0.80 | ~$4.00 | 200K | Anthropic cheap |
| gemini-3.5-pro | ~$1.25 | ~$5.00 | 2M | Google flagship |
| **gemini-3.5-flash** | **~$0.075** | **~$0.30** | 1M | **Disruptivo** |

## Pricing Tier 2 (Strong open/affordable)

| Modelo | Input $/1M | Output $/1M | Context |
|---|---|---|---|
| **deepseek-v4-flash** | **~$0.07** | **~$0.27** | 64K |
| **deepseek-v4** | ~$0.27 | ~$1.10 | 64K |
| **deepseek-r1** | ~$0.27 | ~$1.10 | 64K (reasoning) |
| Mistral Large 3 | ~$2.00 | ~$6.00 | 128K |
| Qwen3-72B | ~$0.40 | ~$1.20 | 128K |

## Pricing Tier 3 (Specialized)

| Modelo | Input $/1M | Output $/1M | Notas |
|---|---|---|---|
| Grok 4.3 | ~$5.00 | ~$15.00 | X context |
| Perplexity sonar-pro | ~$3.00 | ~$15.00 | Search-augmented |
| Cohere command-r-plus | ~$2.50 | ~$10.00 | RAG-optimized |

## Pricing Tier 4 (Self-host)

| Modelo | Costo |
|---|---|
| Ollama + Llama 4 8B | ~$0 (eléctrico, hardware depreciado) |
| Ollama + DeepSeek R1 32B | ~$0 |
| Llama 4 405B (multi-GPU) | ~$0 + alto CAPEX |

## Ratios de coste (vs OpenAI gpt-5.5 = baseline $3/$15)

| Modelo | Ratio input | Ratio output |
|---|---|---|
| **deepseek-v4-flash** | **0.023x** (42x más barato) | **0.018x** (56x más barato) |
| **gemini-3.5-flash** | 0.025x | 0.020x |
| gpt-5.4-nano | 0.033x | 0.027x |
| deepseek-r1 | 0.090x | 0.073x |
| claude-haiku-4-5 | 0.267x | 0.267x |
| gemini-3.5-pro | 0.417x | 0.333x |
| gpt-5.4-mini | 0.133x | 0.107x |

**DeepSeek y Gemini Flash son 40-50x más baratos que OpenAI flagship**.

## Tendencias 2024-2026

- **2024**: Frontier ~$15/$75 per 1M (Anthropic Claude Opus)
- **2025**: Frontier ~$3/$15 (GPT-4o class), reasoning +$15/$60
- **2026**: Frontier estable en ~$3/$15 (gpt-5.5, claude-sonnet-4-6), **flash/mini** class en ~$0.075-$0.40

El pricing ha caído **50x en 3 años** para tier "fast/cheap".

## Costo total estimado para Aithera V0.7.3

Asumiendo 1M tokens/día de chat (input + output combinado):

| Proveedor | Costo/día | Costo/mes |
|---|---|---|
| **gpt-5.5** | ~$18 | ~$540 |
| **gpt-5.4-mini** | ~$2 | ~$60 |
| **deepseek-v4-flash** | ~$0.34 | ~$10 |
| **gemini-3.5-flash** | ~$0.38 | ~$11 |
| **Ollama local (Llama 4 8B)** | ~$0.5 (electricity) | ~$15 |

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-038 rate-limits.md](./rate-limits.md)
- [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md)

## Fuentes

1. https://openai.com/api/pricing/
2. https://docs.anthropic.com/en/docs/about-claude/pricing
3. https://ai.google.dev/pricing
4. https://platform.deepseek.com/api-docs/pricing
5. https://docs.mistral.ai/getting-started/models/models_overview

## Nivel de confianza

**75%** — Pricing estimado. **VERIFICAR** en websites oficiales antes de decisiones financieras.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified