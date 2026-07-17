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

from app.ai.reasoning_filter import strip_reasoning
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


async def _mos_context_block(query: str) -> str:
    """Memoria del MOS con atribucion de fuente. memory_router.context() ya
    cubre conversaciones (mem_conversational, alias de la coleccion legacy) +
    lo ingestado por M2/M3 (emails, agenda, resumenes diarios) — sin duplicar
    la busqueda conversacional de _preferences_block, que es un dominio
    distinto (preferencias, no historial)."""
    if not query:
        return ""
    try:
        return await asyncio.wait_for(
            memory_router.context(query, max_tokens=CONTEXT_MAX_TOKENS),
            timeout=CONTEXT_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        print(f"[chat_service] memory_router.context excedio {CONTEXT_TIMEOUT_S}s — contexto vacio")
        return ""
    except Exception as e:
        print(f"[chat_service] memory_router.context error: {e}")
        return ""


async def build_system_prompt(user_message: str) -> str:
    """[V0.85 M4] Sustituye a chat.py::_build_system_prompt (ahora async: el
    contexto del MOS es una llamada async con presupuesto de latencia)."""
    base = DEFAULT_SYSTEM_PROMPT
    if not user_message:
        return base
    prefs = _preferences_block(user_message)
    mos_ctx = await _mos_context_block(user_message)
    parts = [base]
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
    message: str, *, channel: str = "web", persist_chat_message: bool = True
) -> ChatAnswer:
    """Pipeline UNICO de chat (no streaming): system prompt (con memoria y
    fuentes) + IA + strip_reasoning + persistencia. Usado por POST /api/chat
    (chat.py) y por el Gateway (gateway.py::chat_message_handler).

    El mensaje del usuario se indexa ANTES de llamar a la IA (si la IA falla,
    el mensaje sigue quedando en memoria — mismo orden que el codigo legacy).

    persist_chat_message=False: no escribe en ChatMessage (tabla SQL del
    historial de la UI de escritorio) — asi se comportaba ya el Gateway antes
    de esta consolidacion; la memoria semantica (ChromaDB) SIEMPRE se escribe,
    independientemente de este flag.
    """
    from app.ai.ai_manager import ai_manager  # import diferido: patrón de email_service.py

    system_prompt = await build_system_prompt(message)

    memory_manager.store_conversation("user", message, metadata={"channel": channel})

    result = await ai_manager.chat(message=message, system_prompt=system_prompt)
    text = strip_reasoning(result.get("response", "")) or ""

    if text:
        memory_manager.store_conversation("assistant", text, metadata={"channel": channel})

    if persist_chat_message:
        db = SessionLocal()
        try:
            db.add(ChatMessage(role="user", content=message, model_used=result.get("model")))
            db.add(ChatMessage(
                role="assistant", content=text,
                model_used=result.get("model"), tokens_used=result.get("tokens"),
            ))
            db.commit()
        finally:
            db.close()

    return ChatAnswer(text=text, model=result.get("model"), tokens=result.get("tokens"))
