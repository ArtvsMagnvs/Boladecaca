# Vite 5 — Build tool en uso en Aithera

## Resumen

**Vite 5** es el build tool de Aithera V0.7.3. Rápido, ESM nativo, HMR instantáneo. Ver CLAUDE.md §2.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versión

Vite 5.x (CLAUDE.md §2).

## Por qué Vite

- ✅ **ESM nativo**: load directo de TS/ESM sin bundle en dev.
- ✅ **HMR instantáneo**: < 50ms.
- ✅ **Build con Rollup**: optimizaciones top-tier.
- ✅ **Plugins ecosystem**: Vite-React, Vite-TS, etc.

## Hello World

```typescript
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
    plugins: [react()],
    server: { port: 5173 },
    build: { target: "es2020" }
});
```

## Scripts package.json

```json
{
    "scripts": {
        "dev": "vite",
        "build": "tsc && vite build",
        "preview": "vite preview",
        "electron:dev": "vite & electron .",
        "electron:build": "vite build && electron-builder"
    }
}
```

## HMR

Vite HMR es magic:
- Editas `Chat.tsx` → re-renderiza solo Chat.
- State se preserva (si usas `useState`).
- CSS se actualiza sin full reload.

## Build output

```
dist/
├── assets/
│   ├── index-[hash].js
│   ├── index-[hash].css
│   └── ...
└── index.html
```

## Para Aithera

- ✅ V0.7.3: dev mode con HMR.
- ✅ Build con `tsc && vite build` (type check + bundle).
- ✅ Electron wrapper (`iniciar_frontend_react.bat`).

## Pitfalls

- ❌ **CommonJS imports** — Vite es ESM-only.
- ❌ **`require()`** en código — usar `import`.
- ❌ **Node APIs en frontend** — `fs`, `path` no disponibles en browser.

## Referencias cruzadas

- [JWIKI-093 build-webpack.md](./build-webpack.md)
- [JWIKI-094 desktop-electron.md](./desktop-electron.md)
- [JWIKI-079 README.md](./README.md)

## Fuentes

1. https://vitejs.dev/
2. CLAUDE.md §2

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified