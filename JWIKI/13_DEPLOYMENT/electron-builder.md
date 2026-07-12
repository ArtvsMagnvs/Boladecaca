# Electron Builder — Aithera

## Resumen

**electron-builder 24** es la herramienta usada por Aithera para empaquetar la app desktop. Configuración en `frontend/package.json`. CLAUDE.md §2.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Configuración

```json
{
  "build": {
    "appId": "com.aithera.desktop",
    "productName": "Aithera",
    "directories": {
      "output": "release"
    },
    "files": [
      "dist/**/*",
      "electron/**/*",
      "package.json"
    ],
    "win": {
      "target": "nsis",
      "icon": "build/icon.ico"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true
    }
  }
}
```

## Build command

```bash
npm run electron:build
# → release/Aithera Setup 0.7.3.exe
```

## Output

- `release/Aithera Setup 0.7.3.exe` (~80-150MB NSIS installer)
- `release/win-unpacked/` (portable unpacked)

## Para Aithera

- ✅ V0.7.3: electron-builder + NSIS.

## Referencias cruzadas

- [JWIKI-094 desktop-electron.md](../04_FRONTEND/desktop-electron.md)
- CLAUDE.md §2

## Fuentes

1. https://www.electron.build/

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified