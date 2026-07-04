# app/gateway/adapters/telegram_adapter.py
#
# V0.8 (PLAN_MAESTRO_2026): adapter de Telegram sobre el Gateway. Pieza FINA:
#   - chat natural  -> to_envelope() -> gateway.dispatch() -> deliver()
#     (reusa chat_message_handler: IA activa + memoria, con B21 aplicado).
#   - comandos /start /proyectos /tareas /estado -> lecturas simples de la BD.
#
# Diseño y contrato: PLAN_MAESTRO_2026/06_GATEWAY_V08_DISENO.md
#
# Seguridad: la whitelist de chat_id se comprueba tanto en authorize() (chat
# natural, via dispatch) como en cada comando. Un chat no autorizado solo
# obtiene su propio chat_id (por /start) para que el dueño lo añada.
#
# IMPORTANTE: las dependencias de `telegram` se importan DENTRO de start() y de
# los callbacks, nunca a nivel de modulo. Asi el modulo es importable y
# testeable (to_envelope, authorize, formateadores) sin python-telegram-bot.

from __future__ import annotations

from typing import Any, Optional, Set

from app.core.logging_config import get_system_logger
from app.gateway.base import ChannelAdapter
from app.gateway.envelope import MessageEnvelope, OutboundMessage

logger = get_system_logger("telegram")


# ----------------------------------------------------------------------
# Formateadores de comandos — funciones PURAS (reciben una sesion de BD y
# devuelven texto). Separadas de los callbacks para poder testearlas.
# ----------------------------------------------------------------------

def format_proyectos(db) -> str:
    from app.db.models import Project
    rows = (
        db.query(Project)
        .filter(Project.status != "archived")
        .order_by(Project.updated_at.desc())
        .all()
    )
    if not rows:
        return "No tienes proyectos activos."
    lines = ["*Proyectos*"]
    for p in rows:
        pct = int(round((p.progress or 0.0)))
        lines.append(f"• {p.name} — {p.status} ({pct}%)")
    return "\n".join(lines)


def format_tareas(db) -> str:
    from app.db.models import Task
    rows = (
        db.query(Task)
        .filter(Task.status != "done", Task.status != "completed")
        .order_by(Task.priority.desc())
        .all()
    )
    if not rows:
        return "No tienes tareas pendientes. 🎉"
    lines = ["*Tareas pendientes*"]
    for t in rows:
        due = f" · vence {t.due_date:%d/%m}" if t.due_date else ""
        lines.append(f"• [{t.priority}] {t.title}{due}")
    return "\n".join(lines)


def format_estado(db) -> str:
    from datetime import datetime
    from app.db.models import Project, Task, CalendarEvent
    n_proj = db.query(Project).filter(Project.status == "active").count()
    n_task = (
        db.query(Task)
        .filter(Task.status != "done", Task.status != "completed")
        .count()
    )
    n_ev = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.start_date >= datetime.utcnow())
        .count()
    )
    return (
        "*Estado de Aithera*\n"
        f"• Proyectos activos: {n_proj}\n"
        f"• Tareas pendientes: {n_task}\n"
        f"• Eventos próximos: {n_ev}"
    )


_WELCOME = (
    "Soy *Aithera*. Escríbeme normalmente y te respondo con la IA activa.\n\n"
    "Comandos:\n"
    "/proyectos — tus proyectos activos\n"
    "/tareas — tus tareas pendientes\n"
    "/estado — resumen rápido"
)


