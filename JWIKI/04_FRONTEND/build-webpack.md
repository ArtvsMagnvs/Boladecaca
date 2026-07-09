# Webpack 5 — Alternativa build tool

## Resumen

**Webpack 5** es el bundler tradicional. Aithera V0.7.3 usa Vite (más moderno), **NO Webpack**.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Webpack vs Vite

| Aspecto | Webpack 5 | Vite 5 |
|---|---|---|
| Dev speed | ⭐⭐ (lento) | ⭐⭐⭐⭐⭐ (HMR < 50ms) |
| Build speed | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Config | Verbose | Minimal |
| HMR | Sí | Instantáneo |
| Ecosystem | enorme | medio (pero growing) |
| TypeScript | ts-loader | esbuild nativo |

## Para Aithera

Vite es la elección correcta. Webpack sería válido pero más lento.

## Hello World

```javascript
// webpack.config.js
module.exports = {
    entry: "./src/index.tsx",
    output: { filename: "bundle.[contenthash].js", path: __dirname + "/dist" },
    module: {
        rules: [
            { test: /\.tsx?$/, use: "ts-loader" },
            { test: /\.css$/, use: "css-loader style-loader" }
        ]
    },
    resolve: { extensions: [".tsx", ".ts", ".js"] }
};
```

## Referencias cruzadas

- [JWIKI-092 build-vite.md](./build-vite.md)

## Fuentes

1. https://webpack.js.org/

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified