# Auto-Update — electron-updater

## Resumen

**electron-updater** permite a la app Electron auto-actualizarse desde GitHub Releases. **NO usado en Aithera V0.7.3**. V0.85+ considera.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Setup

```javascript
const { autoUpdater } = require("electron-updater");

autoUpdater.setFeedURL({
    provider: "github",
    owner: "NousResearch",  // o tu repo
    repo: "aithera"
});

autoUpdater.checkForUpdatesAndNotify();
```

## Update flow

```
App launches → checkForUpdates()
  ↓
GitHub Releases API: latest version?
  ↓
If newer → download Update.exe
  ↓
Prompt user: "Update available, restart now?"
  ↓
Quit + install + relaunch
```

## Pros y cons

| Pro | Con |
|---|---|
| ✅ User always on latest | ❌ Requires GitHub Releases infra |
| ✅ Transparent update | ❌ Code signing required |
| ✅ Delta updates (small downloads) | ❌ Windows SmartScreen warnings |

## Para Aithera

- ❌ V0.7.3: NO auto-update (manual update).
- ⏳ V0.85+: electron-updater.

## Referencias cruzadas

- [JWIKI-204 electron-builder.md](./electron-builder.md)

## Fuentes

1. https://www.electron.build/auto-update

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified