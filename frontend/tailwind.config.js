/** @type {import('tailwindcss').Config} */
// [Tema claro/oscuro 2026-07-21] Los colores se definen como variables CSS
// (src/styles/index.css) en vez de hex fijos: así el MISMO nombre de color
// (bg-base-950, text-ink…) resuelve a valores distintos según el tema activo
// (.dark / .light en <html>), sin tocar ni una clase de los componentes. El
// patrón `rgb(var(--x) / <alpha-value>)` conserva el soporte de opacidad de
// Tailwind (bg-base-900/60 sigue funcionando).
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
  plugins: [],
};
