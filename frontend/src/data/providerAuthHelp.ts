// providerAuthHelp.ts — AUTH-2 (2026-07-23)
//
// Catálogo de ayuda por proveedor para el modal "Configurar {provider}" de
// Settings.tsx: enlace directo a la página donde el usuario crea su API key
// + una clave i18n con la instrucción breve específica de ese proveedor
// (dónde hacer clic, qué sección buscar). NINGÚN proveedor de este catálogo
// ofrece hoy un login OAuth real para su API (ver nota de investigación en
// PLAN_MAESTRO_2026/30, sesión AUTH-2) — por eso todos siguen el mismo patrón
// de "pega tu API key", solo cambia el enlace/instrucción. `ollama` (local,
// sin key) y `claude_code` (CLI con su propio flujo "Activar") no llevan
// entrada aquí a propósito: no pasan por este modal de API key.
//
// Si el usuario pide en el futuro conectar xAI/Grok por OAuth de suscripción
// (SuperGrok/X Premium+, real y documentado en accounts.x.ai — PKCE), es una
// integración nueva y aparte (mismo tipo de trabajo que hizo Google OAuth),
// no una entrada más de este catálogo.

export interface ProviderAuthHelp {
  /** URL directa a la página donde el proveedor deja crear/ver API keys. */
  url: string;
  /** Clave i18n de la instrucción breve (1-2 frases, "dónde hacer clic"). */
  instructionKey: string;
}

export const PROVIDER_AUTH_HELP: Record<string, ProviderAuthHelp> = {
  openai: {
    url: "https://platform.openai.com/api-keys",
    instructionKey: "settings.ia.authHelp.openai",
  },
  anthropic: {
    url: "https://console.anthropic.com/settings/keys",
    instructionKey: "settings.ia.authHelp.anthropic",
  },
  gemini: {
    url: "https://aistudio.google.com/apikey",
    instructionKey: "settings.ia.authHelp.gemini",
  },
  minimax: {
    url: "https://platform.minimax.io",
    instructionKey: "settings.ia.authHelp.minimax",
  },
  deepseek: {
    url: "https://platform.deepseek.com/api_keys",
    instructionKey: "settings.ia.authHelp.deepseek",
  },
  openrouter: {
    url: "https://openrouter.ai/keys",
    instructionKey: "settings.ia.authHelp.openrouter",
  },
  grok: {
    url: "https://console.x.ai/team/default/api-keys",
    instructionKey: "settings.ia.authHelp.grok",
  },
};
