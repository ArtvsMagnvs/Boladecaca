# PWA Service Worker

## Resumen

**Service worker** es el JS que corre en background, habilita offline + caching + push notifications. Aithera V1.0+ PWA lo usaría.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Hello World

```javascript
// sw.js
self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open("v1").then((cache) => {
            return cache.addAll([
                "/",
                "/styles.css",
                "/app.js"
            ]);
        })
    );
});

self.addEventListener("fetch", (event) => {
    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request);
        })
    );
});
```

## Registration

```javascript
// app.js
if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js");
}
```

## Para Aithera

- ❌ V0.7.3: NO PWA.
- ⏳ V1.0+: PWA con service worker.

## Fuentes

1. https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified