# SOP — Configurar PWA

## Cuándo
V1.0+: exponer Aithera como PWA web.

## Pasos

1. **Crear `public/manifest.json`**:
```json
{
    "name": "Aithera",
    "short_name": "Aithera",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#0a0e1a",
    "theme_color": "#4a90e2",
    "icons": [
        {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png"}
    ]
}
```

2. **Crear `public/sw.js`** (service worker).

3. **Update `index.html`**:
```html
<link rel="manifest" href="/manifest.json">
<script>
    if ("serviceWorker" in navigator) {
        navigator.serviceWorker.register("/sw.js");
    }
</script>
```

4. **Generar iconos** (192, 512, maskable).

5. **Testear** en Chrome DevTools > Application > Manifest.

## Referencias cruzadas

- [JWIKI-211 pwa-manifest.md](../13_DEPLOYMENT/pwa-manifest.md)

---

*Estado: 🟢 verified*