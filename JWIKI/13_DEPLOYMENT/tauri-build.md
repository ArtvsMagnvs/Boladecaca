# Tauri Build — Alternativa

## Resumen

**Tauri 2** puede empaquetar la app Aithera como alternativa a Electron. Bundle size mucho menor. **NO usado en Aithera V0.7.3** (Electron).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Setup

```toml
# src-tauri/tauri.conf.json
{
    "bundle": {
        "active": true,
        "targets": ["nsis"],
        "icon": ["icons/icon.ico"]
    },
    "package": {
        "productName": "Aithera",
        "version": "0.7.3"
    }
}
```

## Build

```bash
cargo tauri build
# → src-tauri/target/release/bundle/nsis/Aithera Setup 0.7.3.exe
```

## Bundle size comparison

| Framework | Bundle size |
|---|---|
| Electron | ~150MB |
| Tauri 2 | ~10-15MB |

## Para Aithera

- ❌ V0.7.3: Electron.
- ⏳ V0.85+: evaluar Tauri.

## Referencias cruzadas

- [JWIKI-095 desktop-tauri.md](../04_FRONTEND/desktop-tauri.md)

## Fuentes

1. https://tauri.app/

## Nivel de confianza

**85%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified