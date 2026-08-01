# app/tie/progress.py — el rastro de actividad EN VIVO de una misión
#
# EL PROBLEMA QUE RESUELVE (petición del usuario, 2026-08-02): mientras una
# misión trabaja, el chat solo decía "Entendido, me pongo con ello" y después
# se quedaba mudo hasta la respuesta final — con un latido genérico cada 15 s
# (S4) que no cuenta NADA. El detalle existía, pero solo en Mission Control, es
# decir, en otra pantalla y después. El usuario quiere lo mismo que ve aquí, en
# Claude: una línea corta por cada cosa que se está haciendo, según pasa.
#
# POR QUÉ UNA COLA Y NO EL BUS DE EVENTOS (`app/core/events.py`): el bus es
# global y de suscripción por nombre — para esto haría falta filtrar por misión
# a mano en cada handler y arriesgarse a que el rastro de una misión se cuele en
# el chat de otra (dos misiones concurrentes es lo normal, doc 23). Una cola
# ligada al CONTEXTO de la tarea resuelve el enrutado por construcción:
# `contextvars` se copia al crear la task (`ensure_future`), así que todo lo que
# corre dentro de una misión —toolloop, planner, executor— escribe en SU cola y
# en ninguna otra, sin pasarse referencias por 6 capas de firmas.
#
# REGLA DE ORO: esto es OBSERVACIÓN. `emit()` no bloquea nunca (`put_nowait`
# sobre una cola acotada; si se llena, se tira la línea más vieja), no lanza
# nunca, y sin cola ligada es un no-op. Un fallo aquí jamás puede afectar al
# trabajo real — mismo criterio que la telemetría (doc 31) y que `events.emit`.
from __future__ import annotations

import asyncio
import contextvars
from typing import AsyncIterator, Optional

# Tope de líneas pendientes de drenar. Generoso para una misión normal y aun así
# acotado: si el consumidor se va (el usuario cierra la pestaña), la cola no
# puede crecer sin límite.
_MAX_PENDING = 200

_current: contextvars.ContextVar[Optional["asyncio.Queue[str]"]] = contextvars.ContextVar(
    "aithera_progress_queue", default=None,
)


def emit(line: str) -> None:
    """Anota una línea del rastro. Best-effort absoluto: sin cola ligada (una
    misión de fondo, un test, el AE) no hace nada."""
    if not line:
        return
    try:
        q = _current.get()
        if q is None:
            return
        if q.full():
            # Preferimos perder lo VIEJO: el rastro es un "qué está pasando
            # ahora", no un histórico (para eso está Mission Control).
            try:
                q.get_nowait()
            except Exception:
                return
        q.put_nowait(line[:180])
    except Exception:
        pass


def bind() -> "asyncio.Queue[str]":
    """Liga una cola nueva al contexto ACTUAL y la devuelve.

    Se llama en el generador del stream ANTES de lanzar la tarea de la misión:
    `ensure_future` copia el contexto, así que la tarea (y todo lo que llame)
    hereda esta cola."""
    q: "asyncio.Queue[str]" = asyncio.Queue(maxsize=_MAX_PENDING)
    _current.set(q)
    return q


def unbind() -> None:
    """Suelta la cola del contexto actual (fin del turno)."""
    try:
        _current.set(None)
    except Exception:
        pass


async def drain_until(task: "asyncio.Future", queue: "asyncio.Queue[str]", *,
                      heartbeat_s: int) -> AsyncIterator[tuple]:
    """Va emitiendo `("activity", línea)` según aparecen, mientras `task` siga en
    vuelo, y `("status", "sigo trabajando")` si pasa `heartbeat_s` sin ninguna.

    SUSTITUYE a `_heartbeat_until` (S4 · NEW-2) allá donde hay rastro: el latido
    genérico deja de hacer falta cuando de verdad hay algo que contar, pero se
    conserva para los ratos legítimamente callados (una sola llamada al LLM que
    tarda un minuto). Igual que aquél, NO consume el resultado: el caller hace
    `await task` después.

    ORDEN DE LAS COMPROBACIONES, y no es un detalle: la línea recibida se
    atiende ANTES que el fin de la tarea. Es lo que garantiza que una RÁFAGA
    final (varias líneas emitidas seguidas justo antes de terminar, sin ningún
    await por medio) salga entera — el bucle sigue dando vueltas mientras queden
    líneas, y solo sale cuando la cola está vacía Y la tarea ha terminado.
    Invertir el orden perdería siempre el final del trabajo, que es justo lo que
    el usuario quiere ver."""
    espera = heartbeat_s if heartbeat_s and heartbeat_s > 0 else None
    while True:
        getter = asyncio.ensure_future(queue.get())
        done, _ = await asyncio.wait({getter, task}, timeout=espera,
                                     return_when=asyncio.FIRST_COMPLETED)
        if getter in done:
            yield ("activity", getter.result())
            continue
        # La línea no llegó: o acabó la tarea, o venció el latido. `getter` no
        # está resuelto, así que cancelarlo no puede perder ninguna línea.
        getter.cancel()
        if task in done:
            return
        yield ("status", _still_working())


def _still_working() -> str:
    from app.core.strings import t

    return t("status.still_working")


# ---------------------------------------------------------------------------
# Cómo se NARRA una herramienta: "acción + objeto corto"
# ---------------------------------------------------------------------------
# Decisión del usuario (2026-08-02): ni solo el verbo ("leyendo un archivo" —
# no distingue dos lecturas seguidas) ni el resultado completo ("leído X · 12.400
# caracteres" — ruidoso). Acción + SOBRE QUÉ, y punto.
#
# El mapa es DELIBERADAMENTE explícito en vez de derivarse del catálogo de
# tools: el nombre técnico de una acción (`get_text`, `list_dir`) no es lo que
# se le enseña a una persona. Una tool nueva sin entrada aquí no rompe nada —
# cae en `act.generic`, que ya es legible.
#   (tool_id, action) → (clave i18n, nombre del parámetro del que sale el objeto)
_PHRASES: dict[tuple, tuple] = {
    ("filesystem", "read_file"): ("act.reading", "path"),
    ("filesystem", "write_file"): ("act.writing", "path"),
    ("filesystem", "list_dir"): ("act.listing", "path"),
    ("filesystem", "create_dir"): ("act.writing", "path"),
    ("filesystem", "delete_file"): ("act.deleting", "path"),
    ("filesystem", "file_exists"): ("act.listing", "path"),
    ("document", "read_pdf"): ("act.reading", "path"),
    ("document", "read_docx"): ("act.reading", "path"),
    ("document", "read_xlsx"): ("act.reading", "path"),
    ("document", "write_docx"): ("act.writing", "path"),
    ("document", "write_xlsx"): ("act.writing", "path"),
    ("search", "search_web"): ("act.searching_web", "query"),
    ("search", "search_news"): ("act.searching_web", "query"),
    ("search", "search_images"): ("act.searching_web", "query"),
    ("search", "search_videos"): ("act.searching_web", "query"),
    ("browser", "open_url"): ("act.browsing", "url"),
    ("browser", "new_tab"): ("act.browsing", "url"),
    ("browser", "google_search"): ("act.searching_web", "query"),
    ("browser", "get_text"): ("act.reading", "url"),
    ("browser", "get_html"): ("act.reading", "url"),
    ("browser", "download_file"): ("act.downloading", "url"),
    ("shell", "run"): ("act.running", "command"),
    ("powershell", "run_script"): ("act.running", "script"),
    ("email", "list_inbox_preview"): ("act.email_reading", None),
    ("email", "search_emails"): ("act.email_reading", None),
    ("email", "get_email"): ("act.email_reading", None),
    ("email", "create_draft"): ("act.email_writing", "to"),
    ("email", "send_email"): ("act.email_writing", "to"),
    ("memory", "search_memory"): ("act.memory_read", "query"),
    ("memory", "save_memory"): ("act.memory_write", None),
    ("memory", "update_memory"): ("act.memory_write", None),
    ("download", "download_url"): ("act.downloading", "url"),
    # Las consultas sobre la propia Aithera llevan el sustantivo YA traducido en
    # la plantilla: "Consultando list_projects" era técnico y feo.
    ("aithera", "list_projects"): ("act.self_projects", None),
    ("aithera", "project_status"): ("act.self_projects", None),
    ("aithera", "list_agents"): ("act.self_agents", None),
    ("aithera", "list_rules"): ("act.self_rules", None),
    ("aithera", "create_agent"): ("act.self_write", "name"),
    ("aithera", "update_agent"): ("act.self_write", "name"),
    ("aithera", "assign_tools"): ("act.self_write", "__action__"),
    ("aithera", "create_task"): ("act.self_write", "title"),
    ("aithera", "update_task"): ("act.self_write", "title"),
    ("aithera", "create_project"): ("act.self_write", "name"),
    ("aithera", "create_milestone"): ("act.self_write", "name"),
    ("aithera", "create_rule"): ("act.self_write", "name"),
    ("aithera", "create_cron_job"): ("act.self_write", "name"),
}

# Tools cuyo objeto es una RUTA: se muestra solo el nombre del archivo. Una ruta
# absoluta de Windows ocupa toda la línea y no aporta nada que el usuario no sepa.
_PATH_TOOLS = {"filesystem", "document", "download"}

# Familias enteras que se narran igual sin enumerar cada acción.
_FAMILY: dict[str, str] = {
    "browser": "act.browser_acting",
    "git": "act.git",
    "calendar": "act.calendar",
    "desktop": "act.desktop",
}


def describe(tool_id: str, action: str, params: Optional[dict] = None) -> str:
    """La línea del rastro para una llamada a herramienta. Nunca lanza: ante
    cualquier cosa rara devuelve algo legible (narrar no puede romper nada)."""
    try:
        from app.core.strings import t

        params = params or {}
        entry = _PHRASES.get((tool_id, action))
        if entry:
            key, param = entry
            if param is None:                     # frase sin objeto ("Revisando el correo")
                return t(key)
            obj = action if param == "__action__" else _short(params.get(param), tool_id)
            if not obj:
                # El parámetro esperado no vino: "Leyendo " a secas no dice nada.
                # Se busca cualquier otro objeto útil antes de rendirse al genérico.
                obj = _first_useful(params, tool_id)
            return t(key, obj=obj) if obj else t("act.generic_noobj", tool=tool_id)
        fam = _FAMILY.get(tool_id)
        if fam:
            return t(fam, obj=action)
        obj = _first_useful(params, tool_id)
        return t("act.generic", tool=tool_id, obj=obj) if obj else t("act.generic_noobj", tool=tool_id)
    except Exception:
        return f"{tool_id}.{action}"


def _short(value, tool_id: str) -> str:
    """Objeto corto y legible: nombre de archivo, dominio, o texto recortado.

    El acortado de RUTA solo se aplica a las tools cuyo objeto ES una ruta
    (`_PATH_TOOLS`). Hacerlo por "¿tiene barras?" destrozaba un comando de
    shell: `python -m pytest tests/ -q` se quedaba en " -q"."""
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    if s.startswith("http"):
        resto = s.split("://", 1)[-1]
        s = resto.split("/", 1)[0] or resto
    elif tool_id in _PATH_TOOLS:
        s = s.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1] or s
    return s if len(s) <= 60 else s[:57] + "…"


def _first_useful(params: dict, tool_id: str) -> str:
    for k in ("query", "path", "url", "name", "title", "text", "command"):
        if params.get(k):
            return _short(params[k], tool_id)
    return ""
