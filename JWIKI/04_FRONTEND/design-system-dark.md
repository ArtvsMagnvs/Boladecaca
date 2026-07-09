# Design System Dark-first — Convenciones Aithera

## Resumen

Aithera V0.7.3 es **dark-first** (CLAUDE.md §2: `bg-base-950`, `text-ink`, `text-accent`). Convenciones del design system.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Color tokens (presuntos)

Basado en convenciones Tailwind + dark-first:

| Token | Uso | Hex (estimado) |
|---|---|---|
| `bg-base-950` | Background principal | `#0a0e1a` (dark) |
| `bg-base-900` | Background secundario | `#111827` |
| `bg-base-800` | Background elevated | `#1f2937` |
| `text-ink` | Texto principal | `#e0e0e0` (light gray) |
| `text-ink-muted` | Texto secundario | `#9ca3af` (gray) |
| `text-accent` | Links, CTAs | `#4a90e2` (blue) |
| `border-base-800` | Borders | `#374151` |

## Typography

- **Sans**: Inter (presunto).
- **Mono**: JetBrains Mono (presunto).
- **Tamaños**: scale Tailwind (text-sm, text-base, text-lg, text-xl, text-2xl, text-3xl).

## Spacing

- `p-2`, `p-4`, `p-6` (padding).
- `m-2`, `m-4`, `m-6` (margin).
- `gap-2`, `gap-4` (flex/grid gap).

## Radii

- `rounded` (4px), `rounded-md` (6px), `rounded-lg` (8px), `rounded-full` (pill).

## Shadows

- `shadow-sm`, `shadow`, `shadow-md`, `shadow-lg` (elevation).

## Components (presuntos)

| Componente | Estilo |
|---|---|
| Card | `bg-base-900 border border-base-800 rounded-lg p-4` |
| Button primary | `bg-accent text-white px-4 py-2 rounded` |
| Button secondary | `bg-base-800 text-ink px-4 py-2 rounded` |
| Input | `bg-base-900 border border-base-800 rounded px-3 py-2` |
| Modal | `bg-base-950 border border-base-800 rounded-lg shadow-2xl` |

## Para Aithera V0.85+

- ✅ Mantener dark-first.
- ⏳ V0.85 audit: revisar design system consistency (AUDITORIA_HUB_V073.md).
- ⏳ V0.85 "Hub Visual": polish de animaciones + colores.

## Referencias cruzadas

- [JWIKI-097 tailwind.md](./tailwind.md)
- [JWIKI-080 react.md](./react.md)

## Fuentes

1. https://tailwindcss.com/docs/customizing-colors
2. CLAUDE.md §2
3. AUDITORIA_HUB_V073.md (sección 14: identidad visual)

## Nivel de confianza

**70%** — Tokens estimados del contexto. Verificar `frontend/tailwind.config.js` real.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified (con caveats)