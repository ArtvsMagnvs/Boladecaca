# Deployment — Overview

## Resumen

Aithera V0.7.3 deployment incluye **Electron desktop app** (Windows) + **FastAPI backend** (local). Distribución: electron-builder + NSIS installer. CLAUDE.md §2.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Distribution channels

| Channel | Tool | Status |
|---|---|---|
| **Windows desktop** | electron-builder + NSIS | ✅ V0.7.3 |
| **Web (PWA)** | manifest + service worker | ⏳ V1.0+ |
| **Microsoft Store** | MSIX package | ⏳ V1.5+ |
| **Mac/Linux desktop** | electron-builder cross-compile | ⏳ V1.0+ |
| **Server (SaaS)** | Docker compose | ⏳ V1.5+ |

## Build pipeline

```bash
# 1. Build backend (PyInstaller o Docker)
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000  # dev mode

# 2. Build frontend
cd frontend
npm install
npm run build  # dist/

# 3. Package Electron
npm run electron:build  # release/*.exe via NSIS
```

## Para Aithera

- ✅ V0.7.3: Electron + NSIS.
- ⏳ V0.85+: auto-update via electron-updater.
- ⏳ V1.0+: PWA + web deploy.

## Referencias cruzadas

- [JWIKI-204 electron-builder.md](./electron-builder.md)
- [JWIKI-211 pwa-manifest.md](./pwa-manifest.md)
- CLAUDE.md §2

## Fuentes

1. https://www.electron.build/
2. https://www.electronjs.org/

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified