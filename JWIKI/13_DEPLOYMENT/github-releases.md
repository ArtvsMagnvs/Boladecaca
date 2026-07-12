# GitHub Releases — Distribución

## Resumen

**GitHub Releases** es donde electron-updater descarga nuevas versiones. Aithera V0.85+ lo usaría.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Crear release

```bash
# Tag
git tag v0.8.0
git push origin v0.8.0

# Release con electron-builder
npm run electron:build
# → release/Aithera Setup 0.8.0.exe

# Subir a GitHub
gh release create v0.8.0 release/*.exe --generate-notes
```

## electron-updater feed

```json
{
    "build": {
        "publish": {
            "provider": "github",
            "owner": "NousResearch",
            "repo": "aithera"
        }
    }
}
```

## Para Aithera

- ❌ V0.7.3: NO GitHub Releases para distribution (manual).
- ⏳ V0.85+: GitHub Releases + electron-updater.

## Referencias cruzadas

- [JWIKI-206 electron-auto-update.md](./electron-auto-update.md)

## Fuentes

1. https://docs.github.com/en/repositories/releasing-projects-on-github

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified