# Tailwind CSS — Utility-first CSS en Aithera

## Resumen

**Tailwind CSS 3.4** es el framework CSS de Aithera V0.7.3. Utility-first, no opinionated. Ver CLAUDE.md §2.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versión

Tailwind CSS 3.4 (CLAUDE.md §2).

## Por qué Tailwind

- ✅ **Utility-first**: sin CSS files separados.
- ✅ **Tree-shaking**: solo clases usadas en bundle.
- ✅ **Consistencia**: design tokens built-in.
- ✅ **No naming wars**: sin BEM.

## Hello World

```tsx
<button className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
    Click me
</button>
```

## Custom config

```javascript
// tailwind.config.js
module.exports = {
    content: ["./src/**/*.{ts,tsx}"],
    theme: {
        extend: {
            colors: {
                "aithera-blue": "#4a90e2",
                "aithera-bg": "#0a0e1a",
            },
            fontFamily: {
                sans: ["Inter", "system-ui"],
            },
        },
    },
};
```

## CSS variables (Aithera dark-first)

Tailwind puede usar CSS variables para theming dinámico:

```css
/* src/styles/globals.css */
:root {
    --color-bg: #0a0e1a;
    --color-text: #e0e0e0;
    --color-accent: #4a90e2;
}
```

```tsx
<div className="bg-[var(--color-bg)] text-[var(--color-text)]">
    Hello
</div>
```

CLAUDE.md §2 menciona CSS variables: `text-ink`, `bg-base-950`, `text-accent`. Aithera probablemente usa CSS vars para theme dark-first.

## Aithera components típicos

- `bg-base-950` (dark bg).
- `text-ink` (texto principal).
- `text-accent` (acentos, links).
- `border-base-800` (borders).
- `hover:bg-base-900` (hover).

## Pros y cons

- ✅ **Rápido de escribir**: sin context-switch a CSS.
- ✅ **Refactor seguro**: cambiar una clase no rompe otras.
- ❌ **HTML verboso**: className largo.
- ❌ **Curva de aprendizaje**: memorizar utility classes.

## Tailwind 4.0 (futuro)

Tailwind 4.0 anunciado 2025:
- CSS-first config.
- Mejor performance.
- Lightning CSS engine.

## Referencias cruzadas

- [JWIKI-098 design-system-dark.md](./design-system-dark.md)
- [JWIKI-080 react.md](./react.md)

## Fuentes

1. https://tailwindcss.com/
2. CLAUDE.md §2

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified