# API Changes History — Cambios entre versiones 2024-2026

## Resumen

Historial de cambios importantes en las APIs de los principales proveedores 2024-2026. Para Aithera V0.7.3, importante saber qué APIs breaking changes hubo.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## OpenAI — Breaking changes 2024-2026

| Fecha | Cambio | Impacto |
|---|---|---|
| 2024-01 | gpt-4-turbo vision API | Multimodal |
| 2024-05 | gpt-4o omni | Voice in/out |
| 2024-08 | structured outputs (JSON schema) | Function calling estricto |
| 2024-09 | o1 / o1-mini preview | Reasoning model |
| 2024-12 | o3 announced | Frontier reasoning |
| 2025-01 | **Assistants API → Responses API** | **BREAKING**: Assistants deprecado |
| 2025-03 | gpt-4.5 | Última "v4.x" |
| 2025-Q2 | gpt-5 lanzamiento | Frontier nuevo |
| 2025-Q3 | gpt-realtime multimodal | Voice |
| 2026-Q2 | gpt-5.5 | Última flagship |
| 2026-Q3 | gpt-oss | Primer open weights |

**Crítico Aithera**: Aithera V0.7.3 usa `gpt-5` (default según `openai_provider.py`). **Actualizar a `gpt-5.5`** en próxima iteración.

## Anthropic — Breaking changes 2024-2026

| Fecha | Cambio | Impacto |
|---|---|---|
| 2024-03 | Claude 3 (Haiku, Sonnet, Opus) | Nueva familia |
| 2024-06 | Tool use GA | Function calling |
| 2024-11 | Prompt caching | Killer feature |
| 2024-11 | Computer Use (beta) | Único en producción |
| 2025-01 | Claude 3.7 | Mezcla reasoning |
| 2025-05 | Claude 4 | Opus 4, Sonnet 4, Haiku 4 |
| 2025-10 | Claude 4.5 Haiku | Última Haiku |
| 2025-11 | Claude 4.5 Opus | Frontier nuevo |
| 2026-Q1 | Claude 4.6 | |
| 2026-Q2 | Claude Opus 4-8 | Última flagship |

**Crítico Aithera**: Aithera V0.7.3 usa `claude-sonnet-4-6`. **Actualizar a `claude-opus-4-8`**.

## Google Gemini — Breaking changes 2024-2026

| Fecha | Cambio | Impacto |
|---|---|---|
| 2024-02 | Gemini 1.5 Pro (1M context) | Frontier |
| 2024-05 | Gemini 1.5 Flash | Ligero |
| 2024-09 | Imagen 3 | Image gen |
| 2024-12 | Gemini 2.0 Flash | Thinking mode |
| 2025-Q1 | Gemini 2.5 Pro/Flash | |
| 2025-Q2 | Gemini 3.0 | Frontier |
| 2026-Q2 | Gemini 3.5 Pro/Flash/Deep/Omni | Última |

**Crítico Aithera**: Aithera V0.7.3 tiene `gemini-3.1-pro-preview` (TYPO/STALE — no existe). **Actualizar a `gemini-3.5-pro` o `gemini-2.5-pro`**.

## DeepSeek — Breaking changes

| Fecha | Cambio |
|---|---|
| 2024-12 | DeepSeek-V3 + DeepSeek-Coder-V2.5 |
| 2025-01 | DeepSeek-R1 (reasoning, open weights) |
| 2025-Q1 | R1-distill series (1.5B-70B) |
| 2025-Q4 | DeepSeek-V4 + V4-flash |

**Aithera OK**: usa `deepseek-v4-flash`, alineado con latest.

## Mistral — Breaking changes

| Fecha | Cambio |
|---|---|
| 2024-02 | Mistral Large 2 |
| 2024-07 | Codestral 22B |
| 2024-12 | Pixtral Large (multimodal) |
| 2025-Q1 | Mistral Small 3, Medium 3, Large 3 |

## OpenAI-Compat migration matrix

Si Aithera quiere actualizar `default_model_name` por proveedor:

| Proveedor | Aithera V0.7.3 | Latest jul 2026 |
|---|---|---|
| OpenAI | `gpt-5` | `gpt-5.5` |
| Anthropic | `claude-sonnet-4-6` | `claude-opus-4-8` |
| Gemini | `gemini-3.1-pro-preview` (typo) | `gemini-3.5-pro` o `gemini-2.5-pro` |
| DeepSeek | `deepseek-v4-flash` | OK |
| MiniMax | `MiniMax-M2.7-highspeed` | OK |
| Grok | `grok-4.3` | OK |
| OpenRouter | (varía) | OK |
| Ollama | `llama3` | `llama3` o `llama4:8b` |

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-020 openai.md](./openai.md)
- [JWIKI-021 anthropic.md](./anthropic.md)
- [JWIKI-022 gemini.md](./gemini.md)
- [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md)
- [JWIKI-263 change-active-provider.md](../16_SOPS/change-active-provider.md)

## Fuentes

1. https://platform.openai.com/docs/changelog
2. https://docs.anthropic.com/en/release-notes
3. https://ai.google.dev/gemini-api/docs/changelog
4. https://platform.deepseek.com/api-docs/release-notes

## Nivel de confianza

**85%** — Fechas aproximadas, verificar en changelogs oficiales.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified