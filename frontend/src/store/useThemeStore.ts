// store/useThemeStore.ts — Tema claro/oscuro (2026-07-21)
//
// Cambia la clase `.dark`/`.light` en <html>; los colores (definidos como
// variables CSS en styles/index.css) se recalculan solos, sin tocar ningún
// componente. Persiste en localStorage. "dark" es el default (el histórico).
import { create } from "zustand";

export type Theme = "dark" | "light";
const THEME_KEY = "aithera.theme";

function readStoredTheme(): Theme {
  try {
    const v = window.localStorage.getItem(THEME_KEY);
    if (v === "dark" || v === "light") return v;
  } catch {
    /* localStorage no disponible */
  }
  return "dark";
}

/** Aplica la clase de tema al <html>. Idempotente. */
export function applyTheme(theme: Theme) {
  const root = document.documentElement;
  root.classList.remove("dark", "light");
  root.classList.add(theme);
  // `color-scheme` ayuda a los controles nativos (scrollbars, inputs) a pintar
  // acorde al tema.
  root.style.colorScheme = theme;
}

interface ThemeState {
  theme: Theme;
  setTheme: (t: Theme) => void;
  toggleTheme: () => void;
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: readStoredTheme(),
  setTheme: (t) => {
    applyTheme(t);
    try {
      window.localStorage.setItem(THEME_KEY, t);
    } catch {
      /* noop */
    }
    set({ theme: t });
  },
  toggleTheme: () => get().setTheme(get().theme === "dark" ? "light" : "dark"),
}));

// Aplica el tema guardado en cuanto se carga el módulo (antes del primer
// render), para que no haya un parpadeo de tema al arrancar.
applyTheme(readStoredTheme());
