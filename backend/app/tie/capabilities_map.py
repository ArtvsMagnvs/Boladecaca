# app/tie/capabilities_map.py — lo que Aithera sabe hacer, en lenguaje humano
# (V1.0, doc 23 R6, cierra Δ9)
#
# EL PROBLEMA QUE RESUELVE: si le preguntas a Aithera "¿qué sabes hacer?", el
# `DEFAULT_SYSTEM_PROMPT` de `chat_service.py` no dice nada al respecto — el
# modelo o inventa una respuesta genérica, o se queda corto, o (peor) empieza a
# describir su propia arquitectura porque es lo único que "sabe" de sí misma.
#
# LA REGLA DE DISEÑO (doc 23 R6, no negociable): este mapa se GENERA desde el
# código real en cada llamada (con caché, ver abajo) — NUNCA es una lista
# escrita a mano. `tool_manager.list_tools()` ya es la fuente de verdad de la
# UI y de la validación de `allowed_tools`; aquí se recorre esa MISMA fuente.
# Una lista a mano se queda obsoleta en la siguiente sesión de desarrollo; ésta
# no puede, porque no hay "la lista" — hay una función que la recalcula.
#
# CRITERIO DE CIERRE #3 (doc 23): "añadir una tool nueva → aparece en el mapa
# SIN TOCAR el mapa". Por eso hay dos niveles:
#   - `_TOOL_BLURBS`: una frase cuidada, en español llano, para las tools que
#     YA conocemos — mejor UX que un genérico.
#   - el genérico (`_generic_blurb`): para cualquier `tool_id` que NO esté en
#     el diccionario. Nunca se omite una tool por no estar curada.
# El bucle que arma el mapa es el que decide qué tools existen (vía
# `tool_manager.list_tools`), no el diccionario — así una tool #15 aparece sola.
#
# FRONTERA DE CONFIDENCIALIDAD (la otra mitad del criterio de cierre): el mapa
# describe CAPACIDADES, nunca implementación. Ni aquí ni en `_TOOL_BLURBS` se
# escribe una ruta de archivo, un nombre de módulo (`app.`, `.py`), un motor
# concreto (Playwright, ChromaDB, DPAPI) ni un esquema de BD. Al usuario le
# importa QUÉ puede pedir, no CÓMO está construido — `tool.description` (la
# que ve el desarrollador en el catálogo interno) SÍ nombra esas cosas a
# propósito, así que nunca se usa tal cual aquí.
from __future__ import annotations

import time
from typing import Optional

# Presupuesto de caracteres del bloque que se inyecta en el system prompt. Un
# mapa de 91 acciones sin resumir se comería el contexto de cada mensaje del
# chat — esto es una GUÍA para el modelo, no un manual de referencia. El
# recorte respeta líneas completas (ver `_build`): nunca corta a media frase.
MAX_CHARS = 1500
# [C1b] Tope APARTE para la línea de servicios MCP conectados: se añade encima
# de MAX_CHARS (ver el final de `_build`), así que necesita su propio límite
# para que veinte servidores no hinchen el system prompt sin control.
_MCP_LINE_MAX = 400

# Cuánto se cachea el mapa entre recálculos. El catálogo de tools es estático
# tras el arranque (se registran una vez en `_register_default_tools`), así
# que el TTL es generoso — no hay nada que cambie entre un mensaje y el
# siguiente salvo que se instale una tool nueva en caliente, algo que hoy no
# ocurre en producción.
_CACHE_TTL_S = 3600.0
_cache: dict[str, tuple[float, str]] = {}


# ---------------------------------------------------------------------------
# Frases curadas por tool_id — en español llano, sin jerga de implementación.
# Ausente de esta lista != invisible: ver `_generic_blurb`.
# ---------------------------------------------------------------------------
_TOOL_BLURBS: dict[str, str] = {
    "email": "leer, buscar y enviar tu correo, y gestionar respuestas automáticas",
    "calendar": "leer y crear eventos en tu calendario, y comprobar tu disponibilidad",
    # [C·WEB-4] Mencionar los flujos completos, pero MUY corto: este bloque
    # entra en el system prompt de cada mensaje y `MAX_CHARS` recorta líneas
    # enteras — una frase larga aquí tira la última categoría del mapa.
    "browser": "navegar por internet de verdad: abrir páginas, hacer clic, escribir, "
               "leer lo que hay en pantalla, y llevar flujos enteros (compra, "
               "cita, research) parando antes de pagar o confirmar",
    "search": "buscar en la web (páginas, noticias, imágenes, vídeos)",
    "filesystem": "leer, escribir y organizar archivos y carpetas en tu ordenador",
    "shell": "ejecutar comandos de desarrollo (Python, git, npm...) con una lista "
             "cerrada de programas permitidos",
    "powershell": "ejecutar tus propios scripts guardados, nunca comandos sueltos",
    "git": "consultar y operar repositorios de código (estado, historial, commits)",
    "process": "ver qué programas tienes abiertos, y abrir o cerrar aplicaciones",
    "desktop": "controlar el ratón y el teclado, y leer lo que hay en tu pantalla "
               "(siempre con tu permiso)",
    "download": "descargar archivos de internet a tu ordenador",
    "model": "gestionar los modelos de IA que tienes instalados en local",
    "memory": "buscar y guardar cosas en tu memoria — lo que ya sabe de ti y tus proyectos",
    "secrets": "guardar contraseñas y claves de forma segura para usarlas cuando haga falta",
    "document": "leer PDF y crear o leer documentos de Word (.docx) y hojas de Excel (.xlsx)",
    "aithera": "gestionar tus proyectos, tareas, agentes y automatizaciones por ti",
}

# Categorías para agrupar el mapa (más legible que una lista plana de 14
# líneas). Un tool_id sin categoría curada cae en "Otras".
_CATEGORIES: list[tuple[str, tuple[str, ...]]] = [
    ("comunicarme y organizarte", ("email", "calendar")),
    ("moverme por internet", ("browser", "search", "download")),
    ("tu ordenador", ("filesystem", "shell", "powershell", "git", "process", "desktop", "document")),
    ("mi propia inteligencia", ("model", "memory", "secrets")),
    ("organizar tu trabajo", ("aithera",)),
]


def _generic_blurb(tool_name: str, n_actions: int) -> str:
    """Frase segura para una tool que no está en `_TOOL_BLURBS` — el caso que
    demuestra el criterio de cierre #3. Solo usa `tool.name` (ya pensado para
    humanos, p.ej. "Browser Tool") y un conteo; nunca `tool.description`
    completa, que sí puede nombrar detalles internos."""
    clean = tool_name.replace(" Tool", "").strip() or tool_name
    return f"{clean.lower()} ({n_actions} acciones disponibles)"


def _automation_line() -> Optional[str]:
    """Una frase sobre lo que el Automation Engine sabe disparar, generada
    desde `DEFAULT_ACTIONS` — no una lista a mano. Best-effort: si el AE no
    está disponible en este proceso, se omite sin romper el mapa."""
    try:
        from app.automation import DEFAULT_ACTIONS
    except Exception:
        return None

    labels = {
        "telegram_message": "avisarte por Telegram",
        "email_summary": "mandarte un resumen de tu email",
        "chat_query": "responderte algo por su cuenta",
        "agent_task": "lanzar una tarea a uno de tus agentes",
        "workspace": "crear o actualizar tareas en tus proyectos",
    }
    known = [labels[k] for k in DEFAULT_ACTIONS if k in labels]
    if not known:
        return None
    return ("También puedo programar avisos y tareas automáticas (a una hora fija, "
            "o cuando pase algo) — por ejemplo: " + ", ".join(known) + ".")


def _mcp_line() -> Optional[str]:
    """[C1b, doc 42 §4] Los servicios externos que el usuario ha conectado por
    MCP. Van en su propia línea y NO por el bucle de categorías de arriba: sus
    tools ya aparecerían en el cajón "Además" con un genérico de conteo
    ("mcp · github (14 acciones disponibles)"), que no dice nada — lo que
    importa es que el chat sepa DECIR "puedo consultar tu GitHub".

    Best-effort: sin servidores conectados (el caso por defecto), no añade
    nada y el mapa queda idéntico al de siempre."""
    try:
        from app.tie import mcp_command

        servicios = mcp_command.connected()
    except Exception:
        return None
    if not servicios:
        return None
    frases = [f"{nombre}" + (f" ({desc})" if desc else "")
              for _tid, nombre, desc in servicios]
    linea = ("También tienes conectados estos servicios externos, y puedo usarlos "
             "cuando la petición encaje con ellos: " + "; ".join(frases) + ".")
    # Tope propio: con muchos servidores conectados esta línea podría comerse
    # el presupuesto entero y dejar sin sitio a lo que Aithera sabe hacer de
    # base (`_build` le reserva espacio, así que sin este tope lo reservado
    # crecería sin límite).
    return linea[:_MCP_LINE_MAX] if len(linea) > _MCP_LINE_MAX else linea


def _build() -> str:
    """Recorre el catálogo REAL y arma el texto. Nunca lanza: ante cualquier
    fallo, un mapa vacío es preferible a tumbar el chat por esto."""
    try:
        from app.tools import tool_manager

        tools = tool_manager.tie_catalog()  # [P1] accesor único, ver tool_manager.tie_catalog()
    except Exception:
        return ""
    if not tools:
        return ""

    by_id = {t["tool_id"]: t for t in tools}
    used: set[str] = set()
    lines: list[str] = []

    for category, ids in _CATEGORIES:
        phrases = []
        for tid in ids:
            t = by_id.get(tid)
            if t is None:
                continue
            used.add(tid)
            blurb = _TOOL_BLURBS.get(tid) or _generic_blurb(t["name"], len(t["actions"]))
            phrases.append(blurb)
        if phrases:
            lines.append(f"- Para {category}: " + "; ".join(phrases) + ".")

    # [C1b] Los servidores MCP conectados se cuentan aparte, con su nombre y
    # su descripción real — y se marcan como "usados" para que el cajón
    # genérico de abajo no los repita con un conteo de acciones sin sentido
    # ("mcp · github (14 acciones disponibles)" no dice nada).
    mcp = _mcp_line()
    if mcp:
        from app.automation import permission_service

        used.update(t["tool_id"] for t in tools
                    if t["tool_id"].startswith(permission_service.MCP_TOOL_PREFIX))

    # Cualquier tool NO cubierta por una categoría (la nueva del criterio #3)
    # entra en un cajón final, genérico pero visible.
    resto = [t for t in tools if t["tool_id"] not in used]
    if resto:
        frases = [_TOOL_BLURBS.get(t["tool_id"]) or _generic_blurb(t["name"], len(t["actions"]))
                  for t in resto]
        lines.append("- Además: " + "; ".join(frases) + ".")

    auto = _automation_line()
    if auto:
        lines.append(f"- {auto}")

    # Recorte por LÍNEAS completas, nunca a media frase: una línea cortada a
    # mitas de camino confunde más de lo que informa (y podría, por accidente,
    # dejar una palabra técnica suelta que sin el resto de la frase pierde su
    # matiz humano). Si ni la primera línea cabe, se devuelve solo la cabecera.
    header = "Esto es lo que puedo hacer de verdad (no solo hablar de ello):"
    kept: list[str] = []
    total = len(header)
    for line in lines:
        if total + 1 + len(line) > MAX_CHARS:
            break
        kept.append(line)
        total += 1 + len(line)
    # [C1b] La línea de servicios MCP se añade ENCIMA del presupuesto base, no
    # dentro. Medido: el mapa base ya ocupa 1449 de los 1500, así que meterla
    # dentro tenía DOS finales malos — o desaparecía en silencio (el modo de
    # fallo que PU8 encontró con la última categoría), o desplazaba a una
    # categoría nativa (verificado: expulsaba "organizar tu trabajo"). Ninguno
    # vale: lo que el usuario conecta se SUMA a lo que Aithera ya sabía hacer,
    # no lo sustituye. El coste extra solo lo paga quien tiene MCP conectado, y
    # está acotado por `_MCP_LINE_MAX`.
    if mcp:
        kept.append(f"- {mcp}")
    return header + ("\n" + "\n".join(kept) if kept else "")


def summary(*, force: bool = False) -> str:
    """El bloque listo para inyectar en el system prompt. Cacheado
    (`_CACHE_TTL_S`) para que preguntar "¿qué sabes hacer?" cien veces no
    recorra el catálogo cien veces — es puramente descriptivo, no depende del
    mensaje del usuario, así que cachear no pierde nada."""
    now = time.monotonic()
    cached = _cache.get("summary")
    if not force and cached and (now - cached[0]) < _CACHE_TTL_S:
        return cached[1]
    text = _build()
    _cache["summary"] = (now, text)
    return text


def invalidate() -> None:
    """[C1b] Tira la caché. La llama `mcp_command.invalidate_cache()` cuando el
    usuario conecta o desconecta un servidor MCP: con un TTL de una hora, el
    cambio no se notaría hasta mucho después de haberlo hecho."""
    _cache.pop("summary", None)
