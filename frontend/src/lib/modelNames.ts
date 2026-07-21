// lib/modelNames.ts — nombres CORTOS de (proveedor, modelo) para toda la UI
// [2026-07-21] Única fuente de abreviación: Ajustes (Inteligencia, badges),
// Sidebar y Hub muestran el mismo nombre corto para el mismo modelo. Evita
// redundancias tipo "MiniMax · MiniMax-M3-highspeed" (el modelo repetía la
// marca) y nombres de proveedor larguísimos en espacios pequeños.

export const PROVIDER_SHORT: Record<string, string> = {
  claude_code: "Claude CLI",
  minimax: "MiniMax",
  openai: "OpenAI",
  anthropic: "Anthropic",
  gemini: "Gemini",
  deepseek: "DeepSeek",
  openrouter: "OpenRouter",
  grok: "Grok",
  kimi: "Kimi",
  glm: "GLM",
  qwen: "Qwen API",
  ollama: "Local",
};

// Alias del CLI de Claude → nombre comercial real.
export const MODEL_SHORT: Record<string, string> = {
  fable: "Fable 5",
  opus: "Opus 4.8",
  sonnet: "Sonnet 5",
  haiku: "Haiku 4.5",
};

// El modelo repite la marca del proveedor ("MiniMax-M3-highspeed" bajo
// MiniMax): se recorta el prefijo redundante — el proveedor ya se muestra.
const MODEL_PREFIX_STRIP: Record<string, RegExp> = {
  minimax: /^MiniMax-/i,
  deepseek: /^deepseek-/i,
  gemini: /^gemini-/i,
  grok: /^grok-/i,
  glm: /^glm-/i,
  kimi: /^kimi-/i,
  anthropic: /^claude-/i,
};

/** "provider:model" → "Claude CLI · Opus 4.8" / "MiniMax · M3-highspeed" /
 *  "Local · qwen3:8b". Tolera keys sin ":" (solo proveedor). */
export function shortRef(key: string): string {
  const idx = key.indexOf(":");
  const prov = idx >= 0 ? key.slice(0, idx) : key;
  let model = idx >= 0 ? key.slice(idx + 1) : "";
  const p = PROVIDER_SHORT[prov] ?? prov;
  if (model) {
    const strip = MODEL_PREFIX_STRIP[prov];
    if (strip) model = model.replace(strip, "");
    model = MODEL_SHORT[model] ?? model;
  }
  return model ? `${p} · ${model}` : p;
}
