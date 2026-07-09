# Perplexity — Search-augmented LLM

## Resumen

**Perplexity** combina un LLM con búsqueda web en tiempo real. Su API **Sonar** ofrece grounding con citations automáticas. NO integrado en Aithera V0.7.3.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| **sonar-pro** | jul 2026 | Flagship con búsqueda online |
| **sonar** | jul 2026 | Ligero, búsqueda online |
| Perplexity Pro (UI) | n/a | Producto consumer |

## Pricing (verificación pendiente)

| Modelo | Input $/1M | Output $/1M | Search queries/1K |
|---|---|---|---|
| **sonar-pro** | ~$3 | ~$15 | ~$5 |
| **sonar** | ~$1 | ~$1 | ~$3 |

## API y SDK

**Endpoint**: `https://api.perplexity.ai` (NO OpenAI-compat — formato propio).

```python
import requests

response = requests.post(
    "https://api.perplexity.ai/chat/completions",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "model": "sonar-pro",
        "messages": [{"role": "user", "content": "Latest AI news 2026"}],
    }
)

# response.json()['choices'][0]['message']['content']
# response.json()['citations']  # URLs citadas automáticamente
```

## Search-augmented (killer feature)

Perplexity es el **LLM con búsqueda web nativa**:

```python
response = requests.post(...)
# Devuelve respuesta + citations automáticas de fuentes web
# Sin necesidad de mantener un retrieval propio
```

## Cuándo elegir Perplexity

- ✅ **Búsqueda web en tiempo real** (sin retrieval propio).
- ✅ **Citations automáticas** (transparencia).
- ✅ **Investigación rápida** (research tasks).

❌ NO elegir:
- ❌ Function calling complejo.
- ❌ Self-host (no es open weights).
- ❌ Latencia ultra-baja.

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-022 gemini.md](./gemini.md) — Gemini con Search Grounding

## Fuentes

1. https://docs.perplexity.ai/ — API docs
2. https://perplexity.ai/ — producto consumer

## Nivel de confianza

**78%** — Confirmado. Pendiente: validar pricing y capabilities exactas.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified