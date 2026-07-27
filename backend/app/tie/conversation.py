# app/tie/conversation.py — misiones en segundo plano (modo conversación, A·VOZ-4)
#
# EL PROBLEMA QUE RESUELVE (doc 32 A·VOZ-4): en conversación —sobre todo por
# voz— dar una orden no debe cortar el diálogo. Aithera acusa recibo al instante
# ("me pongo a ello"), ejecuta DETRÁS, y avisa cuando termina o falla, como hace
# Claude Code. El turno de chat/voz se cierra con el acuse; el reporte llega por
# otro camino más tarde.
#
# LAS DOS PIEZAS:
#   1) Registro de misiones de fondo en curso (mission_id → contexto de entrega).
#      Quién lanza la misión la registra ANTES de crear la tarea de fondo, así el
#      evento `mission.completed`/`failed` —que llega después— siempre encuentra
#      a quién avisar.
#   2) Un ÚNICO handler suscrito al bus (`mission.completed`/`mission.failed`):
#      cuando una misión REGISTRADA termina, construye un reporte en lenguaje
#      natural desde el outcome de la traza y lo entrega por el canal de origen.
#      Las misiones NO registradas (primer plano, AE, WPMS) se ignoran.
#
# POR QUÉ EVENT-DRIVEN Y NO await inline: una misión compleja con paso sensible
# se PAUSA en el gate del plan (`mission.state == "waiting"`) y no termina hasta
# que el usuario aprueba —minutos u horas después, en otra petición HTTP—. El
# bus captura esa terminación tardía igual de bien que la inmediata; un await
# inline no podría (el runner ya habría devuelto). El caso "waiting" se comunica
# aparte (on_gate_pending): "necesito tu permiso", sin bloquear el diálogo.
#
# ENTREGA (doc 32 paso 2): reusa `core/notify.py` (R5) para el push externo
# (Telegram) y una cola en memoria + un `ChatMessage` persistido para el chat de
# Electron (que sondea `GET /api/chat/pending-reports`). BEST-EFFORT SIEMPRE: un
# fallo de entrega nunca rompe nada; el reporte también vive en Misiones.
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.core.logging_config import get_system_logger
from app.core.strings import t as _t

logger = get_system_logger("tie.conversation")

# Eventos de terminación que disparan un reporte async. `cancelled` NO está: si
# el usuario canceló (kill-switch) o descartó el plan, ya lo sabe — no se le
# vuelve a avisar de algo que hizo él mismo.
_SETTLE_EVENTS = ("mission.completed", "mission.failed")


@dataclass
class _BgCtx:
    """A quién y por dónde avisar cuando una misión de fondo termine."""
    trace_id: str
    session_id: Optional[str]
    channel: Optional[str]
    goal: str


# mission_id → contexto de entrega. Solo contiene misiones de FONDO en curso.
_pending: dict[str, _BgCtx] = {}


# ---------------------------------------------------------------------------
# Cola de reportes para el chat web (Electron sondea, no hay push por SSE ya)
# ---------------------------------------------------------------------------
@dataclass
class _Report:
    seq: int
    session_id: Optional[str]
    text: str
    trace_id: Optional[str]
    created_at: str


_reports: list[_Report] = []
_seq = 0
_MAX_REPORTS = 200   # ring: nunca crece sin límite


def acuse_text() -> str:
    """El acuse inmediato. Determinista (0 LLM) a propósito: el objetivo de
    A·VOZ-4 es responder en < 2 s; una llamada al modelo lo arruinaría."""
    return _t("conversation.acuse")


def register(mission_id: str, trace_id: str, *, session_id: Optional[str],
             channel: Optional[str], goal: str) -> None:
    """Anota una misión de fondo ANTES de lanzarla (para que el evento de
    terminación, que llega después, encuentre a quién avisar)."""
    _pending[mission_id] = _BgCtx(trace_id=trace_id, session_id=session_id,
                                  channel=channel, goal=goal or "")


def unregister(mission_id: str) -> None:
    _pending.pop(mission_id, None)


async def report_failure(mission_id: str, *, text: Optional[str] = None) -> None:
    """Aviso de que una misión de fondo no pudo terminar (excepción DURA que no
    llegó a emitir `mission.failed`). Usa el contexto registrado y desregistra."""
    ctx = _pending.pop(mission_id, None)
    if ctx is None:
        return
    await _deliver(text or _t("conversation.report_error"), ctx)


async def on_gate_pending(mission_id: str) -> None:
    """La misión se pausó en un gate (necesita permiso). Se avisa por el canal —
    hablando, en voz— SIN bloquear el diálogo, y se MANTIENE registrada: cuando
    el usuario apruebe y la misión termine de verdad, el bus entregará el reporte
    final por este mismo camino."""
    ctx = _pending.get(mission_id)
    if ctx is None:
        return
    text = _t("conversation.gate_pending", goal=(ctx.goal or "eso")[:120])
    await _deliver(text, ctx)


# ---------------------------------------------------------------------------
# Handler del bus — el corazón del reporte async
# ---------------------------------------------------------------------------
async def _on_settled(event) -> None:
    """Suscrito a `mission.completed`/`mission.failed`. Solo actúa sobre misiones
    de FONDO registradas; las de primer plano (que emiten los mismos eventos) se
    ignoran. Best-effort de punta a punta."""
    try:
        payload = getattr(event, "payload", None) or {}
        mission_id = payload.get("mission_id")
        if not mission_id:
            return
        ctx = _pending.get(mission_id)
        if ctx is None:
            return   # no es una misión de fondo en conversación — la ignoramos
        unregister(mission_id)

        # El texto ya lo escribió el responder/acción directa en la traza; el
        # evento solo trae metadatos (doc 17).
        from app.tie import tracer

        outcome = (tracer.get_outcome(ctx.trace_id) or "").strip()
        ok = event.name == "mission.completed"
        if ok:
            text = _t("conversation.report_done", outcome=outcome or _t("pipeline.generic_done"))
        else:
            text = _t("conversation.report_failed", outcome=outcome or _t("pipeline.generic_could_not"))
        await _deliver(text, ctx)
    except Exception as e:
        logger.error(f"[conversation] _on_settled falló (ignorado): {type(e).__name__}: {e}")


async def deliver_report(text: str, *, session_id: Optional[str] = None,
                         channel: Optional[str] = None, trace_id: Optional[str] = None) -> None:
    """Entrega un reporte suelto (no atado al registro de misiones). Lo usa el
    Orquestador para avisar del resultado de una orquestación multi-objetivo, que
    termina a nivel de RUN (no emite `mission.*` propio)."""
    await _deliver(text, _BgCtx(trace_id=trace_id or "", session_id=session_id,
                                channel=channel, goal=""))


# ---------------------------------------------------------------------------
# Entrega por el canal de origen
# ---------------------------------------------------------------------------
async def _deliver(text: str, ctx: _BgCtx) -> None:
    """Empuja el aviso por donde toque. Web → cola sondeable + ChatMessage
    persistido; canales externos → `notify_user` (Telegram, etc.). Los caminos no
    se excluyen: si la preferencia del usuario es Telegram, también empujamos ahí
    aunque la conversación viniera del chat web."""
    # 1) Chat web (Electron): cola en memoria + ChatMessage para el historial.
    #    El canal "web"/"electron" no es un adapter del Gateway → se sondea.
    _push_web_report(text, ctx)

    # 2) Canal externo preferido (o el de origen si es empujable): notify_user
    #    decide y entrega; devuelve False sin drama si no había por dónde.
    try:
        from app.core.notify import notify_user

        channel = ctx.channel if (ctx.channel or "").lower() in ("telegram",) else None
        await notify_user(text, channel=channel)   # channel=None → usa la preferencia del usuario
    except Exception as e:
        logger.info(f"[conversation] push externo no entregado (no crítico): {type(e).__name__}: {e}")


def _push_web_report(text: str, ctx: _BgCtx) -> None:
    """Encola el reporte para que el chat web lo recoja al sondear, y lo persiste
    como ChatMessage del asistente para que sobreviva a una recarga/reinicio."""
    global _seq
    _seq += 1
    _reports.append(_Report(seq=_seq, session_id=ctx.session_id, text=text,
                            trace_id=ctx.trace_id, created_at=datetime.utcnow().isoformat()))
    while len(_reports) > _MAX_REPORTS:
        _reports.pop(0)

    # Persistir en el historial de la conversación (best-effort).
    try:
        from app.db.database import ChatMessage, SessionLocal

        db = SessionLocal()
        try:
            db.add(ChatMessage(role="assistant", content=text, session_id=ctx.session_id,
                               model_used="background-mission"))
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.info(f"[conversation] no se pudo persistir el reporte como ChatMessage: {e!r}")


def pending_reports(session_id: Optional[str], after_seq: int = 0) -> list[dict]:
    """Reportes de fondo para una sesión con `seq > after_seq` (cursor). Lo sondea
    `GET /api/chat/pending-reports`. No borra nada: el cursor avanza en el cliente,
    y el ring se auto-limpia por tamaño."""
    out = []
    for r in _reports:
        if r.seq <= after_seq:
            continue
        if session_id is not None and r.session_id != session_id:
            continue
        out.append({"seq": r.seq, "text": r.text, "trace_id": r.trace_id,
                    "created_at": r.created_at})
    return out


# ---------------------------------------------------------------------------
# Wiring del bus (idempotente) — lo llama el lifespan de main.py
# ---------------------------------------------------------------------------
def register_handlers() -> None:
    from app.core.events import subscribe, unsubscribe

    for name in _SETTLE_EVENTS:
        unsubscribe(name, _on_settled)
        subscribe(name, _on_settled)


def _reset_for_tests() -> None:
    """Limpia el estado global entre tests (registro + cola)."""
    global _seq
    _pending.clear()
    _reports.clear()
    _seq = 0
