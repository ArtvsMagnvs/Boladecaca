# NSIS Installer — Windows

## Resumen

**NSIS** (Nullsoft Scriptable Install System) es el installer Windows usado por electron-builder. Aithera V0.7.3 usa NSIS para Windows.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Features

- ✅ Instalación por-user (no admin).
- ✅ Custom install directory.
- ✅ Start menu + desktop shortcuts.
- ✅ Uninstaller.
- ✅ Auto-update support.

## Config

```json
{
  "nsis": {
    "oneClick": false,
    "allowToChangeInstallationDirectory": true,
    "createDesktopShortcut": true,
    "createStartMenuShortcut": true,
    "shortcutName": "Aithera"
  }
}
```

## Para Aithera

- ✅ V0.7.3: NSIS installer.

## Fuentes

1. https://nsis.sourceforge.io/

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified