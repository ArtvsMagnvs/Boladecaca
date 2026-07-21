# FASE 7 — V0.9: Web App / PWA
## Documento de implementación para Claude Code
**Versión objetivo**: Aithera V0.9.0
**Prerrequisito**: Aithera V0.8.0 completada
**Tiempo estimado**: 1 sesión

---

## OBJETIVO DE ESTA FASE

Aithera es accesible desde el navegador en la red local, sin instalar nada. La misma app React que usa Electron puede abrirse en un browser de otro dispositivo (tablet, segundo ordenador, teléfono en la misma WiFi). No es una app en la nube — el backend sigue corriendo en el PC principal.

---

## DECISIONES DE ARQUITECTURA

### Qué cambia y qué no cambia

**No cambia nada del código React existente**. La app ya usa HashRouter (compatible con file://) que también funciona perfectamente en un servidor web normal. No hay rutas de servidor que manejar.

**No cambia nada del backend FastAPI**. Ya tiene CORS `*` que permite peticiones desde cualquier origen.

**Lo que se añade**:
1. Servir el build de React como archivos estáticos desde FastAPI (en lugar de solo desde Electron)
2. Un `manifest.json` para que sea instalable como PWA
3. Un Service Worker básico para que funcione offline (caché de assets)
4. Un sistema de PIN para autenticación mínima (la app no debe ser pública en redes inseguras)

### Acceso local únicamente

Esta fase es para acceso en **red local** (192.168.x.x). No es para exponer Aithera a Internet. El backend escucha en `0.0.0.0:8000` (todos los interfaces de red del PC) en lugar de solo `127.0.0.1:8000`.

---

## TAREA 1 — Servir el build de React desde FastAPI

### Modificar `backend/app/main.py`:

Añadir al final del archivo, después de todos los routers:

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Ruta al build de React
FRONTEND_BUILD_PATH = os.path.join(
    os.path.dirname(__file__),
    '..', '..', '..', 'frontend', 'dist'
)

if os.path.exists(FRONTEND_BUILD_PATH):
    # Servir archivos estáticos del build (JS, CSS, assets)
    app.mount("/app", StaticFiles(directory=FRONTEND_BUILD_PATH, html=True), name="frontend")
    
    @app.get("/app/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Sirve index.html para todas las rutas de la SPA (HashRouter maneja el resto)."""
        index_path = os.path.join(FRONTEND_BUILD_PATH, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"error": "Frontend no compilado. Ejecuta: cd frontend && npm run build"}
```

**El frontend está disponible en**: `http://IP_DEL_PC:8000/app`

---

## TAREA 2 — Cambiar el bind de uvicorn a 0.0.0.0

El backend actualmente solo escucha en `127.0.0.1` (solo local). Para ser accesible en la red local, debe escuchar en `0.0.0.0`.

### Actualizar el comando de arranque en la documentación del proyecto

El comando de desarrollo pasa de:
```bash
python -m uvicorn app.main:app --reload --port 8000
```

A:
```bash
python -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
```

**Documentar esto en `CLAUDE.md` sección 13 (Pipeline de desarrollo).**

### Para acceder desde otro dispositivo

1. En el PC principal: ejecutar uvicorn con `--host 0.0.0.0`
2. Averiguar la IP del PC: `ipconfig` en Windows → buscar "IPv4 Address" (ej. `192.168.1.50`)
3. En el dispositivo de la misma WiFi: abrir `http://192.168.1.50:8000/app`

---

## TAREA 3 — PWA Manifest

### Crear `frontend/public/manifest.json`:

```json
{
  "name": "Aithera",
  "short_name": "Aithera",
  "description": "Sistema operativo personal de IA",
  "start_url": "/app/#/",
  "display": "standalone",
  "background_color": "#0A0A0F",
  "theme_color": "#5EA8FF",
  "orientation": "portrait-primary",
  "icons": [
    {
      "src": "/app/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/app/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ]
}
```

### Añadir en `frontend/index.html` (dentro de `<head>`):

```html
<link rel="manifest" href="/app/manifest.json">
<meta name="theme-color" content="#5EA8FF">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
```

### Crear iconos

Claude Code debe generar o incluir los archivos:
- `frontend/public/icons/icon-192.png` — Icono de 192x192 pixels
- `frontend/public/icons/icon-512.png` — Icono de 512x512 pixels

Si no hay iconos disponibles, crear placeholders (círculo azul `#5EA8FF` con la letra "A") usando el canvas HTML o un generador de imágenes PNG.

---

## TAREA 4 — Service Worker básico

### Crear `frontend/public/sw.js`:

```javascript
/**
 * Service Worker de Aithera — Caché offline de assets estáticos.
 * No cachea las respuestas de API (siempre quiere datos frescos).
 */
const CACHE_NAME = 'aithera-v0.9.0';
const STATIC_ASSETS = [
  '/app/',
  '/app/index.html',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // Cachear solo assets críticos; si falla alguno, continuar igual
      return cache.addAll(STATIC_ASSETS).catch(() => {});
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Nunca cachear llamadas a la API
  if (url.pathname.startsWith('/api/')) {
    return; // dejar pasar sin cache
  }
  
  // Para assets estáticos: cache-first
  event.respondWith(
    caches.match(event.request).then((cached) => {
      return cached || fetch(event.request).then((response) => {
        // Solo cachear responses OK (no errores 4xx/5xx)
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      });
    })
  );
});
```

### Registrar el Service Worker en `frontend/src/main.tsx`:

```typescript
// Al final del archivo, después del ReactDOM.createRoot(...)
if ('serviceWorker' in navigator && window.location.hostname !== 'localhost') {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/app/sw.js').catch((err) => {
      console.error('Service Worker registration failed:', err);
    });
  });
}
```

**Nota**: El SW se registra solo cuando NO estamos en localhost (para no interferir con el desarrollo Electron).

---

## TAREA 5 — Sistema de PIN (autenticación mínima)

### Objetivo

Evitar que cualquiera en la red local pueda acceder a Aithera simplemente abriendo la URL. Un PIN de 4-6 dígitos es suficiente para uso doméstico/oficina pequeña.

### Backend — Middleware de PIN

```python
# backend/app/core/pin_auth.py

import hashlib
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

# El PIN se guarda hasheado en la tabla config
# Key: 'web_pin_hash' | Value: sha256 del PIN

def verify_pin(provided_pin: str, stored_hash: str) -> bool:
    return hashlib.sha256(provided_pin.encode()).hexdigest() == stored_hash

def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()
```

**Endpoints nuevos**:

`POST /api/auth/pin/verify`
```json
Body: { "pin": "1234" }
Response: { "valid": true, "token": "session_token_aleatorio_32_chars" }
```
El token se genera aleatoriamente (`secrets.token_hex(16)`) y se guarda en memoria (dict `active_sessions`) con TTL de 8 horas.

`POST /api/auth/pin/set`
```json
Body: { "pin": "1234" }
Response: { "success": true }
```
Solo accesible desde localhost (para que solo el dueño del PC lo configure).

`GET /api/auth/status`
```json
Response: { "pin_configured": true, "web_access_enabled": true }
```

### Frontend — Pantalla de PIN

Antes de cargar el Hub, comprobar si hay un token de sesión guardado en `sessionStorage`. Si no hay, mostrar una pantalla de PIN:

```typescript
// frontend/src/pages/PinLogin.tsx
// Pantalla simple: 
// - Logo de Aithera
// - Input de PIN (tipo password)
// - Botón "Entrar"
// - Al enviar: POST /api/auth/pin/verify
//   - Si válido: guardar token en sessionStorage, redirigir a Hub
//   - Si inválido: mostrar "PIN incorrecto"
```

La pantalla de PIN NO se muestra en Electron (en Electron, `window.location.hostname` es siempre `localhost` o vacío, así que se puede saltarla). Solo aparece cuando la app se carga desde un browser externo.

### Configurar el PIN inicial

Si no hay PIN configurado (`web_pin_hash` no existe en la tabla config):
- El acceso web está **desactivado**: el endpoint `/app` devuelve una página de "Configure el PIN en Settings"
- En Settings → Web Access: campo para establecer el PIN

---

## TAREA 6 — URL de acceso en Settings

### Actualizar `frontend/src/pages/Settings.tsx`

Añadir sección "Acceso Web":
- Estado: "Activado / Desactivado"
- URL de acceso: detectar la IP local automáticamente
- Campo para cambiar el PIN
- Botón "Generar QR" (opcional, baja prioridad) — código QR con la URL para escanear con el móvil

Para detectar la IP del servidor, añadir endpoint:

`GET /api/system/network`
```json
{ "local_ip": "192.168.1.50", "port": 8000, "web_url": "http://192.168.1.50:8000/app" }
```

En Python:
```python
import socket
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()
```

---

## CRITERIOS DE ACEPTACIÓN

Esta fase está completa cuando:

1. ✅ `http://localhost:8000/app` sirve la app React correctamente en el browser
2. ✅ `http://192.168.x.x:8000/app` funciona desde otro dispositivo en la misma red
3. ✅ La app React funciona igual en browser que en Electron (sin errores JS)
4. ✅ El `manifest.json` es válido (verificable con Chrome DevTools → Application → Manifest)
5. ✅ La PWA es instalable desde Chrome (aparece el icono de "Instalar" en la barra de URL)
6. ✅ El PIN protege el acceso desde browser externo
7. ✅ Desde Electron (localhost), la pantalla de PIN no aparece
8. ✅ Settings muestra la URL de acceso local con la IP detectada automáticamente
9. ✅ El Service Worker se registra correctamente (verificable en DevTools → Application → SW)

---

## ARCHIVOS CREADOS/MODIFICADOS EN ESTA FASE

**Nuevos archivos**:
- `frontend/public/manifest.json`
- `frontend/public/sw.js`
- `frontend/public/icons/icon-192.png`
- `frontend/public/icons/icon-512.png`
- `frontend/src/pages/PinLogin.tsx`
- `backend/app/core/pin_auth.py`

**Modificados**:
- `backend/app/main.py` — StaticFiles mount, ruta /api/system/network, /api/auth/*, bump a v0.9.0
- `frontend/index.html` — Tags de manifest y meta PWA
- `frontend/src/main.tsx` — Registro del Service Worker
- `frontend/src/App.tsx` — Ruta /login para PinLogin
- `frontend/src/pages/Settings.tsx` — Sección Web Access
- `CLAUDE.md` — Actualizar comando de arranque con --host 0.0.0.0

---

*Al completar esta fase, Aithera V0.9.0 es accesible como PWA en la red local.*
*Siguiente: `Fase_8_Orchestrator_V10.md`*
