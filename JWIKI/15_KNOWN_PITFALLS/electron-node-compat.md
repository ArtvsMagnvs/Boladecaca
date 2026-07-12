# Electron Node Compatibility

## Resumen

**Electron** usa Chromium + Node.js. Aithera V0.7.3 tiene algunas particularidades a recordar.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Pitfalls

### 1. nodeIntegration

```javascript
// ❌ INSECURE
new BrowserWindow({
    webPreferences: { nodeIntegration: true }
});

// ✅ SECURE
new BrowserWindow({
    webPreferences: {
        contextIsolation: true,
        nodeIntegration: false,
        preload: __dirname + "/preload.cjs"
    }
});
```

### 2. Path separator

```javascript
// ❌ Unix only
const path = "/home/user/file.txt";

// ✅ Cross-platform
const path = require("path").join(app.getPath("home"), "file.txt");
```

### 3. Native modules

Native modules (better-sqlite3, etc.) requieren rebuild para Electron:
```bash
npm install --save-dev @electron/rebuild
npx electron-rebuild
```

### 4. dev vs prod

```javascript
const isDev = process.env.NODE_ENV === "development";

if (isDev) {
    win.loadURL("http://localhost:5173");  // Vite dev server
} else {
    win.loadFile("dist/index.html");  // production
}
```

## Para Aithera

- ✅ V0.7.3: secure config (CLAUDE.md §2).

## Referencias cruzadas

- [JWIKI-094 desktop-electron.md](../04_FRONTEND/desktop-electron.md)
- CLAUDE.md §2

## Fuentes

1. https://www.electronjs.org/docs/latest/tutorial/security

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified