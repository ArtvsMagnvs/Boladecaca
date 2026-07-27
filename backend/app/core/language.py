# app/core/language.py — idioma de RESPUESTA del LLM (I18N-9, doc 30)
#
# QUÉ RESUELVE: hasta ahora Aithera respondía "en el idioma del usuario" —
# inferido del mensaje. Si el usuario tiene la app en inglés pero pega un
# documento en español y pide "summarize this", la respuesta salía en español.
# El usuario pidió lo contrario: "cuando tienes un idioma seleccionado, ese es
# el idioma con el que habla el chat", sin importar en qué idioma escriba o
# estén los documentos que pase.
#
# POR QUÉ SE LEE DE `Config.app_language` Y NO SE ENHEBRA DESDE EL REQUEST:
# el idioma de interfaz YA vive en `Config.app_language` — lo escribe
# `useI18n.setLang` en el frontend en CADA cambio de idioma, y ya lo leen
# `app/ai/personalities.py` (`_display_lang`) y `api/endpoints/voice.py`
# (`_DEFAULT_VOICE_BY_LANG`). Enhebrarlo desde cada request obligaría a tocar
# el schema `ChatRequest`, el contrato CONGELADO `AgentTask` y ~6 archivos del
# pipeline del TIE, cuando una lectura central cubre TODOS los caminos del chat
# (streaming/no-streaming, TIE camino corto, Gateway, legacy) porque todos pasan
# por `chat_service.build_system_prompt`. Aithera es monousuario con un único
# idioma activo a la vez (Principio 6, CLAUDE.md §18), así que un ajuste GLOBAL
# es correcto — y mucho menos invasivo. El único desfase teórico (cambiar de
# idioma y mandar un mensaje en el mismo milisegundo, antes de que el
# `setConfig` best-effort persista) se autocorrige al mensaje siguiente.
from __future__ import annotations

from typing import Optional

_LANG_KEY = "app_language"
_SUPPORTED = {"es", "en", "fr", "pt"}

# Nombre natural del idioma para la instrucción del prompt (en su propia lengua:
# un modelo obedece mejor "responde en English" que "responde en inglés").
_NAMES = {
    "es": "español",
    "en": "English",
    "fr": "français",
    "pt": "português",
}


def ui_language() -> Optional[str]:
    """Código de 2 letras del idioma de interfaz elegido (`Config.app_language`),
    o `None` si el usuario no ha elegido ninguno todavía (primer arranque antes
    del onboarding). Best-effort: nunca lanza — un fallo de BD equivale a "sin
    idioma elegido", que mantiene el comportamiento histórico (inferir del
    mensaje)."""
    try:
        from app.db.database import SessionLocal
        from app.db.models import Config

        db = SessionLocal()
        try:
            row = db.query(Config).filter(Config.key == _LANG_KEY).first()
            if not row or not row.value:
                return None
            code = row.value.split("-")[0].lower()
            return code if code in _SUPPORTED else None
        finally:
            db.close()
    except Exception:
        return None


def ui_language_name() -> Optional[str]:
    """Nombre natural del idioma de interfaz elegido (`"English"`, `"español"`…),
    o `None` si no hay ninguno. Para instrucciones a medida (p.ej. el planner
    quiere localizar solo los `goal`, no dar una directiva de chat completa)."""
    code = ui_language()
    return _NAMES[code] if code else None


# Instrucción de idioma ESCRITA EN EL PROPIO IDIOMA OBJETIVO. Es la diferencia
# entre que un modelo local (llama3, etc.) la obedezca o la ignore: una orden en
# español ("responde en inglés") enterrada en un system prompt 95% español la
# pierde el modelo, que ancla al idioma dominante del contexto. La MISMA orden en
# el idioma objetivo, y colocada la PRIMERA, es una señal que el modelo sigue.
# Por eso `build_system_prompt` la pone al principio de todo. Bilingüe (nativa +
# refuerzo en español) para máxima obediencia con modelos débiles.
_DIRECTIVES = {
    "en": (
        "CRITICAL — RESPONSE LANGUAGE: You MUST write EVERY response entirely in "
        "English, regardless of the language the user writes in or the language of "
        "any documents, emails or data they share. English is the language the user "
        "chose for the app and it OVERRIDES the language of their message. Never "
        "reply in Spanish or any other language. (Responde SIEMPRE en inglés.)"
    ),
    "fr": (
        "CRITIQUE — LANGUE DE RÉPONSE : tu DOIS écrire CHAQUE réponse entièrement en "
        "français, quelle que soit la langue de l'utilisateur ou celle des documents, "
        "e-mails ou données qu'il partage. Le français est la langue choisie pour "
        "l'application et elle PRIME sur la langue du message. Ne réponds jamais en "
        "espagnol ni dans une autre langue. (Responde SIEMPRE en francés.)"
    ),
    "pt": (
        "CRÍTICO — IDIOMA DA RESPOSTA: DEVES escrever CADA resposta inteiramente em "
        "português, independentemente do idioma em que o utilizador escreva ou do "
        "idioma de quaisquer documentos, e-mails ou dados que partilhe. O português é "
        "o idioma escolhido para a aplicação e PREVALECE sobre o idioma da mensagem. "
        "Nunca respondas em espanhol nem noutro idioma. (Responde SIEMPRE en portugués.)"
    ),
    "es": (
        "IDIOMA DE RESPUESTA: responde SIEMPRE en español, sin importar en qué idioma "
        "escriba el usuario o en qué idioma estén los documentos, emails o datos que "
        "te pase. Es el idioma elegido para la aplicación y tiene prioridad sobre el "
        "idioma del mensaje."
    ),
}


def language_directive() -> str:
    """Instrucción de idioma para añadir a un system prompt, o `""` si no hay
    idioma elegido. Escrita EN EL IDIOMA OBJETIVO (no en español) y pensada para
    ir la PRIMERA del prompt: es lo que hace que un modelo local la obedezca en
    vez de anclar al idioma dominante del resto del contexto."""
    code = ui_language()
    if not code:
        return ""
    return _DIRECTIVES.get(code, _DIRECTIVES["es"])
