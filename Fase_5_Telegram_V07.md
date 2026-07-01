# FASE 5 — V0.7: Interfaz Telegram
## Documento de implementación para Claude Code
**Versión objetivo**: Aithera V0.7.0
**Prerrequisito**: Aithera V0.6.0 completada
**Tiempo estimado**: 1-2 sesiones

---

## OBJETIVO DE ESTA FASE

Aithera es accesible desde Telegram. El mismo backend que usa la app Electron sirve al bot de Telegram — no hay lógica de negocio duplicada. El bot es solo una interfaz de entrada/salida.

---

## DECISIONES DE ARQUITECTURA

### Por qué python-telegram-bot y no otras opciones

`python-telegram-bot` v21 (verificado activo junio 2026, 28k+ stars, LGPL):
- Async nativo con `asyncio` — compatible con FastAPI
- La API más completa y documentada para bots de Telegram en Python
- Gratuito, sin límites de mensajes en bots privados
- No requiere servidor web externo (usa polling o webhook)

### Modo de operación: Polling

Para una app personal de escritorio, el **polling** (el bot consulta a Telegram cada X segundos si hay mensajes nuevos) es más simple que los webhooks (que requieren un servidor con IP pública y HTTPS). Polling es perfecto para uso personal local.

### Seguridad: Solo acepta mensajes del propietario

El bot debe rechazar cualquier mensaje que no venga del `chat_id` autorizado. El `chat_id` del propietario se configura en la UI de Settings.

### Integración con el backend

El bot de Telegram **no implementa lógica de negocio**. Llama directamente a las funciones internas de FastAPI (importando los servicios, no haciendo HTTP requests a sí mismo). Esto es más eficiente que hacer requests HTTP internos.

---

## TAREA 1 — Instalar dependencias

Añadir a `backend/requirements.txt`:
```
python-telegram-bot==21.10
```

---

## TAREA 2 — Telegram Bot Service

### Crear `backend/app/telegram/bot.py`:

```python
"""
Bot de Telegram de Aithera.

Arquitectura:
- Corre en un asyncio task separado dentro del mismo proceso FastAPI
- Se inicia/para via el lifespan de FastAPI
- Llama directamente a los servicios internos (ai_manager, memory_manager, etc.)
- Solo acepta mensajes del chat_id autorizado (configurado en Settings)
- En modo polling (sin servidor externo necesario)
"""
import asyncio
import logging
from typing import Optional

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from app.ai.ai_manager import ai_manager
from app.memory.memory_manager import memory_manager
from app.db.database import SessionLocal
from app.db.models import Project, Task
from app.core.logging_config import get_system_logger

logger = get_system_logger("telegram")


class AitheraTelegramBot:
    """
    Bot de Telegram de Aithera.
    Actúa como interfaz de entrada/salida — no contiene lógica de negocio.
    """
    
    def __init__(self, token: str, authorized_chat_id: int):
        self.token = token
        self.authorized_chat_id = authorized_chat_id
        self._app: Optional[Application] = None
        self._running = False
    
    def _is_authorized(self, update: Update) -> bool:
        """Verifica que el mensaje viene del propietario de Aithera."""
        return update.effective_chat.id == self.authorized_chat_id
    
    async def _unauthorized_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Responde a mensajes no autorizados."""
        logger.warning(f"Mensaje no autorizado de chat_id: {update.effective_chat.id}")
        await update.message.reply_text("❌ No autorizado.")
    
    # ─── HANDLERS DE COMANDOS ────────────────────────────────────────────────
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._unauthorized_response(update, context)
        await update.message.reply_text(
            "👋 Hola, soy Aithera.\n\n"
            "Comandos disponibles:\n"
            "/proyectos — Ver proyectos activos\n"
            "/tareas — Ver tareas pendientes\n"
            "/estado — Estado del sistema\n"
            "/email — Resumen de email (requiere Fase 4)\n"
            "\nO simplemente escríbeme y te respondo."
        )
    
    async def cmd_proyectos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._unauthorized_response(update, context)
        
        db = SessionLocal()
        try:
            projects = db.query(Project).filter(Project.status == 'active').limit(10).all()
            if not projects:
                await update.message.reply_text("No hay proyectos activos.")
                return
            
            lines = ["📁 *Proyectos activos:*\n"]
            for p in projects:
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(p.priority, "⚪")
                lines.append(f"{priority_emoji} {p.name}")
                if p.due_date:
                    lines.append(f"   📅 Fecha límite: {p.due_date.strftime('%d/%m/%Y')}")
            
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        finally:
            db.close()
    
    async def cmd_tareas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._unauthorized_response(update, context)
        
        db = SessionLocal()
        try:
            tasks = db.query(Task).filter(Task.status == 'pending').limit(10).all()
            if not tasks:
                await update.message.reply_text("No hay tareas pendientes.")
                return
            
            lines = ["✅ *Tareas pendientes:*\n"]
            for t in tasks:
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t.priority, "⚪")
                lines.append(f"{priority_emoji} {t.title}")
                if t.assignee:
                    lines.append(f"   👤 {t.assignee}")
            
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        finally:
            db.close()
    
    async def cmd_estado(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._unauthorized_response(update, context)
        
        health = await ai_manager.health_check()
        mem_stats = memory_manager.get_stats()
        
        status_text = (
            f"🤖 *Estado de Aithera*\n\n"
            f"IA: {health.get('provider', 'N/A')} / {health.get('model', 'N/A')}\n"
            f"Estado IA: {'✅' if health.get('healthy') else '❌'}\n\n"
            f"🧠 Memoria:\n"
            f"  Conversaciones: {mem_stats['conversations']}\n"
            f"  Contexto usuario: {mem_stats['user_context']}\n"
            f"  Documentos: {mem_stats['documents']}"
        )
        await update.message.reply_text(status_text, parse_mode="Markdown")
    
    # ─── HANDLER DE MENSAJES DE TEXTO (CHAT) ─────────────────────────────────
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._unauthorized_response(update, context)
        
        user_message = update.message.text
        
        # Indicar que Aithera está "escribiendo"
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        # Construir contexto de memoria
        memory_context = memory_manager.build_context_for_chat(user_message)
        system_prompt = "Eres Aithera, un sistema operativo personal de IA. Responde de forma concisa para Telegram (máximo 500 caracteres). Usa emojis con moderación."
        if memory_context:
            system_prompt = f"{system_prompt}\n\n{memory_context}"
        
        # Almacenar mensaje del usuario
        memory_manager.store_conversation("user", user_message, {"interface": "telegram"})
        
        # Obtener respuesta (no-streaming para Telegram)
        try:
            result = await ai_manager.chat(user_message, system_prompt)
            response_text = result.get("response", "No pude generar una respuesta.")
            
            # Almacenar respuesta
            memory_manager.store_conversation("assistant", response_text, {"interface": "telegram"})
            
            # Telegram tiene límite de 4096 chars por mensaje
            if len(response_text) > 4000:
                response_text = response_text[:4000] + "...\n_(respuesta truncada)_"
            
            await update.message.reply_text(response_text)
        except Exception as e:
            logger.error(f"Error en handle_message: {e}")
            await update.message.reply_text("❌ Error al procesar tu mensaje. Inténtalo de nuevo.")
    
    # ─── CICLO DE VIDA DEL BOT ────────────────────────────────────────────────
    
    async def start(self):
        """Inicia el bot en modo polling. Llamado desde el lifespan de FastAPI."""
        if self._running:
            return
        
        self._app = (
            Application.builder()
            .token(self.token)
            .build()
        )
        
        # Registrar comandos
        self._app.add_handler(CommandHandler("start", self.cmd_start))
        self._app.add_handler(CommandHandler("proyectos", self.cmd_proyectos))
        self._app.add_handler(CommandHandler("tareas", self.cmd_tareas))
        self._app.add_handler(CommandHandler("estado", self.cmd_estado))
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Configurar los comandos en el menú de Telegram
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
        logger.info("Bot de Telegram iniciado en modo polling")
    
    async def stop(self):
        """Para el bot. Llamado en el shutdown de FastAPI."""
        if self._app and self._running:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
            self._running = False
            logger.info("Bot de Telegram detenido")


# Singleton global (None hasta que se configure)
_telegram_bot: Optional[AitheraTelegramBot] = None


def get_telegram_bot() -> Optional[AitheraTelegramBot]:
    return _telegram_bot


def init_telegram_bot(token: str, authorized_chat_id: int) -> AitheraTelegramBot:
    global _telegram_bot
    _telegram_bot = AitheraTelegramBot(token, authorized_chat_id)
    return _telegram_bot
```

---

## TAREA 3 — Integrar el bot en el lifespan de FastAPI

### Modificar `backend/app/main.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    log_info("startup", "Iniciando Aithera Backend V0.7.0...")
    Base.metadata.create_all(bind=engine)
    
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
        else:
            log_info("startup", "Bot de Telegram no configurado (opcional)")
    except Exception as e:
        log_error("startup", e, "Error iniciando bot de Telegram (no es crítico)")
    finally:
        db.close()
    
    yield
    
    # Parar el bot al cerrar
    from app.telegram.bot import get_telegram_bot
    bot = get_telegram_bot()
    if bot:
        await bot.stop()
    log_info("shutdown", "Cerrando Aithera Backend...")
```

---

## TAREA 4 — Nuevos endpoints de configuración Telegram

### Añadir a `backend/app/api/endpoints/config.py` (o crear `telegram.py`):

**`GET /api/telegram/status`**
```json
{ "configured": true, "running": true, "bot_username": "@AitheraBot" }
```

**`POST /api/telegram/configure`**
```json
Body: { "token": "1234567890:AAF...", "chat_id": 123456789 }
Response: { "success": true, "bot_username": "@AitheraBot" }
```

Al llamar a este endpoint:
1. Guarda `telegram_bot_token` y `telegram_chat_id` en la tabla `config`
2. Inicia el bot inmediatamente (sin reiniciar el servidor)
3. Devuelve el username del bot para confirmar que el token es válido

**`DELETE /api/telegram/configure`**
```json
Response: { "stopped": true }
```

---

## TAREA 5 — UI de configuración Telegram en Settings

### Modificar `frontend/src/pages/Settings.tsx`

Añadir sección "Telegram":

**Si no está configurado**:
- Instrucciones: "1. Habla con @BotFather en Telegram, 2. Crea un bot con /newbot, 3. Copia el token"
- Campo para el Bot Token
- Instrucciones para obtener el chat_id: "1. Escribe /start a tu bot, 2. Visita https://api.telegram.org/bot{TOKEN}/getUpdates"
- Campo para el Chat ID
- Botón "Conectar bot"

**Si está configurado**:
- Estado: "✓ Bot activo: @NombreDeBot"
- Botón "Desconectar"

---

## TAREA 6 — Notificaciones proactivas (opcional, baja prioridad)

Una vez que el bot está funcionando, se puede añadir un sistema de notificaciones. Esto es opcional en V0.7 y puede dejarse para la Fase 6 (Automation Engine).

Ejemplo de notificación desde el backend:
```python
async def send_notification(message: str):
    """Envía un mensaje proactivo al propietario via Telegram."""
    bot = get_telegram_bot()
    if bot and bot._running:
        await bot._app.bot.send_message(
            chat_id=bot.authorized_chat_id,
            text=message
        )
```

---

## CÓMO OBTENER EL CHAT_ID (instrucciones para el usuario)

1. Crear el bot en Telegram con @BotFather: `/newbot` → elegir nombre → copiar el token
2. Abrir Telegram y escribir `/start` al bot recién creado
3. Visitar en el browser: `https://api.telegram.org/bot{TU_TOKEN}/getUpdates`
4. En el JSON de respuesta, buscar `"chat":{"id":XXXXXXX}` — ese número es el chat_id
5. Copiar el token y el chat_id en la configuración de Aithera

---

## CRITERIOS DE ACEPTACIÓN

Esta fase está completa cuando:

1. ✅ El usuario puede configurar el bot desde la UI de Settings
2. ✅ `/start` en Telegram recibe la bienvenida de Aithera
3. ✅ `/proyectos` devuelve los proyectos activos de la BD
4. ✅ `/tareas` devuelve las tareas pendientes de la BD
5. ✅ `/estado` muestra el estado del sistema
6. ✅ Escribir un mensaje de texto recibe una respuesta de la IA activa
7. ✅ Mensajes de usuarios no autorizados son rechazados silenciosamente
8. ✅ El bot se inicia automáticamente al arrancar el backend si está configurado
9. ✅ El bot se para graciosamente cuando el backend se cierra
10. ✅ `GET /api/telegram/status` reporta correctamente si el bot está activo

---

## ARCHIVOS CREADOS/MODIFICADOS EN ESTA FASE

**Nuevo directorio**: `backend/app/telegram/`
- `backend/app/telegram/__init__.py`
- `backend/app/telegram/bot.py`

**Modificados**:
- `backend/app/main.py` — Lifespan del bot, bump a v0.7.0
- `backend/app/api/endpoints/config.py` — Endpoints de configuración Telegram
- `backend/requirements.txt` — python-telegram-bot
- `frontend/src/pages/Settings.tsx` — Sección Telegram

---

*Al completar esta fase, Aithera V0.7.0 es accesible desde Telegram.*
*Las fases siguientes (V0.8 Automation, V0.9 PWA, V1.0 Orchestrator) se documentarán en ficheros separados cuando llegue el momento.*
