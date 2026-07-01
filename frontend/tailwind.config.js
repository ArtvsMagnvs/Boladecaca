/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Paleta Aithera (Fase Visual) - dark-first, acentos comedidos.
        // Ver design system en src/styles/tokens.css para el detalle completo.
        base: {
          950: "#0A0A0F",
          900: "#10121A",
          800: "#171A24",
          700: "#222632",
          600: "#2E3340",
        },
        accent: {
          DEFAULT: "#5EA8FF",
          soft: "#7C9CFF",
          glow: "#8FD9FF",
        },
        ink: {
          DEFAULT: "#E8EAF0",
          dim: "#9AA1B2",
          faint: "#5C6175",
        },
        signal: {
          ok: "#5FD9A4",
          warn: "#E8B95E",
          error: "#E0716E",
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
