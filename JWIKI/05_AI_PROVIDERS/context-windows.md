# Context Windows — Tamaños de contexto por proveedor

## Resumen

**Context window** = máximo de tokens que el modelo puede procesar en una sola request (input + output). Crítico para RAG, codebase analysis, video processing.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Matriz de context windows

| Proveedor / Modelo | Max context | Notas |
|---|---|---|
| **Llama 4 Scout** | **10M tokens** | 🥇 Mayor del mercado |
| Gemini 3.5-pro | 2M | 🥈 |
| Gemini 3.5-flash | 1M | |
| gpt-5.5 / gpt-5.4 | 256K | |
| Llama 4 Maverick | 1M | |
| Claude Opus 4-8 / Sonnet 4-6 / Haiku 4-5 | 200K | |
| Codestral 25.08 | 256K | Specialized código |
| DeepSeek V4 / R1 | 64K | Limitado |
| Mistral Large 3 / Qwen3 | 128K | |
| Pixtral Large | 128K | |
| Qwen3-Coder | 128K | |
| OpenAI Realtime | 32K (audio) | Audio context |
| Gemini 2.5-pro | 2M | |

## Casos de uso por context size

| Context | Caso de uso típico |
|---|---|
| **10M (Llama 4 Scout)** | Codebase entera, libro largo, varios videos |
| **2M (Gemini)** | Codebase media, video largo (~2h), varios PDFs |
| **1M (Gemini Flash, Maverick)** | Capítulo de libro, varios papers |
| **256K (OpenAI, Codestral)** | Paper académico, varios documentos |
| **200K (Claude)** | Paper académico, conversación larga |
| **128K (Mistral, Qwen)** | Conversación larga, doc medio |
| **64K (DeepSeek)** | Conversación media, doc pequeño |

## Aithera y context window

Aithera V0.7.3 no usa context windows grandes directamente (cada chat es independiente). Pero para V0.85 Memory, podría usar Gemini 2M context para ingesta masiva de JWIKI docs.

## Limitaciones prácticas

- **Costo**: a mayor context, mayor coste (input se cobra por token).
- **Latencia**: más tokens = más latencia en la primera respuesta.
- **Quality**: modelos pueden "perder el foco" en contextos muy largos (lost in the middle).

## Para JWIKI completa

Si quisiera meter los 267 docs JWIKI en un solo context:
- Gemini 2M: cabe ~150 docs densos.
- Llama 4 Scout 10M: cabe TODOS los docs.

## Referencias cruzadas

- [JWIKI-022 gemini.md](./gemini.md)
- [JWIKI-023 meta-llama.md](./meta-llama.md)

## Fuentes

1. https://platform.openai.com/docs/models
2. https://docs.anthropic.com/en/docs/about-claude/models/overview
3. https://ai.google.dev/gemini-api/docs/models

## Nivel de confianza

**85%** — Confirmado para los principales, verificar modelos nuevos.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified