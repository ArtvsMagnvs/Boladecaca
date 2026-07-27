// store/useI18n.ts — Framework de internacionalización (I18N-1, doc 30 §2)
//
// Store minimalista (mismo patrón que useThemeStore) — CERO dependencia nueva,
// control total, suficiente para 4 idiomas. Las traducciones viven en
// `i18n/locales/{es,en,fr,pt}.json` (clave → texto). El idioma activo persiste
// en localStorage (arranque instantáneo, sin parpadeo) y se sincroniza con el
// backend (`Config.app_language`) para que /voice/defaults elija la voz acorde.
//
// Migración INCREMENTAL (doc 30 §2): cada pantalla se pasa a `t(...)` cuando se
// toca (I18N-2/3). Las claves que aún no existen en un idioma caen a español
// (base) y, si tampoco están, devuelven la propia clave — nunca se rompe la UI.
import { create } from "zustand";
import es from "@/i18n/locales/es.json";
import en from "@/i18n/locales/en.json";
import fr from "@/i18n/locales/fr.json";
import pt from "@/i18n/locales/pt.json";
import { api } from "@/lib/api";

export type Lang = "es" | "en" | "fr" | "pt";

export const LANGUAGES: { code: Lang; name: string; flag: string }[] = [
  { code: "es", name: "Español", flag: "🇪🇸" },
  { code: "en", name: "English", flag: "🇬🇧" },
  { code: "fr", name: "Français", flag: "🇫🇷" },
  { code: "pt", name: "Português", flag: "🇵🇹" },
];

// [I18N-8] Locale BCP-47 para `Date.prototype.toLocaleString` — el formato de
// fecha/hora (no solo el texto de la UI) debe seguir el idioma seleccionado.
export const LOCALE_TAG: Record<Lang, string> = {
  es: "es-ES",
  en: "en-US",
  fr: "fr-FR",
  pt: "pt-PT",
};

const LANG_KEY = "aithera.lang";
const DICTS: Record<Lang, Record<string, string>> = { es, en, fr, pt };

function isLang(v: unknown): v is Lang {
  return v === "es" || v === "en" || v === "fr" || v === "pt";
}

function readStored(): Lang {
  try {
    const v = window.localStorage.getItem(LANG_KEY);
    if (isLang(v)) return v;
  } catch {
    /* localStorage no disponible */
  }
  return "es";
}

/** Traduce una clave al idioma dado. Fallback: idioma → español → la clave.
 *  Interpolación de variables con `{nombre}` (null/undefined → cadena vacía,
 *  para no propagar errores de tipos desde datos opcionales del backend).
 *  Pura (sin estado de React). */
export function translate(
  lang: Lang,
  key: string,
  vars?: Record<string, string | number | null | undefined>,
): string {
  let s = DICTS[lang]?.[key] ?? DICTS.es[key] ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(v == null ? "" : String(v));
  return s;
}

interface I18nState {
  lang: Lang;
  /** Cambia el idioma. Persiste en localStorage y (por defecto) sincroniza con
   *  el backend. `sync:false` para no re-escribir cuando el origen ya es el
   *  backend (p.ej. reconciliación de arranque o el onboarding). */
  setLang: (l: Lang, opts?: { sync?: boolean }) => void;
}

export const useI18n = create<I18nState>((set) => ({
  lang: readStored(),
  setLang: (l, opts = {}) => {
    try { window.localStorage.setItem(LANG_KEY, l); } catch { /* noop */ }
    set({ lang: l });
    if (opts.sync !== false) {
      api.setConfig("app_language", l).catch(() => { /* best-effort */ });
    }
  },
}));

/** Hook REACTIVO para componentes: devuelve un `t(clave, vars?)` ligado al
 *  idioma activo. El componente se re-renderiza al cambiar de idioma. */
export function useT() {
  const lang = useI18n((s) => s.lang);
  return (key: string, vars?: Record<string, string | number | null | undefined>) => translate(lang, key, vars);
}

// Reconciliación de arranque: si NUNCA se guardó idioma en este equipo (primer
// arranque antes del onboarding), toma el `app_language` que el backend ya
// pudiera tener (p.ej. de una instalación previa). No pisa una elección local.
(() => {
  try {
    if (window.localStorage.getItem(LANG_KEY)) return;
  } catch {
    return;
  }
  api.getConfig()
    .then((rows) => {
      const row = rows.find((r) => r.key === "app_language");
      if (row && isLang(row.value)) useI18n.getState().setLang(row.value, { sync: false });
    })
    .catch(() => { /* backend caído: se queda en el default 'es' */ });
})();
