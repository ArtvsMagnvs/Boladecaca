# PWA Manifest

## Resumen

**PWA manifest** es el JSON que describe la app web (nombre, iconos, theme). Aithera V1.0+ expondría web via PWA.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## manifest.json

```json
{
    "name": "Aithera",
    "short_name": "Aithera",
    "description": "Personal AI assistant",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#0a0e1a",
    "theme_color": "#4a90e2",
    "icons": [
        {
            "src": "/icons/icon-192.png",
            "sizes": "192x192",
            "type": "image/png"
        },
        {
            "src": "/icons/icon-512.png",
            "sizes": "512x512",
            "type": "image/png"
        }
    ]
}
```

## Index.html link

```html
<link rel="manifest" href="/manifest.json">
```

## Para Aithera

- ❌ V0.7.3: NO PWA (Electron).
- ⏳ V1.0+: PWA para web.

## Fuentes

1. https://web.dev/add-manifest/

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified