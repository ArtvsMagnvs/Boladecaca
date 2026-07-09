# Rate Limits — Por proveedor jul 2026

## Resumen

**Rate limits** = restricciones de uso (requests per minute, tokens per minute). Varían por tier (free, tier 1-5).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Matriz de rate limits (Tier 1)

| Tier | Spend | RPM | TPM | Notas |
|---|---|---|---|---|
| OpenAI Free | $0 | 3 | 40K | |
| OpenAI Tier 1 | $5+ | 60 | 500K | |
| OpenAI Tier 2 | $50+ | 500 | 2M | |
| OpenAI Tier 3 | $100+ | 5K | 10M | |
| OpenAI Tier 4 | $250+ | 10K | 20M | |
| OpenAI Tier 5 | $1K+ | Custom | Custom | |

| Tier | Spend | RPM | TPM |
|---|---|---|---|
| Anthropic Free | $0 | 5 | 25K |
| Anthropic Build 1 | $5+ | 60 | 500K |
| Anthropic Build 2 | $50+ | 500 | 1M |
| Anthropic Build 3 | $200+ | 2K | 4M |
| Anthropic Build 4 | $1K+ | 4K | 8M |

| Tier | Spend | RPM | TPM |
|---|---|---|---|
| Google Free | $0 | 15 | 1M |
| Google Tier 1 | $5+ | 360 | 4M |
| Google Tier 2 | $50+ | 1K | 10M |
| Google Tier 3 | $200+ | 2K | 30M |

## DeepSeek (más generoso)

- Default: 100 RPM, 1M TPM
- Tier 1 ($5+): 500 RPM, 5M TPM
- Tier 2 ($50+): 2K RPM, 20M TPM

**DeepSeek es ~2x más generoso que OpenAI** en rate limits.

## Ollama local

**Sin rate limits** (depende solo del hardware).

## Auto-retry y backoff

OpenAI SDK y la mayoría auto-retry en 429 con exponential backoff:
- 1 retry después 0.5s
- 2 retry después 1s
- 3 retry después 2s
- Después: error final

```python
from openai import OpenAI

client = OpenAI(
    api_key="...",
    max_retries=3,  # default
    timeout=20.0
)
```

## Para Aithera V0.85

Si Aithera quiere garantizar uptime:
1. **Multi-proveedor fallback**: si OpenAI 429, fallback a DeepSeek.
2. **Queue con backoff**: usar `tenacity` o similar.
3. **Rate limit awareness**: track uso por minuto, parar antes de 429.

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md)

## Fuentes

1. https://platform.openai.com/account/limits
2. https://docs.anthropic.com/en/api/rate-limits
3. https://ai.google.dev/gemini-api/docs/rate-limits
4. https://platform.deepseek.com/api-docs/limits

## Nivel de confianza

**80%** — Cifras aproximadas, verificar en docs oficiales.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified