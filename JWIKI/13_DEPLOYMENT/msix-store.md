# Microsoft Store — MSIX

## Resumen

**MSIX** es el formato de package para Microsoft Store. Aithera V1.5+ lo consideraría para distribution enterprise.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## electron-builder MSIX

```json
{
    "build": {
        "win": {
            "target": "appx"
        },
        "appx": {
            "identityName": "Aithera",
            "publisher": "CN=Aithera",
            "publisherDisplayName": "Aithera Inc"
        }
    }
}
```

## Submit to Microsoft Store

1. Build MSIX.
2. Crear Microsoft Partner Center account ($19 USD one-time).
3. Submit for review (~3-7 days).
4. Microsoft certifies + publishes.

## Pros y cons

| Pro | Con |
|---|---|
| ✅ Reach enterprise users | ❌ $19 fee |
| ✅ Auto-update built-in | ❌ MS review process |
| ✅ Trust + SmartScreen clean | ❌ Limited customization |

## Para Aithera

- ❌ V0.7.3: NO Microsoft Store.
- ⏳ V1.5+: considerar.

## Fuentes

1. https://learn.microsoft.com/en-us/windows/msix/

## Nivel de confianza

**85%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified