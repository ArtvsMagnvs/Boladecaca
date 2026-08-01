/** @type {import('tailwindcss').Config} */
// [Tema claro/oscuro 2026-07-21] Los colores se definen como variables CSS
// (src/styles/index.css) en vez de hex fijos: así el MISMO nombre de color
// (bg-base-950, text-ink…) resuelve a valores distintos según el tema activo
// (.dark / .light en <html>), sin tocar ni una clase de los componentes. El
// patrón `rgb(var(--x) / <alpha-value>)` conserva el soporte de opacidad de
// Tailwind (bg-base-900/60 sigue funcionando).
import plugin from "tailwindcss/plugin.js";

const v = (name) => `rgb(var(${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        base: {
          950: v("--c-base-950"),
          900: v("--c-base-900"),
          800: v("--c-base-800"),
          700: v("--c-base-700"),
          600: v("--c-base-600"),
        },
        accent: {
          DEFAULT: v("--c-accent"),
          soft: v("--c-accent-soft"),
          glow: v("--c-accent-glow"),
        },
        ink: {
          DEFAULT: v("--c-ink"),
          dim: v("--c-ink-dim"),
          faint: v("--c-ink-faint"),
        },
        signal: {
          ok: v("--c-signal-ok"),
          warn: v("--c-signal-warn"),
          error: v("--c-signal-error"),
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glass: "0 8px 32px rgba(0,0,0,0.35)",
      },
      backdropBlur: {
        glass: "20px",
      },
    },
  },
  // [PU7, 2026-08-02] Variante `light:` (equivalente a `dark:` pero para el
  // tema claro): las paletas fijas de Tailwind (amber-300, rose-400…) NO
  // pasan por las variables CSS de tema — están calibradas para fondo
  // OSCURO, así que sobre el lienzo gris claro (`--c-base-950` en `.light`)
  // quedan poco legibles ("letras amarillas que no contrastan", reportado
  // por el usuario). En vez de sustituir esas clases (perdiendo el color de
  // acento por tipo/estado en oscuro, que funciona bien), se añade una
  // variante que solo actúa bajo `.light`: `light:text-amber-800` deja el
  // oscuro intacto y oscurece el tono SOLO en claro. La especificidad de
  // `.light &` (2 clases) siempre gana sobre la utilidad sin prefijo (1
  // clase), así que el orden de las clases en el JSX no importa.
  plugins: [
    plugin(({ addVariant }) => {
      addVariant("light", ".light &");
    }),
  ],
};
