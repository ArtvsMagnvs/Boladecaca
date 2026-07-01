# FASE 5 — V0.8: Clientes adicionales (Telegram + Web App)
## Documento de implementación para Claude Code
**Versión objetivo**: Aithera V0.8.0
**Prerrequisito**: Aithera V0.7.0 completada (Email + Calendar funcionales)
**Sesiones**: 2

---

## PRINCIPIO DE ESTA FASE

El backend no cambia. Se añaden dos clientes que usan exactamente los mismos endpoints que ya usa Electron. Los clientes son interfaces puras — no contienen lógica de negocio.

---

## SESIÓN 1: Web App (acceso desde el navegador)

**Tiempo estimado**: 2-3 horas
**Empieza con**: Aithera V0.7.0 funcionando

### Paso 1 — Build del frontend

```bash
cd frontend
npm run build
# Genera frontend/dist/
```

### Paso 2 — Servir el build desde FastAPI

Añadir en `backend/app/main.py` (después de todos los routers):

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

FRONTEND_BUILD_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'frontend', 'dist')
)

if os.path.exists(FRONTEND_BUILD_PATH):
    app.mount(
        "/app/assets",
        StaticFiles(directory=os.path.join(FRONTEND_BUILD_PATH, "assets")),
        name="assets"
    )

    @app.get("/app/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""):
        index_path = os.path.join(FRONTEND_BUILD_PATH, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"error": "Frontend no compilado. Ejecuta: cd frontend && npm run build"}

    @app.get("/app", include_in_schema=False)
    async def serve_spa_root():
        return await serve_spa("")
```

La app web queda en: `http://localhost:8000/app`

### Paso 3 — Cambiar el bind a 0.0.0.0

Para acceso desde otros dispositivos en la misma red:

```bash
# Antes:
python -m uvicorn app.main:app --reload --port 8000

# Ahora:
python -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
```

Actualizar el comando en `CLAUDE.md` sección 13.

### Paso 4 — Endpoint de información del sistema

Añadir en `backend/app/api/endpoints/config.py`:

```python
import socket

@router.get("/system/info")
def system_info():
    local_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    return {
        "local_ip": local_ip,
        "port": 8000,
        "web_url": f"http://{local_ip}:8000/app",
        "version": settings.VERSION,
    }
```

### Paso 5 — PIN de acceso

Añadir en `backend/app/api/endpoints/config.py`:

```
POST /api/auth/pin/set
    Body: { "pin": "1234" }
    Acción: sha256(pin) → config['web_pin_hash']
    Solo accesible desde 127.0.0.1 (validar request.client.host)
    Response: { "success": true }

POST /api/auth/pin/verify
    Body: { "pin": "1234" }
    Response: { "valid": bool, "token": "32_chars_hex_si_válido" }
    El token se guarda en dict en memoria con TTL de 8 horas

GET /api/auth/status
    Response: { "pin_configured": bool }
```

Un middleware en FastAPI valida el token `X-Aithera-Token` para peticiones `/api/*` que NO vienen de `127.0.0.1`.

### Paso 6 — Pantalla de PIN en el frontend

Crear `frontend/src/pages/PinLogin.tsx`:
- Se muestra solo cuando `window.location.hostname !== 'localhost'` y no hay token en `sessionStorage`
- Pantalla simple: logo + input PIN (type="password") + botón "Entrar"
- Al enviar: `POST /api/auth/pin/verify` → si válido, guardar token en `sessionStorage`, redirigir al Hub
- Si inválido: "PIN incorrecto"

Añadir en `frontend/src/App.tsx` la ruta `/login` → `PinLogin`.

### Paso 7 — PWA instalable

Crear `frontend/public/manifest.json`:
```json
{
  "name": "Aithera",
  "short_name": "Aithera",
  "start_url": "/app/",
  "display": "standalone",
  "background_color": "#0A0A0F",
  "theme_color": "#5EA8FF",
  "icons": [
    { "src": "/app/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/app/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

Crear `frontend/public/sw.js` — service worker básico que solo cachea assets estáticos (nunca rutas `/api/`).

Crear iconos `frontend/public/icons/icon-192.png` y `icon-512.png` — círculo `#5EA8FF` con letra "A" blanca sobre fondo `#0A0A0F`.

Añadir en `frontend/index.html`:
```html
<link rel="manifest" href="/app/manifest.json">
<meta name="theme-color" content="#5EA8FF">
```

Registrar SW en `frontend/src/main.tsx`:
```typescript
if ('serviceWorker' in navigator && !window.location.hostname.includes('localhost')) {
    navigator.serviceWorker.register('/app/sw.js');
}
```

### Paso 8 — Sección Web Access en Settings

`frontend/src/pages/Settings.tsx` — añadir sección "Acceso Web":
- Llamar `GET /api/system/info` al montar → mostrar URL de acceso
- "Accede desde: http://192.168.x.x:8000/app"
- Campo para configurar el PIN (solo visible cuando se accede desde localhost)

### ✅ Checkpoint Sesión 1 — verificar antes de parar

- [ ] `http://localhost:8000/app` sirve la app React correctamente en el browser
- [ ] `http://192.168.x.x:8000/app` funciona desde otro dispositivo de la misma red
- [ ] La app funciona igual en browser que en Electron (sin errores JS en consola)
- [ ] El PIN protege el acceso desde browser externo
- [ ] Settings muestra la URL de acceso con la IP detectada
- [ ] Chrome muestra el icono de instalar PWA en la barra de URL

### 🛑 Para aquí

Commit: `feat: Web App accesible en red local + PWA + PIN`. La Sesión 2 implementa el bot de Telegram.

---

## SESIÓN 2: Telegram Bot

**Tiempo estimado**: 2-3 horas
**Empieza con**: Web App funcionando, uvicorn en `--host 0.0.0.0`

### Paso 1 — Instalar dependencias

```bash
pip install python-telegram-bot==21.10 --break-system-packages
```

Añadir a `backend/requirements.txt`: `python-telegram-bot==21.10`

### Paso 2 — Crear `backend/app/telegram/bot.py`

El bot corre como asyncio task en el mismo proceso que FastAPI (modo polling — sin servidor público necesario).

```python
"""
Bot de Telegram de Aithera.
- Modo polling (sin webhook, sin IP pública)
- Solo acepta mensajes del chat_id autorizado
- Los comandos llaman directamente a los servicios internos
"""
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

class AitheraTelegramBot:
    def __init__(self, token: str, authorized_chat_id: int):
        self.token = token
        self.authorized_chat_id = authorized_chat_id
        self._app = None
        self._running = False

    def _is_authorized(self, update: Update) -> bool:
        return update.effective_chat.id == self.authorized_chat_id

    # Handlers: cmd_start, cmd_proyectos, cmd_tareas, cmd_estado, handle_message
    # Ver descripción de cada uno abajo

    async def start(self):
        """Llamado desde el lifespan de FastAPI."""
        self._app = Application.builder().token(self.token).build()
        self._app.add_handler(CommandHandler("start", self.cmd_start))
        self._app.add_handler(CommandHandler("proyectos", self.cmd_proyectos))
        self._app.add_handler(CommandHandler("tareas", self.cmd_tareas))
        self._app.add_handler(CommandHandler("estado", self.cmd_estado))
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        await self._app.bot.set_my_commands([
            BotCommand("start", "Inicio y ayuda"),
            BotCommand("proyectos", "Ver proyectos activos"),
            BotCommand("tareas", "Ver tareas pendientes"),
            BotCommand("estado", "Estado del sistema"),
        ])
        self._running = True
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(drop_pending_updates=True)

    async def stop(self):
        if self._app and self._running:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
            self._running = False
```

**Descripción de handlers**:

`cmd_start`: bienvenida + lista de comandos disponibles.

`cmd_proyectos`: query directa a PostgreSQL → proyectos activos formateados con emoji de prioridad.

`cmd_tareas`: query directa a PostgreSQL → tareas pendientes.

`cmd_estado`: llama a `ai_manager.health_check()` y `memory_manager.get_stats()` → resumen del sistema.

`handle_message`: mensajes de texto libre → `memory_manager.build_context_for_chat()` + `ai_manager.chat()` (no streaming) → responde. Trunca a 4000 chars si la respuesta es más larga.

Mensajes de chat_id no autorizado: ignorar completamente (sin respuesta).

### Paso 3 — Integrar en el lifespan de FastAPI

En `backend/app/main.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... código existente ...

    # Iniciar bot de Telegram si está configurado
    db = SessionLocal()
    try:
        from app.telegram.bot import init_telegram_bot
        token_row = db.query(Config).filter(Config.key == 'telegram_bot_token').first()
        chat_id_row = db.query(Config).filter(Config.key == 'telegram_chat_id').first()
        if token_row and token_row.value and chat_id_row and chat_id_row.value:
            bot = init_telegram_bot(token_row.value, int(chat_id_row.value))
            asyncio.create_task(bot.start())
            log_info("startup", "Bot de Telegram iniciado")
    except Exception as e:
        log_error("startup", e, "Bot de Telegram no iniciado (no es crítico)")
    finally:
        db.close()

    yield

    from app.telegram.bot import get_telegram_bot
    bot = get_telegram_bot()
    if bot:
        await bot.stop()
```

### Paso 4 — Endpoints de configuración Telegram

Añadir en `backend/app/api/endpoints/config.py`:

```
GET /api/telegram/status
    Response: { "configured": bool, "running": bool, "bot_username": str | null }

POST /api/telegram/configure
    Body: { "token": "...", "chat_id": 123456789 }
    Acción: guarda en config, inicia el bot inmediatamente
    Response: { "success": bool, "bot_username": str }

DELETE /api/telegram/configure
    Acción: para el bot, borra config
    Response: { "stopped": bool }
```

### Paso 5 — Sección Telegram en Settings

`frontend/src/pages/Settings.tsx` — añadir sección "Telegram":

**Si no configurado**:
- Instrucciones: "@BotFather → /newbot → copiar token"
- Campo: Bot Token
- Instrucciones para chat_id: "Escribe /start al bot → visita https://api.telegram.org/bot{TOKEN}/getUpdates → busca `id`"
- Campo: Chat ID
- Botón "Conectar"

**Si configurado**:
- "✓ Bot activo: @NombreDelBot"
- Botón "Desconectar"

### Bump de versión

- `backend/app/main.py`: `version="0.8.0"`
- `backend/app/core/config.py`: `VERSION = "0.8.0"`
- `frontend/package.json`: `"version": "0.8.0"`

### ✅ Checkpoint Sesión 2 — verificar antes de parar

- [ ] El usuario puede configurar el bot desde Settings
- [ ] `/start` en Telegram devuelve la bienvenida de Aithera
- [ ] `/proyectos` devuelve los proyectos activos de la BD
- [ ] `/tareas` devuelve las tareas pendientes
- [ ] Mensaje de texto libre recibe respuesta de la IA activa
- [ ] Mensajes de usuarios no autorizados son ignorados (sin respuesta)
- [ ] El bot se inicia automáticamente al arrancar el backend (si está configurado)
- [ ] `GET /api/telegram/status` reporta si el bot está activo
- [ ] `GET /` devuelve `"version": "0.8.0"`

### 🛑 Para aquí

Aithera V0.8.0 completada. Commit: `feat: V0.8.0 — Web App + Telegram Bot`.

**Siguiente fase**: `Fase_6_Automation_V08.md`

---

## ARCHIVOS CREADOS/MODIFICADOS EN ESTA FASE

**Sesión 1**: `backend/app/main.py` (StaticFiles, endpoints auth/pin, bump v0.8.0), `backend/app/api/endpoints/config.py` (system/info, auth/pin), `frontend/public/manifest.json`, `frontend/public/sw.js`, `frontend/public/icons/icon-192.png`, `frontend/public/icons/icon-512.png`, `frontend/src/pages/PinLogin.tsx`, `frontend/src/App.tsx` (ruta /login), `frontend/src/pages/Settings.tsx` (sección Web Access), `frontend/index.html`, `frontend/src/main.tsx`, `CLAUDE.md` (comando uvicorn)

**Sesión 2**: `backend/app/telegram/__init__.py`, `backend/app/telegram/bot.py`, `backend/app/api/endpoints/config.py` (Telegram endpoints), `backend/requirements.txt`, `frontend/src/pages/Settings.tsx` (sección Telegram), `frontend/package.json`
