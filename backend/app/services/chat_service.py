# app/services/chat_service.py — pipeline UNICO de chat (V0.85 M4)
#
# Consolida /api/chat (chat.py::chat) y el Gateway (gateway.py::chat_message_
# handler): ambos delegan en answer() de aqui. Antes duplicaban casi entera
# la logica de system prompt + memoria + IA + strip_reasoning (doc 12 A4);
# solo divergian en si persisten en ChatMessage (tabla SQL del historial de
# la UI de escritorio) y en el texto de fallback cuando la respuesta viene
# vacia — ambas diferencias se preservan via parametros/en el caller.
#
# Contexto con fuentes (doc 07 §8): build_system_prompt() combina el prompt
# base + preferencias del usuario (coleccion legacy 'user_context', fuera del
# MOS — doc 07 no la migra) + memoria del MOS via memory_router.context()
# (conversacional + personal + proyecto + skill + decision, CON atribucion de
# fuente por linea). Presupuesto de latencia duro: el context() del MOS tiene
# 300 ms; si lo excede, se usa contexto vacio — el chat NUNCA espera a la
# memoria (igual que ya hacia el codigo legacy, que ni siquiera tenia esta
# proteccion — es un endurecimiento, no una regresion).
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from app.db.database import SessionLocal
from app.db.models import ChatMessage
from app.memory import memory_manager, memory_router

DEFAULT_SYSTEM_PROMPT = """Eres Aithera, un sistema operativo personal de IA.

Conoces los proyectos, tareas, calendario y preferencias del usuario.
Responde siempre en el idioma del usuario. Se conciso y util.

Responde SIEMPRE en texto plano: nunca uses tablas, ni **negrita**/*cursiva*
con asteriscos, ni encabezados con #. La interfaz muestra tu respuesta tal
cual, sin renderizar markdown — una tabla con | y — sale desordenada e
ilegible. Si necesitas enumerar varias cosas, usa saltos de linea con un
guion simple por elemento."""

CONTEXT_TIMEOUT_S = 0.3  # doc 07 §8: presupuesto de latencia del contexto del MOS
CONTEXT_MAX_TOKENS = 1200

# ---------------------------------------------------------------------------
# Continuidad de la conversación (R6.5b, doc 23)
# ---------------------------------------------------------------------------
# EL PRESUPUESTO, y por qué es obligatorio: sin tope, una conversación larga
# acaba metiendo cientos de turnos en CADA mensaje — se come la ventana del
# modelo, encarece cada respuesta y, con MiniMax (2048 tokens de salida máx),
# deja sin sitio a la respuesta. Se recorta por los turnos MÁS ANTIGUOS: lo
# reciente es lo que da continuidad.
HISTORY_MAX_TURNS = 12        # 6 intercambios; suficiente para no perder el hilo
HISTORY_MAX_CHARS = 6000      # tope duro; manda el que se alcance primero

# Cuánto del turno anterior entra en la CONSULTA semántica al MOS (ver
# `_memory_query`). Corto a propósito: es una consulta, no contexto.
QUERY_PREV_CHARS = 300


def _preferences_block(query: str) -> str:
    """Preferencias/hechos del usuario (coleccion legacy 'user_context'). Se
    mantiene aparte del MOS: no es uno de los 5 MemoryType activos y doc 07
    no pide migrarla en V0.85 — se sigue leyendo por su via original."""
    if not memory_manager.is_healthy() or not query:
        return ""
    try:
        items = memory_manager.search_user_context(query, n_results=3)
    except Exception as e:
        print(f"[chat_service] search_user_context error: {e}")
        return ""
    if not items:
        return ""
    lines = ["Contexto del usuario (preferencias y hechos relevantes):"]
    lines += [f"- {it['content']}" for it in items]
    return "\n".join(lines)


def recent_turns(session_id: Optional[str], *, max_turns: int = HISTORY_MAX_TURNS,
                 max_chars: int = HISTORY_MAX_CHARS) -> list[dict]:
    """Los últimos turnos de ESTA conversación, listos para `ExecutionRequest.
    messages` (formato canónico de R6.5a).

    Se piden a la BD los más RECIENTES (`ORDER BY id DESC LIMIT`) y luego se
    devuelven en orden cronológico: traer la conversación entera para quedarse
    con el final sería absurdo en una charla de 500 mensajes.

    El recorte por caracteres se hace desde el final hacia atrás — se conservan
    los turnos recientes y se sueltan los viejos, que es lo que mantiene el hilo.

    Sin `session_id` devuelve [] : un mensaje sin conversación (el AE, un agente,
    un canal sin sesión) no tiene historial que recuperar, y adivinarlo mezclaría
    conversaciones ajenas."""
    if not session_id:
        return []
    db = SessionLocal()
    try:
        filas = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.desc())
            .limit(max_turns)
            .all()
        )
    except Exception as e:
        print(f"[chat_service] no se pudo leer el historial: {e}")
        return []
    finally:
        db.close()

    # `filas` viene del MÁS NUEVO al más viejo (ORDER BY id DESC). Se recorre en
    # ese orden justamente para recortar: cuando se acaba el presupuesto, lo que
    # se queda fuera es lo VIEJO. Al final se le da la vuelta una sola vez, para
    # que el modelo lea la conversación en su orden natural.
    turnos: list[dict] = []
    total = 0
    for fila in filas:
        contenido = (fila.content or "").strip()
        if not contenido:
            continue
        if total + len(contenido) > max_chars and turnos:
            break                          # cabe lo reciente; lo viejo se suelta
        turnos.append({
            "role": "assistant" if fila.role == "assistant" else "user",
            "content": contenido,
        })
        total += len(contenido)
    turnos.reverse()
    return turnos


def _memory_query(user_message: str, history: list[dict]) -> str:
    """La consulta con la que se busca en el MOS.

    [R6.5b] EL ARREGLO DE MÁS IMPACTO DEL SPRINT, y el más barato: hasta ahora
    la consulta era el mensaje actual A SECAS. Por eso Aithera recordaba cosas
    de hace días pero no de qué se estaba hablando hace diez segundos: si
    preguntas «¿y cuánto cuesta?», ese texto no se parece a NADA en la memoria,
    así que la búsqueda semántica no recuperaba el producto del que hablabais.

    Añadiendo el último turno del usuario, la consulta pasa a tener de qué
    agarrarse. Arregla de paso el recuerdo ENTRE conversaciones, sin ningún
    modelo nuevo ni coste adicional."""
    actual = (user_message or "").strip()
    previo = ""
    for turno in reversed(history):
        if turno["role"] != "user":
            continue
        candidato = (turno["content"] or "").strip()
        # Si el "turno anterior" ES el mensaje actual, el historial se leyó
        # DESPUÉS de persistirlo. Duplicar el texto en la consulta no aporta
        # nada y sesga la búsqueda. Salta al turno de usuario de antes.
        # (Visto en la verificación en vivo de R6.5b: producía la consulta
        # «¿y cuánto cuesta?\n¿y cuánto cuesta?».)
        if candidato == actual:
            continue
        previo = candidato[:QUERY_PREV_CHARS]
        break
    return f"{previo}\n{actual}".strip() if previo else actual


def _profile_block() -> str:
    """[R6.5c] Hechos estables del usuario (nombre, ocupación, preferencias
    duraderas…), destilados de noche por `app.memory.profile`.

    DETERMINISTA a propósito, no semántico: `mos_ctx` de abajo depende de
    ganar un hueco en el `top_k` de una búsqueda por similitud — y en
    `mem_personal` compiten cientos de emails ingeridos (M2) que a menudo
    puntúan más alto que una frase corta como "Se llama X". Hallazgo real de
    la verificación en vivo de R6.5c: con solo `context()`, un hecho recién
    guardado no aparecía ni una vez en top_k=8 frente al buzón real del
    usuario — el criterio de cierre #1 del sprint ("se usa en una
    conversación NUEVA") fallaba en la práctica. Por eso "quién es el
    usuario" no se busca, se LEE entero (acotado por `MAX_FACTS_PER_RUN`,
    unas pocas decenas como mucho — barato, sin LLM, sin ranking)."""
    try:
        from app.memory import profile

        hechos = profile.list_facts()
    except Exception as e:
        print(f"[chat_service] list_facts error: {e}")
        return ""
    if not hechos:
        return ""
    return "\n".join(f"- {h['value']}" for h in hechos)


async def _mos_context_block(query: str, project_id=None) -> str:
    """Memoria del MOS con atribucion de fuente. memory_router.context() ya
    cubre conversaciones (mem_conversational, alias de la coleccion legacy) +
    lo ingestado por M2/M3 (emails, agenda, resumenes diarios) — sin duplicar
    la busqueda conversacional de _preferences_block, que es un dominio
    distinto (preferencias, no historial)."""
    if not query:
        return ""
    try:
        return await asyncio.wait_for(
            # [S2-extra, C-1b] aislamiento de proyecto tambien en el chat.
            memory_router.context(query, max_tokens=CONTEXT_MAX_TOKENS, project_id=project_id),
            timeout=CONTEXT_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        print(f"[chat_service] memory_router.context excedio {CONTEXT_TIMEOUT_S}s — contexto vacio")
        return ""
    except Exception as e:
        print(f"[chat_service] memory_router.context error: {e}")
        return ""


def _capabilities_block() -> str:
    """[R6, doc 23] Lo que Aithera sabe hacer, generado desde el catálogo real
    (`app.tie.capabilities_map`) y cacheado ahí mismo — llamarlo aquí en cada
    mensaje no recorre el catálogo cada vez. Se incluye SIEMPRE (no solo
    cuando el usuario pregunta "¿qué sabes hacer?"): así el modelo puede
    ofrecer una capacidad sin que el usuario tenga que adivinar que existe, y
    el coste es despreciable (tope duro de caracteres, ver `MAX_CHARS`).
    Best-effort: si el TIE no está disponible en este proceso (p.ej. algunos
    tests unitarios), el chat sigue funcionando sin este bloque."""
    try:
        import app.tie as tie

        return tie.capabilities_summary()
    except Exception as e:
        print(f"[chat_service] capabilities_summary error: {e}")
        return ""


async def build_system_prompt(user_message: str, *, history: Optional[list] = None,
                              project_id: Optional[int] = None) -> str:
    """[V0.85 M4] Sustituye a chat.py::_build_system_prompt (ahora async: el
    contexto del MOS es una llamada async con presupuesto de latencia).

    `history` [R6.5b]: los turnos previos. NO se meten en el system prompt — su
    sitio es `ExecutionRequest.messages` (R6.5a). Aquí se usan SOLO para
    construir una consulta de memoria que tenga de qué agarrarse
    (ver `_memory_query`)."""
    base = DEFAULT_SYSTEM_PROMPT
    caps = _capabilities_block()
    if caps:
        base = f"{base}\n\n{caps}"
    if not user_message:
        return base
    consulta = _memory_query(user_message, history or [])
    prefs = _preferences_block(consulta)
    profile = _profile_block()
    mos_ctx = await _mos_context_block(consulta, project_id=project_id)
    parts = [base]
    if profile:
        parts.append(f"Lo que sabes del usuario:\n{profile}")
    if prefs:
        parts.append(prefs)
    if mos_ctx:
        parts.append(f"Memoria relevante (con fuente):\n{mos_ctx}")
    return "\n\n".join(parts)


@dataclass
class ChatAnswer:
    text: str  # puede venir vacio; el caller decide el texto de fallback a mostrar
    model: Optional[str]
    tokens: Optional[int]


async def answer(
    message: str, *, channel: str = "web", persist_chat_message: bool = True,
    model_override: Optional[str] = None, project_id: Optional[int] = None,
    session_id: Optional[str] = None,
) -> ChatAnswer:
    """Pipeline UNICO de chat (no streaming): system prompt (con memoria y
    fuentes) + MEL + persistencia. Usado por POST /api/chat (chat.py) y por el
    Gateway (gateway.py::chat_message_handler).

    [E2, doc 22 §3·E2] La llamada al modelo pasa por el MEL: pide la capacidad
    CHAT y el MEL elige el modelo por la política activa (el `strip_reasoning`
    B21 ya lo aplica el MEL). El resto (system prompt con memoria, orden de
    persistencia) NO cambia.

    El mensaje del usuario se indexa ANTES de llamar a la IA (si la IA falla,
    el mensaje sigue quedando en memoria — mismo orden que el codigo legacy).

    persist_chat_message=False: no escribe en ChatMessage (tabla SQL del
    historial de la UI de escritorio) — asi se comportaba ya el Gateway antes
    de esta consolidacion; la memoria semantica (ChromaDB) SIEMPRE se escribe,
    independientemente de este flag.

    `model_override` [E2b, doc 14 §3.5]: id EXACTO de un modelo pedido
    explícitamente por el usuario. En E2 nadie lo pasa (siempre None → decide
    la política); E2b lo cablea desde el camino corto del TIE.

    `session_id` [R6.5b]: la conversación a la que pertenece este turno. Con él
    se recuperan los turnos previos (con presupuesto) y se persiste el turno
    nuevo en la misma conversación. Sin él, el comportamiento es el de siempre:
    un mensaje suelto sin continuidad — que es lo correcto para el AE, los
    agentes y cualquier canal sin conversación."""
    from app.mel import Capability, ExecutionRequest, complete as mel_complete

    history = recent_turns(session_id)
    system_prompt = await build_system_prompt(message, history=history, project_id=project_id)

    memory_manager.store_conversation("user", message, metadata={"channel": channel})

    res = await mel_complete(ExecutionRequest(
        capability=Capability.CHAT, prompt=message, system_prompt=system_prompt,
        messages=history,          # [R6.5b] los turnos previos, vía el canal de R6.5a
        model_override=model_override,
        # [E2b] project_id en context_tags → el MEL consulta el pin de proyecto
        # (mel_overrides) si lo hay. Sin project_id, tags vacío (chat general).
        context_tags={"project_id": project_id} if project_id else {},
    ))
    text = res.text or ""   # el MEL ya aplicó strip_reasoning (B21)
    model = res.served_by.model if res.served_by else None
    tokens = res.usage.tokens if res.usage else None

    if text:
        memory_manager.store_conversation("assistant", text, metadata={"channel": channel})

    if persist_chat_message:
        db = SessionLocal()
        try:
            db.add(ChatMessage(role="user", content=message, model_used=model,
                               session_id=session_id))
            db.add(ChatMessage(
                role="assistant", content=text, model_used=model, tokens_used=tokens,
                session_id=session_id,
            ))
            db.commit()
        finally:
            db.close()

    return ChatAnswer(text=text, model=model, tokens=tokens)
