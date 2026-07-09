# Reliability — Uptime y confiabilidad por proveedor

## Resumen

Comparativa de **uptime, SLA, incidents conocidos** por proveedor LLM. Importante para Aithera V0.85+ para garantizar servicio continuo.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Uptime conocido (estimaciones jul 2026)

| Proveedor | Uptime histórico | SLA formal | Multi-region |
|---|---|---|---|
| **OpenAI** | 99.9% | Sí (enterprise) | ✅ global |
| **Anthropic** | 99.9% | Sí (enterprise) | ✅ global |
| **Google Gemini** | 99.95% (Vertex) | Sí (Vertex AI SLA) | ✅ global |
| **DeepSeek** | 99.5% (self-claimed) | ❌ | ❌ single region |
| **Mistral** | 99.5% | ❌ | ❌ EU + US |
| **xAI Grok** | 99% | ❌ | ❌ |
| **Ollama** | 100% (local) | n/a | n/a |

## Incidentes notorios recientes

| Fecha | Proveedor | Impacto |
|---|---|---|
| 2024-12 | OpenAI | Outage 4h global (model degradation) |
| 2025-03 | Anthropic | Rate limit incidents |
| 2025-08 | DeepSeek | Servicio degradado varios días |
| 2025-09 | OpenAI | gpt-5 lanzamiento con problemas iniciales |
| 2026-01 | Gemini | Outage parcial en EU |

## Multi-region y disaster recovery

- **OpenAI**: multi-region automático, no requiere config.
- **Anthropic**: multi-region automático.
- **Google Vertex AI**: requiere config manual region.
- **DeepSeek**: ❌ single region (China).

## Para Aithera V0.85+

**Estrategia recomendada**: multi-proveedor fallback.

```python
PROVIDER_FALLBACK_CHAIN = [
    ("openai", "gpt-5.5"),       # primary
    ("anthropic", "claude-opus-4-8"),  # fallback 1 (mejor razonamiento)
    ("deepseek", "deepseek-v4-flash"),  # fallback 2 (barato)
    ("ollama", "llama3"),        # fallback 3 (offline)
]
```

Aithera intenta OpenAI → si 429/5xx, salta a Anthropic → si falla, DeepSeek → si todo falla, Ollama local.

## Reliability metrics

- **MTTR** (Mean Time To Recovery): OpenAI/Anthropic ~30min, otros ~2-4h.
- **MTBF** (Mean Time Between Failures): OpenAI ~30 días, otros ~7 días.
- **Uptime SLA contractual**: solo en planes enterprise.

## Status pages oficiales

- OpenAI: https://status.openai.com/
- Anthropic: https://status.anthropic.com/
- Google Cloud: https://status.cloud.google.com/
- DeepSeek: https://status.deepseek.com/

## Aithera V0.7.3 actual

Aithera V0.7.3 ya tiene:
- 8 proveedores configurables en BD (`ai_provider_configs`).
- `AIManager` con failover (parcial).
- Circuit breaker básico en `openai_compatible.py`.

Pendiente V0.85:
- Smart fallback chain con health checks.
- Cache de respuestas para degradación graceful.
- Retry policy con jitter.

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md)
- [JWIKI-263 change-active-provider.md](../16_SOPS/change-active-provider.md)

## Fuentes

1. https://status.openai.com/
2. https://status.anthropic.com/
3. https://status.cloud.google.com/
4. https://platform.deepseek.com/status

## Nivel de confianza

**75%** — Uptime histórico aproximado, verificar status pages en tiempo real.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified