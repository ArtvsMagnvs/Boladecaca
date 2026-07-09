# Electron 29 — Desktop wrapper en Aithera

## Resumen

**Electron 29** es el desktop wrapper de Aithera V0.7.3. Chromium + Node.js en un bundle. Ver CLAUDE.md §2.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versión

Electron 29.x (CLAUDE.md §2).

## Por qué Electron

- ✅ **Mismo stack que web**: Chromium + Node.js.
- ✅ **Multi-plataforma**: Windows, macOS, Linux.
- ✅ **Acceso a OS APIs**: filesystem, notifications, etc.
- ✅ **Mature ecosystem**.

## Aithera V0.7.3

- `frontend/electron/main.cjs` — proceso principal.
- `frontend/electron/preload.cjs` — preload script (bridge seguro).
- Build con electron-builder (NSIS installer para Windows).

## Hello World

```javascript
// electron/main.cjs
const { app, BrowserWindow } = require("electron");

function createWindow() {
    const win = new BrowserWindow({
        width: 1280,
        height: 800,
        webPreferences: {
            preload: __dirname + "/preload.cjs",
            contextIsolation: true,
            nodeIntegration: false
        }
    });
    
    if (process.env.NODE_ENV === "development") {
        win.loadURL("http://localhost:5173");
    } else {
        win.loadFile("dist/index.html");
    }
}

app.whenReady().then(createWindow);
```

```javascript
// electron/preload.cjs
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electron", {
    send: (channel, data) => ipcRenderer.send(channel, data),
    receive: (channel, callback) => ipcRenderer.on(channel, callback)
});
```

## Electron vs Tauri

| Aspecto | Electron 29 | Tauri 2 |
|---|---|---|
| Tamaño binario | 80-200MB | 5-20MB |
| Runtime | Chromium + Node.js | WebView nativo + Rust |
| Performance | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Madurez | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

## Pitfalls

- ❌ **`nodeIntegration: true`** en webPreferences — security risk.
- ❌ **`contextIsolation: false`** — risk.
- ❌ **Cargar URLs remotas sin validar** — protocolo custom.

## Para Aithera

- ✅ V0.7.3: app Electron funcional.
- ✅ `iniciar_frontend_react.bat` para dev mode.
- ✅ Build con `electron-builder` (NSIS Windows).

## Referencias cruzadas

- [JWIKI-204 electron-tauri.md](../13_DEPLOYMENT/electron-tauri.md)
- [JWIKI-095 desktop-tauri.md](./desktop-tauri.md)
- [JWIKI-079 README.md](./README.md)

## Fuentes

1. https://www.electronjs.org/
2. CLAUDE.md §2

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified