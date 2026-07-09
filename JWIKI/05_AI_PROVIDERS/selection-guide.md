# Selection Guide — Cuándo elegir qué proveedor

## Resumen

Guía de selección por caso de uso. Compendio de los docs JWIKI-020..043.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Matriz por caso de uso

| Caso de uso | Mejor opción | 2da opción | Evitar |
|---|---|---|---|
| **Chat general alta calidad** | gpt-5.5 | claude-opus-4-8 / gemini-3.5-pro | mini/nano |
| **Razonamiento profundo** | deepseek-r1 / claude-opus-4-8 | gemini-3.5-deep | haiku |
| **Código (mejor absoluto)** | claude-opus-4-8 | gpt-5.5 / qwen-coder-30b | haiku |
| **Velocidad + bajo costo** | gemini-3.5-flash / deepseek-v4-flash | gpt-5.4-nano / claude-haiku-4-5 | opus |
| **Multimodal (image+audio+video)** | gemini-3.5-omni | gpt-5.5 | deepseek (no multimodal) |
| **Long context (1M+)** | llama-4-scout (10M) / gemini-3.5-pro (2M) | claude-opus-4-8 (200K) | deepseek (64K) |
| **Realtime audio** | gpt-realtime-2 (único maduro) | gemini-3.5-omni (Live) | claude (no) |
| **Computer Use** | claude-opus-4-8 (único) | — | todos |
| **Self-host privado** | ollama + llama4:8b / qwen3:32b | lm-studio | openai (no) |
| **RAG retrieval-heavy** | cohere command-r-plus | gpt-5.5 + embeddings openai | deepseek |
| **Búsqueda web en tiempo real** | perplexity sonar-pro | grok-4.3 (X context) | claude (no) |
| **PDF input nativo** | claude-opus-4-8 | gemini-3.5-pro | gpt-5 (no nativo) |
| **X/Twitter context** | grok-4.3 (único) | — | todos |
| **Multilingual europeo** | mistral-large-3 | claude-opus-4-8 | gemini (mejor en inglés) |
| **Multilingual chino** | qwen3-72b | deepseek-v4 / minimax | gpt-5 (chino medio) |
| **RGPD / Europa** | mistral / claude (Vertex EU) | ollama local | openai (US-only) |
| **Reasoning barato** | deepseek-r1 | gemini-3.5-deep | opus (caro) |

## Por presupuesto (1M tokens/día)

| Presupuesto | Recomendación |
|---|---|
| **$0** | Ollama local + Llama 4 8B |
| **< $20/mes** | DeepSeek-V4-flash o Gemini-3.5-flash |
| **< $100/mes** | gpt-5.4-mini o claude-haiku-4-5 |
| **< $1000/mes** | gpt-5.5 o claude-sonnet-4-6 |
| **Sin límite** | Opus 4-8 + gpt-5.5 |

## Por latencia

| Latencia target | Recomendación |
|---|---|
| **< 200ms** | Ollama local |
| **< 500ms** | gemini-3.5-flash, gpt-realtime-2 |
| **< 1s** | gpt-5.4-nano, claude-haiku-4-5 |
| **< 3s** | gpt-5.5, claude-sonnet-4-6 |
| **Sin límite** | Opus 4-8 + reasoning models |

## Por confiabilidad

| Requisito | Recomendación |
|---|---|
| **99.9% SLA** | OpenAI / Anthropic / Google Vertex |
| **Best-effort** | DeepSeek / Mistral / xAI |
| **100% offline** | Ollama local |

## Setup multi-proveedor recomendado para Aithera

| Rol | Proveedor | Modelo |
|---|---|---|
| **Default (chat general)** | MiniMax | MiniMax-M2.7-highspeed |
| **Coding agent** | Anthropic | claude-opus-4-8 |
| **Razonamiento barato** | DeepSeek | deepseek-r1 |
| **Multimodal (futuro)** | Google | gemini-3.5-omni |
| **Fallback offline** | Ollama | llama4:8b |

## Decisión: "¿qué proveedor uso?"

1. ¿Necesitas self-host? → Ollama + Llama 4 / Qwen 3.
2. ¿Necesitas multimodal (image/audio/video)? → Gemini 3.5.
3. ¿Necesitas Realtime audio? → OpenAI gpt-realtime-2.
4. ¿Necesitas Computer Use? → Anthropic Claude.
5. ¿Necesitas razonamiento puro barato? → DeepSeek R1.
6. ¿Necesitas el mejor código? → Anthropic Claude Opus 4-8.
7. ¿Necesitas contexto 10M tokens? → Llama 4 Scout.
8. ¿Necesitas X/Twitter context? → xAI Grok 4.3.
9. ¿Default razonado? → OpenAI gpt-5.5 o Anthropic Opus 4-8.

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-020 openai.md](./openai.md)
- [JWIKI-021 anthropic.md](./anthropic.md)
- [JWIKI-022 gemini.md](./gemini.md)
- [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md)

## Fuentes

Consolidado de todos los docs JWIKI-020..043.

## Nivel de confianza

**88%** — Síntesis bien fundamentada.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified