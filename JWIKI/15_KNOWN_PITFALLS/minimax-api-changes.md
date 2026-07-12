# MiniMax API Changes — Stale defaults

## Resumen

**MiniMax** (claude.md CLAUDE.md §2 dice "MiniMax M2.7") ha cambiado su API. Aithera V0.7.3 tiene defaults stale que necesitan refresh.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Stale defaults Aithera V0.7.3

| Default | V0.7.3 value | Should be (V0.8+) |
|---|---|---|
| `minimax.default_model` | `MiniMax-M2.7-highspeed` | `MiniMax-M3` (latest) |
| `minimax.max_completion_tokens` | 2048 | 4096 |
| `openai.default_model` | `gpt-5.1` | `gpt-5.5` |
| `anthropic.default_model` | `claude-sonnet-4-6` | `claude-opus-4-8` |
| `gemini.default_model` | `gemini-3.1-pro-preview` | `gemini-3.5-pro` |

## MiniMax specifics

- **max_completion_tokens: 2048** (CLAUDE.md §10): MiniMax cap.
- Models can be deprecated; check OpenRouter for mirrors.

## Fix

- ✅ Audit each provider's `default_model_name`.
- ✅ Add **stale default detection** in CI (warn if model deprecated).
- ✅ Use **env var overrides**: `OPENAI_MODEL_NAME`, `ANTHROPIC_MODEL_NAME`.

## Para Aithera

- ❌ V0.7.3: stale defaults.
- ✅ V0.8.0: refreshed (CLAUDE.md §1).

## Referencias cruzadas

- CLAUDE.md §1, §10

## Fuentes

1. CLAUDE.md §10

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified