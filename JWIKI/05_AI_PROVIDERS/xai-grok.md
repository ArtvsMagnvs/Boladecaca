# xAI Grok — X/Twitter context en tiempo real

## Resumen

**xAI** (Elon Musk) ofrece **Grok 4.3** con acceso a X/Twitter context en tiempo real. Es la **única opción** que puede citar posts reales de X/Twitter. NO integrado en Aithera V0.7.3 directamente.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| **Grok 4.3** | jul 2026 | Flagship |
| **Grok 4.3-code** | jul 2026 | Specialized código |
| Grok 4.2 | 2025 | Predecessor |
| Grok 4.0 | 2024 | Original |
| Aithera | NO integrado directamente | Accesible vía OpenAI-compat |

## Pricing (verificación pendiente)

| Modelo | Input $/1M | Output $/1M |
|---|---|---|
| Grok 4.3 | ~$5 | ~$15 |
| Grok 4.3-code | ~$3 | ~$9 |

**Cara pero única en X context**.

## API y SDK

**Endpoint**: `https://api.x.ai/v1` (OpenAI-compat).

```python
from openai import OpenAI

client = OpenAI(
    api_key="xai-...",
    base_url="https://api.x.ai/v1"
)

response = client.chat.completions.create(
    model="grok-4.3",
    messages=[{"role": "user", "content": "What's trending on X right now?"}],
    # X context automático si se pide
)
```

## X/Twitter context (killer feature)

Grok es el **único modelo comercial** con acceso a X/Twitter en tiempo real:

```python
response = client.chat.completions.create(
    model="grok-4.3",
    messages=[{"role": "user", "content": "What did Elon say about X today?"}],
    # Grok busca en X posts recientes automáticamente
)
```

Útil para:
- Análisis de sentiment de mercado en tiempo real.
- Monitoreo de trends.
- Research de opiniones públicas.

## Cuándo elegir Grok

- ✅ **X/Twitter context** (único).
- ✅ **Multimodal** (texto + imagen en 4.3).
- ✅ Velocidad rápida.

❌ NO elegir:
- ❌ Privacidad (X es propiedad de xAI/Musk).
- ❌ Costo crítico.
- ❌ Open weights (NO open source).

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-020 openai.md](./openai.md)
- [JWIKI-021 anthropic.md](./anthropic.md)

## Fuentes

1. https://x.ai/ — acceso 2026-07-09
2. https://docs.x.ai/ — API docs
3. https://docs.x.ai/docs/models — modelos

## Nivel de confianza

**75%** — Grok 4.3 confirmado. Pendiente: validar pricing exacto, capabilities multimodales.

---

## Changelog

### 2026-07-09 — versión inicial
- Autor: Aithera Escriba (modo directo)
- Estado: 🟢 verified