# app/core/grounding.py — ¿el texto afirma algo que de verdad ha pasado? (S2·S6, doc 34)
#
# POR QUÉ EN `core/` Y NO EN `tie/` (desviación deliberada del diseño de doc 34,
# que lo situaba en `app/tie/grounding.py`): lo usan TRES módulos distintos —
# `tie/responder.py`, `orchestrator/consolidator.py` y `services/chat_service.py`.
# Los internos de `app.tie` no se pueden importar desde fuera del TIE
# (disciplina modular, doc 16, vigilada por `test_module_boundaries.py`), así
# que vivir ahí obligaría a exponerlo en el barrel del TIE y a que el
# orquestador y los servicios dependieran del TIE para una función de texto que
# no tiene nada de TIE. `app/core/` es la capa compartida — el mismo sitio que
# `strings.py`, `events.py` y `language.py`, que resuelven lo mismo.
#
# EL PROBLEMA QUE CIERRA: el grounding de A-1 (S1) vive DENTRO de `toolloop.py`
# — protege la capa que ejecuta. Pero por encima hay tres capas que REESCRIBEN
# esos hechos en prosa (`responder`, `consolidator`) o que responden sin
# ejecutar nada (el camino corto), y ninguna comprobaba lo que escribía. Los
# dos fallos reales:
#
#   · 25-jul: el email SE ENVIÓ (tool_call con message_id) y el chat dijo
#     "está preparado pero NO se ha enviado, necesito tu confirmación". No
#     había ninguna aprobación pendiente: el texto se inventó.
#   · 27-jul (campaña 01): el camino corto —que no tiene NINGUNA herramienta—
#     citó 5 fuentes web que nunca visitó, describió una estructura de
#     carpetas inventada y resumió un documento sin leerlo.
#
# POR QUÉ AQUÍ Y ASÍ: el prompt de `consolidator` ya decía literalmente "No
# inventes nada que no esté en los resultados" y no sirvió. Una instrucción no
# es una comprobación. Esto son funciones PURAS, deterministas, 0 LLM: se
# ejecutan sobre el texto YA generado, justo antes de entregarlo.
#
# NO es un "verificador" ni una capa nueva (doc 34 §7, "lo que deliberadamente
# NO propongo"): es un módulo de funciones que las capas existentes llaman —
# la tercera aplicación del MISMO patrón de A-1, no una tercera arquitectura.
#
# SESGO DELIBERADO A NO MOLESTAR: solo se detectan verbos que implican una
# herramienta o un efecto en el mundo (enviar, crear, leer un archivo, visitar
# una web). Los verbos cognitivos ("he pensado", "he entendido", "he visto que
# preguntas por…") JAMÁS disparan: un falso positivo añade una nota innecesaria
# a una respuesta correcta, y eso también erosiona la confianza.
from __future__ import annotations

import re
import unicodedata

from app.core.strings import t as _t

# Cuánto texto se mira al final para detectar una promesa sin cumplir.
_TAIL_CHARS = 250

# Objetos "de conversación": si el verbo cae sobre uno de estos, NO es una
# acción sobre el mundo. "He leído tu mensaje" es cortesía, no una tool.
_SELF_REFERENTIAL = (
    "tu mensaje", "tu pregunta", "tu peticion", "tu consulta", "lo que dices",
    "lo que me dices", "lo que preguntas", "tu texto", "tu comentario",
    "your message", "your question", "your request", "what you said", "what you wrote",
)
_SELF_REF_WINDOW = 30   # caracteres tras el verbo donde se busca el objeto

# Acción REALIZADA sobre el mundo/sistema. Cada patrón implica una herramienta:
# si no hay tool_call detrás, es falso por construcción.
_COMPLETED_ACTION = re.compile(
    r"\b("
    r"he (enviado|creado|leido|visitado|guardado|abierto|escrito|borrado|eliminado|"
    r"descargado|ejecutado|revisado|consultado|buscado|encontrado)"
    r"|hemos (enviado|creado|guardado)"
    r"|se ha (enviado|creado|guardado|escrito|borrado|descargado|ejecutado)"
    r"|(?:el |un )?(?:email|correo|mensaje) (?:ya )?(?:ha sido |fue )?enviad[oa]"
    r"|(?:el |un )?(?:archivo|fichero|documento) (?:ya )?(?:ha sido |fue )?(creado|guardado|escrito)"
    r"|acabo de (enviar|crear|leer|guardar|abrir|escribir|borrar|descargar|ejecutar|buscar)"
    r"|i (sent|created|read|visited|saved|opened|wrote|deleted|downloaded|executed|searched|found)"
    r"|i have (sent|created|read|visited|saved|opened|written|deleted|downloaded|executed)"
    r"|(?:the )?(?:email|message|file|document) (?:has been |was )?(sent|created|saved|written)"
    r")\b",
    re.IGNORECASE,
)

# El texto dice que falta el visto bueno del usuario. Si NO hay ningún gate
# abierto de verdad, esto es exactamente la mentira del 25-jul.
_PENDING_APPROVAL = re.compile(
    r"("
    r"(falta|necesito|espero|esperando|pendiente de)\s+(?:tu|su)\s+"
    r"(confirmacion|aprobacion|permiso|visto bueno|autorizacion|ok)"
    r"|(?:queda|esta) pendiente de (?:tu |su )?(aprobacion|confirmacion|permiso)"
    r"|(?:necesito|requiere) que (?:lo )?(confirmes|apruebes|autorices)"
    r"|(?:waiting for|pending|needs) your (approval|confirmation|permission|ok)"
    r"|i need (?:you to )?(confirm|approve|authorize)"
    r")",
    re.IGNORECASE,
)

# Promesa de acción que NUNCA se cumple: el texto termina anunciando algo y
# ahí se acaba (caso T02/H1 de la campaña 01 — "voy a intentar leerlo…" y el
# stream muere sin ejecutar ni avisar).
_FUTURE_ACTION = re.compile(
    r"\b("
    r"(voy a|vamos a|deja(?:me)?(?: que)?|permiteme)\s+"
    r"(leer|intentar|comprobar|revisar|buscar|abrir|mirar|consultar|verificar|analizar|acceder)"
    r"|(?:ahora|enseguida) (?:mismo )?(?:lo )?(leo|reviso|busco|abro|compruebo|consulto)"
    r"|(?:let me|i'?ll|i will) (read|try|check|look|search|open|verify|access)"
    r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# [NEW-7, doc 34] Evidencia que SOLO una herramienta puede producir
# ---------------------------------------------------------------------------
# EL HUECO QUE CIERRA: los patrones de arriba buscan un VERBO delator ("he
# leído", "he ejecutado"). La fabricación real del 28-jul no usó ninguno —
# presentó los datos y ya está:
#
#     "Total de archivos .py en backend/app/tie: 7"
#     ```python
#     from .config_loader import load_config      ← no existe en el archivo real
#     ```
#
# Sin verbo, `claims_completed_action` no dispara y la respuesta salía limpia,
# con pinta de verdad verificada. Este detector mira la FORMA de la respuesta:
# en el camino corto no hay NINGUNA herramienta, así que presentar el contenido
# de un archivo concreto, un listado de directorio o un recuento de ficheros es
# falso por construcción, se use el verbo que se use.
#
# CONSERVADOR A PROPÓSITO: cada señal exige que el texto se refiera a algo
# CONCRETO del sistema del usuario (una ruta, un nombre con extensión). Un
# bloque de código de ejemplo ("escríbeme una función que…") no dispara: no hay
# archivo real al que atribuirlo. La duplicación de la lista de extensiones con
# `tie/action_intent.py` es deliberada — `app/core` no puede importar de
# `app.tie` (dirección de dependencia, doc 16), y son datos, no lógica.
_EVIDENCE_EXTENSIONS = (
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".txt", ".csv",
    ".pdf", ".docx", ".xlsx", ".html", ".css", ".yml", ".yaml", ".sql",
    ".log", ".ini", ".cfg", ".toml", ".sh", ".bat", ".ps1",
)

# "Total de archivos .py: 7", "hay 12 ficheros", "contiene 3 archivos"
_FILE_COUNT = re.compile(
    r"("
    r"(total|numero|cantidad|hay|contiene|existen|encontre|son)\b[^\n]{0,40}?"
    r"\b\d+\b[^\n]{0,20}?(archivos?|ficheros?|files?|carpetas?|folders?)"
    r"|(archivos?|ficheros?|files?)\b[^\n]{0,30}?:\s*\d+"
    r"|(total|number|count) of[^\n]{0,30}?\b\d+"
    r")",
    re.IGNORECASE,
)

# Una línea de listado: opcional viñeta/número, luego un nombre con extensión
# o una ruta. Tres o más seguidas ⇒ es un `ls`, no una frase.
# `[^\S\n]` = espacio horizontal: si se usara `\s` la coincidencia se comería
# el salto de línea y la viñeta de la línea SIGUIENTE, contando 2 donde hay 4.
# El terminador va en lookahead por el mismo motivo: mira, no consume.
_LISTING_LINE = re.compile(
    r"^[^\S\n]*(?:[-*+•]|\d+[.)])?[^\S\n]*[\w./\\-]{2,}(?:"
    + "|".join(re.escape(e) for e in _EVIDENCE_EXTENSIONS)
    + r")[^\S\n]*(?=[-—:(]|$)",
    re.IGNORECASE | re.MULTILINE,
)

_CODE_FENCE = re.compile(r"```")

# Ruta concreta: `app/tie`, `backend\app`, `C:\Users\...`
_CONCRETE_PATH = re.compile(r"[A-Za-z0-9_.-]+[/\\][A-Za-z0-9_.-]+")

# Cita de fuentes web: dos o más enlaces markdown a http(s).
_MD_LINK = re.compile(r"\[[^\]\n]{1,80}\]\(https?://[^)\s]+\)")


# ---------------------------------------------------------------------------
# [NEW-4, doc 34] Rendición explícita en un nodo que quedó "Hecha"
# ---------------------------------------------------------------------------
# EL HUECO QUE CIERRA: `_validate_result` (T3 §3.4.7, `tie/executor.py`) valida
# barato y determinista — "¿corrió una tool con éxito? ¿hay salida con forma?"
# — nunca "¿el nodo consiguió su objetivo?". Un nodo puede correr `list_dir`
# con éxito Y responder, literalmente: "No puedo completar este objetivo: las
# herramientas disponibles en este paso NO incluyen ninguna de búsqueda web ni
# navegador" — el `list_dir` da forma a la salida, así que el nodo queda DONE
# con el check verde, contradiciendo su propio texto (verificación en vivo,
# 2026-07-28). Es honestidad a nivel de texto y mentira a nivel de estado.
#
# CONSERVADOR A PROPÓSITO (mismo criterio que el resto del módulo): solo
# dispara ante una rendición EXPLÍCITA y DECLARATIVA cerca del principio de la
# respuesta — un nodo que cuenta lo que sí logró y de pasada menciona algo que
# no pudo hacer NO es una rendición, es un resultado parcial honesto y debe
# quedar DONE. Mirar solo la CABECERA evita ese falso positivo.
_SURRENDER_HEAD_CHARS = 200

# [2026-08-02] El OBJETO de la rendición se factoriza: el caso real que se
# escapó era "No he podido completar EL OBJETIVO DEL PASO" — el patrón exigía
# el demostrativo ("este objetivo") y el artículo no colaba. Sigue exigiéndose
# un objeto de la lista (nunca un "no puedo completar" a secas): eso es lo que
# separa una rendición TOTAL de un resultado parcial honesto ("no he podido
# completar la sección de X, pero el resto está").
_SURRENDER_OBJ = r"(?:este|el|la|esta) (?:objetivo|tarea|paso|encargo)|esto"

_SURRENDER = re.compile(
    r"\b("
    rf"no puedo completar (?:{_SURRENDER_OBJ})"
    rf"|no puedo cumplir (?:{_SURRENDER_OBJ})"
    # "no he podido / no pude / no he conseguido / no he logrado …" — las
    # formas en PASADO, que son las que de verdad usa un nodo al informar de
    # lo que ya intentó. Sin ellas, el nodo quedaba en verde ("Hecha")
    # diciendo por escrito que había fallado, y el resumen final de la misión
    # lo contaba como éxito: la contradicción exacta que reportó el usuario.
    rf"|no (?:he podido|pude|he conseguido|consegui|he logrado|logre) (?:completar|cumplir|realizar|terminar) (?:{_SURRENDER_OBJ})"
    r"|no consegui completar"
    r"|no ha sido posible completar"
    r"|no fue posible completar"
    r"|no dispongo de (?:las )?herramientas (?:necesarias|adecuadas|disponibles)"
    r"|las herramientas disponibles[^\n]{0,60}no incluyen"
    r"|i cannot complete this"
    r"|i can't complete this"
    r"|i couldn't complete this"
    r"|i could not complete this"
    r"|i was unable to complete"
    r"|unable to complete this"
    r")\b",
    re.IGNORECASE,
)


def is_surrender(text: str) -> bool:
    """¿El texto es una rendición EXPLÍCITA — el nodo dice, de entrada, que NO
    pudo cumplir su objetivo? Se busca solo en la CABECERA
    (`_SURRENDER_HEAD_CHARS`): una rendición real lo dice de entrada, no la
    menciona de pasada tras haber contado lo que sí logró. Determinista, 0
    LLM — pensado para `_validate_result` (T3), no para el camino corto."""
    if not text or not text.strip():
        return False
    norm = _normalize(text[:_SURRENDER_HEAD_CHARS])
    return bool(_SURRENDER.search(norm))


def _normalize(text: str) -> str:
    """minúsculas + sin acentos, para que 'He leído' y 'he leido' coincidan
    igual. Mismo criterio que `intents._normalize` (no se importa de allí para
    no acoplar el clasificador con esto; son 4 líneas)."""
    t = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def claims_completed_action(text: str) -> bool:
    """¿El texto afirma haber HECHO algo que exigiría una herramienta?

    Devuelve False para los verbos cognitivos y para las acciones que caen
    sobre la propia conversación ("he leído tu mensaje"): esas no necesitan
    ninguna tool y marcarlas sería ruido."""
    norm = _normalize(text)
    for m in _COMPLETED_ACTION.finditer(norm):
        after = norm[m.end():m.end() + _SELF_REF_WINDOW]
        if any(obj in after for obj in _SELF_REFERENTIAL):
            continue        # es cortesía conversacional, no una acción real
        return True
    return False


def claims_pending_approval(text: str) -> bool:
    """¿El texto dice que algo espera el visto bueno del usuario?"""
    return bool(_PENDING_APPROVAL.search(_normalize(text)))


def claims_future_action(text: str) -> bool:
    """¿El texto anuncia una acción y se queda ahí, sin cumplirla?

    Dos condiciones, las dos necesarias — un "voy a leer el archivo" seguido de
    lo que dice el archivo NO es una promesa incumplida, es narrar el proceso:
      1. El anuncio está en la COLA del texto (lo último que se dijo).
      2. Después del anuncio no hay ninguna afirmación de acción realizada."""
    norm = _normalize(text)
    last = None
    for m in _FUTURE_ACTION.finditer(norm):
        last = m
    if last is None:
        return False
    if last.start() < len(norm) - _TAIL_CHARS:
        return False        # el anuncio quedó lejos del final: hubo más respuesta
    return not claims_completed_action(norm[last.end():])


def presents_unverifiable_evidence(text: str) -> bool:
    """¿El texto presenta datos que SOLO una herramienta podría haber obtenido?

    No mira verbos: mira la forma. Contenido de un archivo concreto, un listado
    de directorio, un recuento de ficheros o una lista de fuentes web citadas.
    En el camino corto —que no tiene herramientas— cualquiera de estas cosas es
    inventada, aunque el texto no diga en ningún momento "lo he leído".

    Conservador: un bloque de código suelto NO basta (puede ser un ejemplo
    pedido); hace falta además una ruta o un nombre de archivo concreto al que
    el texto lo atribuya."""
    if not text or not text.strip():
        return False

    tiene_ruta = bool(_CONCRETE_PATH.search(text))
    tiene_nombre = any(ext in text.lower() for ext in _EVIDENCE_EXTENSIONS)
    concreto = tiene_ruta or tiene_nombre

    # 1 · Código presentado como contenido de un archivo real del usuario.
    if concreto and len(_CODE_FENCE.findall(text)) >= 2:
        return True
    # 2 · Listado de directorio (3+ líneas que son nombres de archivo).
    if len(_LISTING_LINE.findall(text)) >= 3:
        return True
    # 3 · Recuento de archivos sobre algo concreto.
    if concreto and _FILE_COUNT.search(_normalize(text)):
        return True
    # 4 · Bibliografía web: 2+ enlaces citados como fuentes visitadas.
    if len(_MD_LINK.findall(text)) >= 2:
        return True
    return False


def honesty_note() -> str:
    """La coletilla honesta para el camino corto (i18n). Función y no
    constante: el idioma se resuelve en cada llamada, como el resto de `_t`."""
    return _t("grounding.no_tools_note")


def fabrication_note() -> str:
    """Aviso FUERTE: el texto no solo afirma algo, presenta datos concretos que
    no pueden ser reales. Merece un lenguaje distinto al de la coletilla suave —
    aquí lo probable no es un matiz, es que todo lo anterior esté mal."""
    return _t("grounding.fabricated_note")


def note_for(text: str) -> str | None:
    """La nota que le corresponde a este texto en el CAMINO CORTO, o None si no
    necesita ninguna. Punto ÚNICO de decisión, para que la versión con
    streaming (que solo puede añadir al final) y la que no (que reescribe el
    texto entero) no puedan divergir."""
    if not text or not text.strip():
        return None
    if presents_unverifiable_evidence(text):
        return fabrication_note()
    if claims_completed_action(text) or claims_future_action(text):
        return honesty_note()
    return None


def with_honesty_note(text: str) -> str:
    """Añade la nota al final si el texto la necesita; si no, lo devuelve tal
    cual. Pensado para el CAMINO CORTO, que no ejecuta ninguna herramienta: ahí
    cualquier afirmación de acción es falsa por construcción, sin necesidad de
    mirar `tool_calls`."""
    nota = note_for(text)
    return f"{text.rstrip()}\n\n{nota}" if nota else text