class TelegramAdapter(ChannelAdapter):
    """Adapter de Telegram (python-telegram-bot v21, polling).

    Construccion barata (no toca la red ni importa telegram). El objeto
    Application y el arranque del polling ocurren en start()."""

    name = "telegram"

    def __init__(self, token: str, allowed_chat_ids: Optional[Set[str]] = None) -> None:
        self._token = token
        # whitelist como strings para comparar sin ambiguedad int/str
        self._allowed: Set[str] = {str(c).strip() for c in (allowed_chat_ids or set())}
        self._app: Any = None  # telegram.ext.Application, creado en start()

    # -------------------- seguridad --------------------

    def is_allowed(self, chat_id) -> bool:
        """whitelist vacia => canal cerrado (nadie autorizado salvo /start)."""
        return str(chat_id) in self._allowed

    async def authorize(self, envelope: MessageEnvelope) -> bool:
        return self.is_allowed(envelope.user_ref)

    # -------------------- traduccion --------------------

    async def to_envelope(self, raw: Any) -> MessageEnvelope:
        """De un telegram.Update a MessageEnvelope. Accede por atributos para
        no depender de los tipos de la lib (facilita el test con dobles)."""
        chat = getattr(raw, "effective_chat", None)
        msg = getattr(raw, "effective_message", None) or getattr(raw, "message", None)
        chat_id = getattr(chat, "id", None)
        text = getattr(msg, "text", "") or ""
        message_id = getattr(msg, "message_id", None)
        return MessageEnvelope(
            channel=self.name,
            user_ref=str(chat_id),
            text=text,
            metadata={"message_id": message_id},
        )

    async def deliver(self, message: OutboundMessage, envelope: MessageEnvelope) -> None:
        """Entrega la respuesta al chat de origen, con reintentos ante fallos de
        red transitorios (la API de Telegram a veces da TimedOut/ConnectTimeout
        aunque el getUpdates funcione)."""
        if self._app is None:
            logger.error("[telegram] deliver sin Application iniciada")
            return
        import asyncio
        from telegram.error import NetworkError, TimedOut

        text = message.text or "(sin respuesta)"
        last_err = None
        for attempt in range(3):
            try:
                await self._app.bot.send_message(chat_id=int(envelope.user_ref), text=text)
                return
            except (TimedOut, NetworkError) as e:
                last_err = e
                await asyncio.sleep(2.0 * (attempt + 1))  # 2s, 4s
        logger.error(
            f"[telegram] no se pudo entregar tras 3 intentos (red inestable): {last_err!r}"
        )

    # -------------------- ciclo de vida --------------------

    async def start(self) -> None:
        from telegram.ext import (
            Application,
            CommandHandler,
            MessageHandler,
            filters,
        )

        # Timeouts generosos: la conexion a api.telegram.org puede ser lenta o
        # inestable segun la red; con margen amplio evitamos TimedOut espurios.
        self._app = (
            Application.builder()
            .token(self._token)
            .connect_timeout(30.0)
            .read_timeout(30.0)
            .write_timeout(30.0)
            .pool_timeout(30.0)
            .get_updates_connect_timeout(30.0)
            .get_updates_read_timeout(30.0)
            .build()
        )
        self._app.add_handler(CommandHandler("start", self._cmd_start))
        self._app.add_handler(CommandHandler("proyectos", self._cmd_proyectos))
        self._app.add_handler(CommandHandler("tareas", self._cmd_tareas))
        self._app.add_handler(CommandHandler("estado", self._cmd_estado))
        # cualquier texto que NO sea comando -> chat natural via Gateway
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_text)
        )
        # error handler: evita el traceback "No error handlers are registered"
        # y deja el fallo (normalmente de red) en el log de forma limpia.
        self._app.add_error_handler(self._on_error)

        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(drop_pending_updates=True)
        logger.info(
            f"[telegram] polling activo — {len(self._allowed)} chat_id autorizados"
        )

    async def stop(self) -> None:
        if self._app is None:
            return
        try:
            if self._app.updater:
                await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
        finally:
            self._app = None
            logger.info("[telegram] detenido")

    # -------------------- callbacks --------------------

    async def _reply(self, update: Any, text: str) -> None:
        """Responde en Markdown, con fallback a texto plano si el parse falla."""
        try:
            from telegram.constants import ParseMode
            await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await update.effective_message.reply_text(text)

    def _guard(self, update: Any) -> bool:
        return self.is_allowed(getattr(update.effective_chat, "id", None))

    async def _cmd_start(self, update: Any, _ctx: Any) -> None:
        chat_id = getattr(update.effective_chat, "id", None)
        if self.is_allowed(chat_id):
            await self._reply(update, _WELCOME)
        else:
            await self._reply(
                update,
                "No estás autorizado todavía.\n"
                f"Tu chat_id es: `{chat_id}`\n"
                "Pídele al dueño de Aithera que lo añada a la whitelist "
                "(Ajustes → Telegram) y vuelve a intentarlo.",
            )

    async def _cmd_proyectos(self, update: Any, _ctx: Any) -> None:
        if not self._guard(update):
            return await self._reply(update, "No autorizado.")
        await self._reply(update, self._with_db(format_proyectos))

    async def _cmd_tareas(self, update: Any, _ctx: Any) -> None:
        if not self._guard(update):
            return await self._reply(update, "No autorizado.")
        await self._reply(update, self._with_db(format_tareas))

    async def _cmd_estado(self, update: Any, _ctx: Any) -> None:
        if not self._guard(update):
            return await self._reply(update, "No autorizado.")
        await self._reply(update, self._with_db(format_estado))

    async def _on_text(self, update: Any, _ctx: Any) -> None:
        """Chat natural: delega en el Gateway (que autoriza y entrega)."""
        from app.gateway.gateway import gateway
        env = await self.to_envelope(update)
        await gateway.dispatch(env)

    async def _on_error(self, _update: Any, context: Any) -> None:
        """Handler global de errores de PTB (normalmente red hacia Telegram)."""
        logger.error(f"[telegram] error no controlado: {getattr(context, 'error', None)!r}")

    @staticmethod
    def _with_db(fn) -> str:
        """Ejecuta un formateador con una sesion de BD de vida corta."""
        from app.db.database import SessionLocal
        db = SessionLocal()
        try:
            return fn(db)
        finally:
            db.close()
