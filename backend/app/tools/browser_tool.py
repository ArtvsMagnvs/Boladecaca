# backend/app/tools/browser_tool.py
#
# V1.0/1.1 (Tools): navegador real (Playwright/Chromium), la pieza que
# "automatiza el 80% de Internet" (peticion del usuario, 2026-07-18). Una
# unica sesion de navegador persistente en el proceso del backend, con varias
# pestanas direccionables por id -- igual de espiritu que el Download Tool
# (tareas de fondo referenciables), pero aqui el estado es "pestanas abiertas".
#
# Import LAZY de playwright: si el paquete o el binario de Chromium
# (`playwright install chromium`) no estan instalados, la tool falla con un
# error claro en el primer uso, en vez de tumbar el arranque del backend.
#
# Seguridad:
# - VISIBLE por defecto (2026-07-19): si Aithera navega por ti, tienes que
#   poder verlo y tomar el control. `BROWSER_HEADLESS=true` lo oculta.
# - Descargas/subidas de archivo pasan por la MISMA validacion de paths que
#   FilesystemTool (solo dentro de HOME).
# - click/type/download/upload REQUIEREN confirmacion (interactuan de verdad
#   con una pagina real); navegar/leer NO (equivalente a "lectura").
# - Conectada al permiso `browser.use` (doc 20 A3b) -- antes reservado con
#   available=False, activado ahora que la tool existe de verdad.
#
# Acciones: open_url, new_tab, close_tab, google_search, click, type, scroll,
# wait_for_element, download_file, upload_file, screenshot, get_html, get_text,
# open_in_default_browser, play_media.
#
# [B·WEB-1, doc 32] open_in_default_browser/play_media NO usan Playwright: abren
# la URL en el navegador REAL del sistema (el mismo que el usuario ya tiene
# logueado, con autoplay y cookies resueltas). Es la solucion al "Google
# bloquea la navegacion automatizada" para el caso de uso mas comun -- poner
# musica o un video -- sin pelear con el muro de consentimiento ni con la
# deteccion de headless. play_media resuelve la URL con la tool 'search'
# (Brave/SerpAPI), NUNCA con 'browser.google_search' (bloqueada) ni con
# scraping por regex (fragil).

import asyncio
import base64
import uuid
import webbrowser
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.core.logging_config import get_system_logger
from .base import BaseTool
from .filesystem_tool import _resolve_user_path, _is_path_allowed
from .search_tool import _search
from . import vision_click

logger = get_system_logger("tools.browser")

# [B·WEB-2 + C·WEB-3, doc 32] SET-OF-MARK. Numera los elementos con los que se
# puede interactuar y les dibuja una caja con su numero encima, para que el
# modelo elija POR INDICE en vez de estimar pixeles. Es la tecnica que da su
# fiabilidad a browser-use/Skyvern y es mucho mas precisa que las coordenadas:
# el indice apunta a un elemento REAL del DOM.
#
# UNA sola implementacion para las DOS acciones que la usan (`find_and_click` de
# B·WEB-2 y `page_state` de C·WEB-3): si se duplicara, una de las dos se
# quedaria atras (patron LOG-1, tres veces visto ya en este proyecto).
#
# [C·WEB-3 · spike] Las heuristicas de interactividad estan copiadas de
# `browser_use/dom/serializer/clickable_elements.py::ClickableElementDetector`
# (leido en el spike, 2026-08-05) y traducidas a JS plano. browser-use las
# resuelve con CDP + arbol de accesibilidad + snapshot (por eso arrastra
# `cdp_use`); aqui se consigue ~el mismo poder de deteccion con
# `getComputedStyle` + atributos, que es lo que Playwright ya nos da gratis.
# Las senales, en su orden: (1) tags interactivos, (2) roles ARIA
# interactivos, (3) manejadores de evento / tabindex / contenteditable,
# (4) `cursor: pointer` —el mejor indicio para los divs clicables de React/Vue—,
# (5) tamano de icono (10-50px) con senales, (6) clases/id de busqueda.
# Se DESCARTAN los deshabilitados y los `aria-hidden`, igual que ellos.
#
# Solo se marca lo VISIBLE en el viewport: un elemento fuera de pantalla no se
# puede clicar de todas formas, y meterlo en la lista solo confunde al modelo.
_SET_OF_MARK_JS = """(opciones) => {
  const cfg = opciones || {};
  const MAX = cfg.max || 60;
  const PINTAR = cfg.paint !== false;
  const INTERACTIVE_TAGS = new Set(['button','input','select','textarea','a','details',
                                    'summary','option','optgroup']);
  const INTERACTIVE_ROLES = new Set(['button','link','menuitem','option','radio','checkbox',
                                     'tab','textbox','combobox','slider','spinbutton',
                                     'search','searchbox','switch','menuitemcheckbox',
                                     'menuitemradio']);
  const EVENT_ATTRS = ['onclick','onmousedown','onmouseup','onkeydown','onkeyup'];
  const BUSQUEDA = ['search','magnify','lookup','buscar','query'];

  document.querySelectorAll('.__aithera_mark').forEach(n => n.remove());

  const esInteractivo = (el, st, r) => {
    const tag = el.tagName.toLowerCase();
    if (tag === 'html' || tag === 'body') return false;
    if (el.disabled) return false;
    if (el.getAttribute('aria-hidden') === 'true') return false;
    if (INTERACTIVE_TAGS.has(tag)) return true;
    const role = (el.getAttribute('role') || '').toLowerCase();
    if (INTERACTIVE_ROLES.has(role)) return true;
    if (el.isContentEditable) return true;
    if (el.hasAttribute('tabindex')) return true;
    for (const a of EVENT_ATTRS) if (el.hasAttribute(a)) return true;
    if (st.cursor === 'pointer') return true;
    const idc = ((el.id || '') + ' ' + (el.className || '')).toLowerCase();
    if (BUSQUEDA.some(s => idc.includes(s))) return true;
    if (r.width >= 10 && r.width <= 50 && r.height >= 10 && r.height <= 50) {
      if (el.getAttribute('aria-label') || el.getAttribute('data-action')) return true;
    }
    return false;
  };

  // Texto util, en el MISMO orden de prioridad que browser-use
  // (`get_meaningful_text_for_llm`): value, aria-label, title, placeholder, alt,
  // y por ultimo el texto visible.
  const textoDe = (el) => {
    const cand = [el.value, el.getAttribute('aria-label'), el.getAttribute('title'),
                  el.getAttribute('placeholder'), el.getAttribute('alt'), el.innerText];
    for (const c of cand) {
      if (typeof c === 'string' && c.trim()) return c.trim().replace(/\\s+/g, ' ').slice(0, 120);
    }
    return '';
  };

  const vw = window.innerWidth, vh = window.innerHeight;
  const marks = [];
  const vistos = new Set();
  for (const el of document.querySelectorAll('*')) {
    if (marks.length >= MAX) break;
    const r = el.getBoundingClientRect();
    if (r.width < 6 || r.height < 6) continue;
    if (r.bottom < 0 || r.right < 0 || r.top > vh || r.left > vw) continue;
    const st = window.getComputedStyle(el);
    if (st.visibility === 'hidden' || st.display === 'none' || st.opacity === '0') continue;
    if (!esInteractivo(el, st, r)) continue;
    // Un boton dentro de un enlace (o similar) se marcaria dos veces en el
    // mismo sitio: nos quedamos con el primero de cada rectangulo.
    const clave = Math.round(r.left) + ':' + Math.round(r.top) + ':' +
                  Math.round(r.width) + ':' + Math.round(r.height);
    if (vistos.has(clave)) continue;
    vistos.add(clave);

    const idx = marks.length;
    if (PINTAR) {
      const box = document.createElement('div');
      box.className = '__aithera_mark';
      box.style.cssText = 'position:fixed;z-index:2147483647;pointer-events:none;' +
        'border:2px solid #E8B95E;box-sizing:border-box;' +
        'left:' + r.left + 'px;top:' + r.top + 'px;' +
        'width:' + r.width + 'px;height:' + r.height + 'px;';
      const tagEl = document.createElement('div');
      tagEl.className = '__aithera_mark';
      tagEl.textContent = String(idx);
      tagEl.style.cssText = 'position:fixed;z-index:2147483647;pointer-events:none;' +
        'background:#E8B95E;color:#000;font:bold 11px monospace;padding:0 3px;' +
        'left:' + r.left + 'px;top:' + Math.max(0, r.top - 13) + 'px;';
      document.body.appendChild(box);
      document.body.appendChild(tagEl);
    }
    marks.push({
      index: idx,
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || null,
      role: el.getAttribute('role') || el.tagName.toLowerCase(),
      text: textoDe(el),
      editable: (el.tagName.toLowerCase() === 'input' && !['checkbox','radio','submit','button','file'].includes((el.getAttribute('type')||'text').toLowerCase()))
                || el.tagName.toLowerCase() === 'textarea' || el.isContentEditable,
      center: [Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2)]
    });
  }
  return {
    marks: marks,
    truncated: marks.length >= MAX,
    scroll: {
      y: Math.round(window.scrollY),
      can_down: (window.scrollY + vh) < (document.body.scrollHeight - 4),
      can_up: window.scrollY > 4
    }
  };
}"""

_CLEAR_MARKS_JS = "() => document.querySelectorAll('.__aithera_mark').forEach(n => n.remove())"


def _serialize_marks(marks: List[Dict[str, Any]]) -> str:
    """Los elementos en el formato que ve el modelo — `[i]<tag ...>texto</tag>`,
    el mismo de browser-use (`llm_representation`), que es compacto y
    autoexplicativo: el indice delante, y el texto util dentro.

    Funcion PURA: se puede probar sin navegador."""
    lineas = []
    for m in marks:
        attrs = ""
        if m.get("type"):
            attrs += f' type="{m["type"]}"'
        if m.get("role") and m["role"] != m.get("tag"):
            attrs += f' role="{m["role"]}"'
        lineas.append(f'[{m["index"]}]<{m.get("tag", "el")}{attrs}>{m.get("text", "")}</{m.get("tag", "el")}>')
    return "\n".join(lineas)


def _launch_default_browser(url: str) -> bool:
    """Abre `url` en el navegador REAL por defecto del sistema (no Playwright).

    `webbrowser` es la abstraccion estandar de Python: en Windows llama a
    `os.startfile` por debajo (el navegador ya logueado del usuario, con
    autoplay y cookies resueltas), y en macOS/Linux usa el comando del sistema
    equivalente -- una sola linea que cubre las 3 plataformas sin tener que
    ramificar por `sys.platform`. Aislada en su propia funcion module-level
    para que los tests puedan sustituirla sin tocar nada mas (nunca se abre un
    navegador real en CI)."""
    return webbrowser.open(url)

# Estado del navegador -- un unico proceso.
_playwright = None
_browser = None              # modo respaldo (ephemeral): Browser de Playwright
_persistent_context = None   # modo normal: BrowserContext PERSISTENTE (perfil)

# [Auditoria v0.9.5, F-1] SESION POR MISION. Antes las pestanas vivian en un
# unico dict global y `_current_tab` era una sola variable: con
# ORCH_MAX_CONCURRENT=3, dos misiones que usaran el navegador a la vez se
# pisaban la pestana activa (la mision A navegaba, la B clicaba en la pagina de
# A). Cada mision tiene su propio grupo de pestanas y su pestana activa.
#
# [2026-07-23, peticion del usuario] PERFIL PERSISTENTE + CHROME REAL: el
# navegador ya no es el Chromium "de test" con perfil de usar-y-tirar — es el
# Google Chrome instalado (channel="chrome") sobre un perfil PROPIO de Aithera
# que sobrevive entre misiones y reinicios (%APPDATA%/Aithera/chrome-profile).
# Consecuencias buscadas: la sesion de Google se inicia UNA vez y queda; cada
# muro de cookies aceptado queda aceptado PARA SIEMPRE en ese sitio (la mitad
# del arreglo definitivo de consentimiento es esta persistencia).
#
# El aislamiento F-1 cambia de forma con el perfil persistente: las misiones
# comparten el MISMO contexto (las cookies/sesiones compartidas son el
# objetivo), y lo que se aisla por mision son las PESTANAS y la pestana
# activa. Si el perfil no puede abrirse (lock huerfano, etc.) se degrada al
# modo antiguo: navegador efimero con un contexto por mision.
#
# Clave "default" = sin mision (chat directo, tests): mismo comportamiento de
# siempre, cero regresion.
_DEFAULT_SESSION = "default"


class _Session:
    """Pestanas + pestana activa de UNA mision. `owns_context=True` solo en el
    modo respaldo (contexto efimero propio que hay que cerrar al terminar)."""

    def __init__(self, context: Any, owns_context: bool = False) -> None:
        self.context = context
        self.owns_context = owns_context
        self.pages: Dict[str, Any] = {}
        self.current_tab: Optional[str] = None


_sessions: Dict[str, _Session] = {}

# [S9, doc 34 §10, reabre F-1] `_ensure_browser()` no tenía ningún lock: dos
# misiones concurrentes que llegaban con `_browser is None and
# _persistent_context is None` pasaban AMBAS el guard y lanzaban DOS
# `launch_persistent_context()` sobre el MISMO perfil -- Chrome bloquea el
# segundo proceso y el pisoteo de los globals (uno machaca al otro) dejaba a
# las DOS misiones con una referencia a un contexto muerto -> `TargetClosedError`
# en ambas (reproducido en vivo, campaña 01, `T06-R-D5-browser-concurrente`).
# Un único lock de módulo sirve para las dos carreras (lanzar el navegador Y
# crear una `_Session` nueva) -- no son operaciones que compitan entre sí.
_launch_lock = asyncio.Lock()


def _browser_mode() -> str:
    """[2026-07-23] Modo elegido por el usuario en Ajustes → Conexiones →
    Búsqueda web: "aithera" (perfil dedicado, persistente, recomendado) o
    "user" (el Chrome HABITUAL del usuario, su sesión real). Valor en claro en
    Config (no es un secreto). Nunca lanza: sin BD legible → "aithera"
    (el modo seguro por defecto)."""
    try:
        from app.db.database import SessionLocal
        from app.db.models import Config

        db = SessionLocal()
        try:
            row = db.query(Config).filter(Config.key == "browser_mode").first()
            return row.value if row and row.value in ("aithera", "user") else "aithera"
        finally:
            db.close()
    except Exception:
        return "aithera"


def _user_chrome_profile_dir() -> Optional[str]:
    """La carpeta "User Data" REAL de Chrome del usuario (Windows). None si no
    se puede localizar — entonces no se intenta el modo "user" a ciegas."""
    import os
    base = os.getenv("LOCALAPPDATA")
    if not base:
        return None
    path = os.path.join(base, "Google", "Chrome", "User Data")
    return path if os.path.isdir(path) else None


# ---------------------------------------------------------------------------
# [S9b, doc 34] Un navegador MUERTO se relanza — antes envenenaba el proceso
# ---------------------------------------------------------------------------
# EL FALLO QUE CIERRA (verificado en vivo, 2026-07-28): `_ensure_browser()`
# comprobaba `is not None`, no si el navegador seguía VIVO. En cuanto el
# `_persistent_context` moría por cualquier causa externa (el usuario cerró esa
# ventana de Chrome, el proceso se cayó, Windows lo mató), la variable global
# seguía apuntando al cadáver PARA SIEMPRE: el guard daba "ya está lanzado", no
# se relanzaba nunca, y TODAS las misiones posteriores morían con
# `TargetClosedError` hasta reiniciar el backend entero. El lock de S9 arregló
# la carrera entre misiones concurrentes, pero dejó esto debajo — y es peor,
# porque no hace falta concurrencia para caer en ello.
#
# DOS MECANISMOS, porque uno solo no basta:
#   1. Chequeo barato ANTES (`_alive`): descarta el cadáver evidente sin coste.
#   2. Reintento en el PUNTO DE USO (`_get_page`): el estado real de un proceso
#      externo solo se conoce al usarlo — entre el chequeo y la llamada puede
#      morir. Si Playwright dice "target closed", se resetea y se relanza UNA
#      vez. Es el mismo patrón que ya cura una pestaña muerta, un nivel arriba.
_CLOSED_MARKERS = ("targetclosederror", "has been closed", "target closed",
                   "browser has been closed", "connection closed")


def _looks_closed(exc: BaseException) -> bool:
    """¿Esta excepción dice 'el navegador ya no está'? Por texto y no por tipo
    a propósito: Playwright lanza `TargetClosedError` pero también `Error` a
    secas con el mismo mensaje según por dónde se rompa."""
    msg = f"{type(exc).__name__} {exc}".lower()
    return any(m in msg for m in _CLOSED_MARKERS)


def _alive(ctx_or_browser: Any) -> bool:
    """Chequeo BARATO de vivacidad. Conservador al revés que el resto del
    módulo: ante la duda devuelve True (que falle en el punto de uso, donde hay
    reintento) — declarar muerto un navegador sano cerraría las pestañas del
    usuario sin motivo."""
    if ctx_or_browser is None:
        return False
    try:
        conectado = getattr(ctx_or_browser, "is_connected", None)
        if callable(conectado):
            return bool(conectado())
        # Un BrowserContext persistente no tiene `is_connected`; su `browser`
        # sí (puede ser None en algunas versiones, y entonces no se sabe).
        br = getattr(ctx_or_browser, "browser", None)
        if br is not None and callable(getattr(br, "is_connected", None)):
            return bool(br.is_connected())
        _ = ctx_or_browser.pages      # lanza si el objeto ya está inutilizable
        return True
    except Exception:
        return False


async def _reset_browser_globals() -> None:
    """Tira TODO el estado de navegador para que el próximo `_ensure_browser()`
    relance de cero. Incluye `_sessions`: sus contextos apuntan al navegador
    muerto, así que conservarlas solo propagaría el error a la misión
    siguiente. Se llama SIEMPRE con `_launch_lock` tomado."""
    global _playwright, _browser, _persistent_context
    for obj in (_persistent_context, _browser):
        try:
            if obj is not None:
                await obj.close()
        except Exception:
            pass          # ya estaba muerto: cerrarlo es cortesía, no requisito
    try:
        if _playwright is not None:
            await _playwright.stop()
    except Exception:
        pass
    _playwright = None
    _browser = None
    _persistent_context = None
    _sessions.clear()
    logger.info("[browser] estado reiniciado: el navegador se relanzará en la "
                "próxima llamada")


def _browser_ready() -> bool:
    """¿Hay un navegador lanzado Y vivo? Lo que el guard debería haber
    comprobado desde el principio."""
    if _persistent_context is not None:
        return _alive(_persistent_context)
    if _browser is not None:
        return _alive(_browser)
    return False


async def _ensure_browser():
    global _playwright, _browser, _persistent_context
    if _browser_ready():
        return
    # [S9] Fast-path SIN lock arriba (ya lanzado -> no pagar el lock en el
    # camino caliente); pero para lanzar de verdad, todo bajo el lock con
    # RE-CHEQUEO dentro (double-checked locking): mientras esta corrutina
    # esperaba el lock, otra puede haber terminado de lanzar ya.
    async with _launch_lock:
        if _browser_ready():
            return
        # [S9b] Si había algo lanzado pero MUERTO, hay que limpiarlo antes de
        # relanzar: si no, `_persistent_context` seguiría apuntando al cadáver.
        if _persistent_context is not None or _browser is not None:
            await _reset_browser_globals()
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise RuntimeError(
                "Playwright no esta instalado (pip install playwright && "
                "playwright install chromium)"
            ) from e
        _playwright = await async_playwright().start()

        # [Fix 2026-07-19] VISIBLE, no headless: si Aithera navega por ti, tienes
        # que poder mirarlo y tomar el control. Ademas headless se bloquea como
        # sospechoso en muchos sitios (documentado en CLAUDE.md §8).
        headless = settings.BROWSER_HEADLESS
        # Sin la barra "Chrome esta siendo controlado por software automatizado":
        # es el navegador DEL USUARIO trabajando para el, no un banco de pruebas.
        launch_kwargs = dict(headless=headless, ignore_default_args=["--enable-automation"])

        mode = _browser_mode()

        # [2026-07-23] Modo "user": el Chrome HABITUAL del usuario, con su sesion
        # real. NUNCA se sustituye en silencio por el perfil dedicado si esto
        # falla (mismo criterio que ExplicitModelUnfit/ExplicitModelUnavailable
        # del MEL: el usuario eligio esto A PROPOSITO, si no funciona se le dice
        # POR QUE, no se le cambia el navegador sin avisar). La causa mas comun de
        # fallo es que su Chrome ya este abierto -- Chrome bloquea un segundo
        # proceso sobre el mismo perfil.
        if mode == "user":
            user_dir = _user_chrome_profile_dir()
            if user_dir is None:
                raise RuntimeError(
                    "No se encontró tu perfil de Chrome en este equipo. Cambia a "
                    "'Chrome dedicado de Aithera' en Ajustes → Conexiones → Búsqueda web."
                )
            try:
                _persistent_context = await _playwright.chromium.launch_persistent_context(
                    user_dir, channel="chrome", **launch_kwargs,
                )
                return
            except Exception as e:
                raise RuntimeError(
                    "No se pudo abrir tu Chrome habitual con tu sesión real. Lo más probable "
                    "es que ya lo tengas abierto — Chrome no permite que dos procesos usen el "
                    "mismo perfil a la vez. Ciérralo del todo y reintenta, o cambia a "
                    "'Chrome dedicado de Aithera' en Ajustes → Conexiones → Búsqueda web. "
                    f"({type(e).__name__}: {e})"
                ) from e

        # Modo "aithera" (por defecto): cadena de degradacion honesta (cada nivel
        # se intenta en orden, el fallo de uno pasa al siguiente):
        #   1) Chrome REAL + perfil persistente de Aithera   ← lo pedido
        #   2) Chromium bundled + perfil persistente         (no hay Chrome)
        #   3) Chromium efimero (modo antiguo)               (perfil bloqueado)
        profile_dir = settings.BROWSER_PROFILE_DIR
        for channel in ([settings.BROWSER_CHANNEL] if settings.BROWSER_CHANNEL != "chromium" else []) + [None]:
            try:
                import os
                os.makedirs(profile_dir, exist_ok=True)
                _persistent_context = await _playwright.chromium.launch_persistent_context(
                    profile_dir, **({**launch_kwargs, "channel": channel} if channel else launch_kwargs),
                )
                return
            except Exception:
                continue
        try:
            _browser = await _playwright.chromium.launch(headless=headless)
        except Exception as e:
            raise RuntimeError(
                f"no se pudo lanzar el navegador (¿falta 'playwright install chromium'?): {e}"
            ) from e


async def _get_session(session_id: Optional[str]) -> _Session:
    """La sesion de navegador de una mision. Con perfil persistente: contexto
    COMPARTIDO (sesiones/cookies del usuario) y pestanas propias por mision.
    En modo respaldo: BrowserContext efimero propio (comportamiento antiguo).

    [S9] La CREACIÓN de una `_Session` nueva (en modo respaldo, un
    `_browser.new_context()` real) va bajo el MISMO `_launch_lock` que
    `_ensure_browser()` -- dos misiones concurrentes con el mismo `sid` (o
    ambas cayendo en `_DEFAULT_SESSION`) tenían la misma carrera en pequeño:
    las dos pasaban `sess is None`, las dos creaban un contexto, y la segunda
    asignación pisaba a la primera en `_sessions[sid]` (contexto huérfano,
    nunca cerrado). Fast-path sin lock si ya existe (camino caliente)."""
    await _ensure_browser()
    sid = session_id or _DEFAULT_SESSION
    sess = _sessions.get(sid)
    # [S9b] Una sesión que apunta al contexto COMPARTIDO de un navegador ya
    # relanzado es basura: su `context` es el cadáver anterior. Se descarta y
    # se recrea contra el contexto vivo. (En modo respaldo cada sesión tiene su
    # propio contexto efímero, así que solo se comprueba que siga vivo.)
    if sess is not None:
        vigente = (sess.context is _persistent_context if _persistent_context is not None
                   else _alive(sess.context))
        if vigente:
            return sess
        _sessions.pop(sid, None)
        sess = None
    async with _launch_lock:
        sess = _sessions.get(sid)   # re-chequeo: pudo crearla otra corrutina
        if sess is None:
            if _persistent_context is not None:
                sess = _Session(_persistent_context, owns_context=False)
            else:
                sess = _Session(await _browser.new_context(), owns_context=True)
            _sessions[sid] = sess
    return sess


def _session_id_of(params: Dict[str, Any]) -> Optional[str]:
    """La mision duena de esta llamada. El toolloop la inyecta en los params
    (`_session`) desde la autoridad de la mision; sin ella se usa "default"."""
    sid = params.get("_session") or params.get("mission_id")
    return str(sid) if sid else None


async def _get_page(tab_id: Optional[str], session_id: Optional[str] = None):
    """Resuelve la pestana DENTRO de la sesion de esta mision: la pedida, o la
    activa, o crea una nueva si no hay ninguna abierta todavia.

    [S9] Si la pestaña resuelta ya está CERRADA (el usuario la cerró a mano,
    o quedó un `TargetClosedError` residual tras un cierre externo) NO se
    devuelve el handle muerto -- eso reventaba la siguiente llamada real de
    Playwright con la misma excepción, tumbando la misión entera. Se descarta
    de `sess.pages` y se crea una nueva: la misión se autocura en vez de
    fallar por una pestaña que ya no existe."""
    sess = await _get_session(session_id)
    tid = tab_id or sess.current_tab
    if tid and tid in sess.pages:
        page = sess.pages[tid]
        try:
            dead = page.is_closed()
        except Exception:
            dead = True
        if not dead:
            return tid, page
        sess.pages.pop(tid, None)
        if sess.current_tab == tid:
            sess.current_tab = None

    # [S9b] Abrir una pestaña es el primer sitio donde se descubre que el
    # navegador entero murió. El chequeo previo de `_ensure_browser` puede
    # haber pasado (murió entre medias, o `_alive` no pudo saberlo): aquí sí se
    # sabe con certeza. Un ÚNICO reintento tras relanzar — si el segundo
    # también falla, el error sube y la misión falla honestamente, sin bucle.
    for intento in (1, 2):
        try:
            page = await sess.context.new_page()
            break
        except Exception as e:
            if intento == 2 or not _looks_closed(e):
                raise
            logger.warning(f"[browser] el navegador estaba cerrado ({type(e).__name__}); "
                           f"relanzando y reintentando una vez")
            async with _launch_lock:
                await _reset_browser_globals()
            await _ensure_browser()
            sess = await _get_session(session_id)
    new_id = uuid.uuid4().hex[:10]
    sess.pages[new_id] = page
    sess.current_tab = new_id
    return new_id, page


async def close_session(session_id: str) -> bool:
    """Cierra la sesion de navegador de una mision. Con perfil persistente
    cierra SOLO las pestanas de esa mision (el perfil/contexto sigue vivo —
    ahi estan la sesion de Google y los consentimientos aceptados); en modo
    respaldo cierra tambien su contexto efimero. La llama el executor al
    terminar una mision."""
    sess = _sessions.pop(session_id, None)
    if sess is None:
        return False
    if sess.owns_context:
        try:
            await sess.context.close()
        except Exception:
            pass
    else:
        for page in list(sess.pages.values()):
            try:
                await page.close()
            except Exception:
                pass
    return True


# ---------------------------------------------------------------------------
# [Auditoria v0.9.5, A-3] Muros de consentimiento (cookies / GDPR)
# ---------------------------------------------------------------------------
# EL FALLO QUE CIERRA: "abre YouTube y pon la cancion X" cargaba el muro de
# cookies de Google, `goto` devolvia success (el DOM habia cargado: el muro ES
# el DOM), y el modelo clicaba a ciegas selectores del contenido real que estaba
# tapado. La mision se daba por hecha sin que sonara nada.
#
# Selectores de los CMP mayoritarios + los formularios de consentimiento de
# Google/YouTube. Orden: de mas especifico a mas generico. Best-effort total:
# cada intento tiene timeout corto y su propio try/except — si no hay muro (el
# caso normal) el coste es ~0 y NUNCA rompe la navegacion.
_CONSENT_SELECTORS = (
    "#onetrust-accept-btn-handler",                        # OneTrust
    "#didomi-notice-agree-button",                          # Didomi
    'button[mode="primary"][aria-label*="ccept"]',          # Quantcast / TCF
    "button.fc-cta-consent",                                # Google Funding Choices
    'form[action*="consent"] button',                       # consent.google / consent.youtube
    'button[aria-label="Aceptar todo"]',
    'button[aria-label="Accept all"]',
    'button[aria-label="Aceptar todas"]',
    '[data-testid="uc-accept-all-button"]',                 # Usercentrics
    "#L2AGLb",                                              # Google "Acepto"
    "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",  # Cookiebot
    "#truste-consent-button",                               # TrustArc
    "button#sp-cc-accept",                                  # Amazon
    ".cmplz-accept",                                        # Complianz (WordPress)
    'button[data-cookiebanner="accept_button"]',            # Facebook/Meta
)
_CONSENT_TIMEOUT_MS = 1200
_CONSENT_MAX_TRIES = 3

# [2026-07-23, v2] Capa de TEXTO: cuando el CMP no esta en el catalogo, se
# busca cualquier boton/enlace visible cuyo texto accesible sea una frase de
# aceptacion (ES/EN/FR/DE/PT). Cubre los CMP caseros, que son la cola larga
# que rompia misiones. Frases EXACTAS o de arranque, cortas — jamas un "ok"
# suelto ni un "configurar/rechazar" (mejor no tocar que tocar mal).
_CONSENT_TEXTS = (
    "aceptar todo", "aceptar todas", "aceptar y continuar", "aceptar cookies",
    "aceptar y cerrar", "acepto las cookies", "aceptar", "acepto", "de acuerdo",
    "entendido", "consentir",
    "accept all", "accept all cookies", "allow all", "allow all cookies",
    "accept cookies", "accept & continue", "accept and continue", "i accept",
    "i agree", "agree all", "agree", "accept", "got it", "allow cookies",
    "tout accepter", "alles akzeptieren", "alle akzeptieren", "aceitar tudo",
    "aceitar todos",
)

# [2026-07-23, v2] APRENDIZAJE PERSISTENTE POR DOMINIO (peticion del usuario:
# "que aprenda de forma definitiva"). Cuando cualquier capa cierra un muro, se
# guarda {dominio → estrategia} en el perfil de Aithera; la proxima visita a
# ese dominio prueba PRIMERO lo aprendido (via rapida). Sumado al perfil
# persistente (un consentimiento aceptado no vuelve a aparecer en ese sitio),
# el muro de un sitio solo puede costar tiempo UNA vez en la vida del perfil.
_learned_consent: Optional[Dict[str, Dict[str, str]]] = None


def _consent_store_path():
    import os
    return os.path.join(settings.BROWSER_PROFILE_DIR, "consent_learned.json")


def _load_learned() -> Dict[str, Dict[str, str]]:
    global _learned_consent
    if _learned_consent is None:
        import json
        try:
            with open(_consent_store_path(), encoding="utf-8") as f:
                _learned_consent = json.load(f)
        except Exception:
            _learned_consent = {}
    return _learned_consent


def _save_learned(domain: str, kind: str, value: str) -> None:
    """Best-effort: aprender jamas puede romper la navegacion."""
    import json
    import os
    try:
        learned = _load_learned()
        learned[domain] = {"kind": kind, "value": value}
        os.makedirs(settings.BROWSER_PROFILE_DIR, exist_ok=True)
        with open(_consent_store_path(), "w", encoding="utf-8") as f:
            json.dump(learned, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def _domain_of(page) -> str:
    try:
        from urllib.parse import urlparse
        host = (urlparse(page.url).netloc or "").lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def _consent_contexts(page) -> list:
    """La pagina + sus iframes (Google/YouTube meten el muro en un iframe que
    `page.locator` no ve — fix A-3 2026-07-21)."""
    contexts = [page]
    try:
        contexts.extend(page.frames)   # incluye la principal otra vez; no pasa nada
    except Exception:
        pass
    return contexts


async def _try_css(page, selector: str) -> bool:
    for ctx in _consent_contexts(page):
        try:
            loc = ctx.locator(selector).first
            if await loc.count() == 0:
                continue
            await loc.click(timeout=_CONSENT_TIMEOUT_MS)
            return True
        except Exception:
            continue
    return False


async def _try_text(page, text: str) -> bool:
    """Boton/enlace por NOMBRE ACCESIBLE exacto (case-insensitive). Los
    locators por rol de Playwright atraviesan shadow DOM — cubre CMPs que el
    CSS plano no alcanza."""
    import re as _re
    pattern = _re.compile(rf"^\s*{_re.escape(text)}\s*$", _re.IGNORECASE)
    for ctx in _consent_contexts(page):
        for role in ("button", "link"):
            try:
                loc = ctx.get_by_role(role, name=pattern).first
                if await loc.count() == 0:
                    continue
                await loc.click(timeout=_CONSENT_TIMEOUT_MS)
                return True
            except Exception:
                continue
    return False


async def _dismiss_consent(page) -> Optional[str]:
    """Cierra un muro de consentimiento (cookies/GDPR). Devuelve la estrategia
    que funciono ("selector", "text=frase" o "learned:..."), o None si no habia
    muro o no se pudo cerrar. Nunca lanza: un muro no cerrado no debe impedir
    que la navegacion siga — el modelo lo vera en `page_state`.

    v2 (2026-07-23) — tres capas, de mas rapida a mas general:
      1. LO APRENDIDO para este dominio (via inmediata).
      2. Catalogo de CMPs mayoritarios (CSS, pagina + iframes).
      3. TEXTO accesible de aceptacion en 5 idiomas (atraviesa shadow DOM).
    Todo exito se APRENDE (dominio → estrategia) y persiste en el perfil."""
    domain = _domain_of(page)

    async def _settle():
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=3000)
        except Exception:
            pass

    # 1) lo aprendido para este dominio
    learned = _load_learned().get(domain)
    if learned:
        try:
            hit = (await _try_css(page, learned["value"])) if learned["kind"] == "css" \
                else (await _try_text(page, learned["value"]))
            if hit:
                await _settle()
                return f"learned:{learned['value']}"
        except Exception:
            pass

    # 2) catalogo de CMPs (acotado: los muros reales aparecen en el top-3 de
    # intentos con elemento presente; sin elemento presente el coste es ~0)
    intentos = 0
    for selector in _CONSENT_SELECTORS:
        if intentos >= _CONSENT_MAX_TRIES:
            break
        for ctx in _consent_contexts(page):
            try:
                loc = ctx.locator(selector).first
                if await loc.count() == 0:
                    continue
                intentos += 1
                await loc.click(timeout=_CONSENT_TIMEOUT_MS)
                await _settle()
                if domain:
                    _save_learned(domain, "css", selector)
                return selector
            except Exception:
                continue

    # 3) texto de aceptacion (la cola larga de CMPs caseros)
    for text in _CONSENT_TEXTS:
        try:
            if await _try_text(page, text):
                await _settle()
                if domain:
                    _save_learned(domain, "text", text)
                return f"text={text}"
        except Exception:
            continue
    return None


async def _page_state(page, tab_id: str, *, consent: Optional[str] = None) -> Dict[str, Any]:
    """[A-3] Donde ha aterrizado de verdad la navegacion. El modelo necesita
    saberlo SIN pagar otra llamada a la tool: antes solo recibia url+status, y
    no podia distinguir "he llegado al video" de "estoy mirando un muro"."""
    try:
        title = await page.title()
    except Exception:
        title = ""
    excerpt = ""
    try:
        excerpt = (await page.inner_text("body", timeout=3000) or "").strip()[:500]
    except Exception:
        pass
    return {
        "tab_id": tab_id,
        "url": page.url,
        "title": title,
        "text_excerpt": excerpt,
        "consent_dismissed": consent,
    }


class BrowserTool(BaseTool):
    tool_id = "browser"
    name = "Browser Tool"
    description = (
        "Navegador real (Chromium via Playwright): abre paginas, hace clic, "
        "escribe, hace scroll, descarga/sube archivos, lee HTML/texto. "
        "Interactuar con una pagina (click/type/download/upload) requiere "
        "confirmacion; navegar y leer no. Ademas: open_in_default_browser y "
        "play_media abren una URL/busqueda en el navegador REAL por defecto "
        "del usuario (fuera de Playwright), la via correcta para reproducir "
        "musica o video."
    )
    requires_confirmation = False  # depende de la accion

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            handler = {
                "open_url": self._open_url,
                "new_tab": self._new_tab,
                "close_tab": self._close_tab,
                "google_search": self._google_search,
                "click": self._click,
                "type": self._type,
                "scroll": self._scroll,
                "wait_for_element": self._wait_for_element,
                "download_file": self._download_file,
                "upload_file": self._upload_file,
                "screenshot": self._screenshot,
                "get_html": self._get_html,
                "get_text": self._get_text,
                "open_in_default_browser": self._open_in_default_browser,
                "play_media": self._play_media,
                "find_and_click": self._find_and_click,
                "page_state": self._page_state,
                "click_index": self._click_index,
                "type_index": self._type_index,
                "browse": self._browse,
            }.get(action)
            if not handler:
                return {
                    "success": False, "result": None,
                    "error": f"Accion desconocida: {action}. Disponibles: {', '.join(sorted(['open_url','new_tab','close_tab','google_search','click','type','scroll','wait_for_element','download_file','upload_file','screenshot','get_html','get_text','open_in_default_browser','play_media','find_and_click','page_state','click_index','type_index','browse']))}",
                }
            return await handler(params)
        except RuntimeError as e:
            return {"success": False, "result": None, "error": str(e)}
        except Exception as e:
            return {"success": False, "result": None, "error": f"{type(e).__name__}: {e}"}

    def list_actions(self) -> List[Dict[str, Any]]:
        tab = {"tab_id": "string opcional (default: pestana activa)"}
        return [
            {"id": "open_url", "description": (
                "Navega la pestana activa (o crea una) a una URL. Cierra solo los "
                "muros de cookies y devuelve donde has aterrizado de verdad: "
                "title, url final y un extracto del texto visible."),
             "requires_confirmation": False, "params": {**tab, "url": "string"}},
            {"id": "new_tab", "description": "Abre una pestana nueva, opcionalmente con una URL.",
             "requires_confirmation": False, "params": {"url": "string opcional"}},
            {"id": "close_tab", "description": "Cierra una pestana.",
             "requires_confirmation": False, "params": tab},
            {"id": "google_search", "description": (
                "Busca una query en Google en la pestana activa. DESACONSEJADA: Google "
                "bloquea la navegacion automatizada y suele fallar. Prefiere la tool "
                "'search' (search_web/search_news/search_images/search_videos) para "
                "obtener la URL y luego 'open_url' para abrirla."),
             "requires_confirmation": False, "params": {**tab, "query": "string"}},
            {"id": "click", "description": "Clic en un elemento (selector CSS).",
             "requires_confirmation": True, "params": {**tab, "selector": "string (selector CSS)"}},
            {"id": "type", "description": "Escribe texto en un campo (selector CSS).",
             "requires_confirmation": True, "params": {**tab, "selector": "string", "text": "string"}},
            {"id": "scroll", "description": "Hace scroll en la pagina.",
             "requires_confirmation": False, "params": {**tab, "direction": "'up'|'down' (default down)", "amount": "int pixeles (default 500)"}},
            {"id": "wait_for_element", "description": "Espera a que aparezca un elemento (hasta timeout).",
             "requires_confirmation": False, "params": {**tab, "selector": "string", "timeout_ms": "int opcional (default 10000)"}},
            {"id": "download_file", "description": "Clic en un elemento que dispara una descarga y la guarda dentro de HOME.",
             "requires_confirmation": True, "params": {**tab, "selector": "string (dispara la descarga)", "path": "string (destino, dentro de HOME)"}},
            {"id": "upload_file", "description": "Sube un archivo (dentro de HOME) a un input de tipo file.",
             "requires_confirmation": True, "params": {**tab, "selector": "string (input[type=file])", "path": "string (dentro de HOME)"}},
            {"id": "screenshot", "description": "Captura de pantalla de la pestana (PNG en base64).",
             "requires_confirmation": False, "params": tab},
            {"id": "get_html", "description": "HTML completo de la pagina actual.",
             "requires_confirmation": False, "params": tab},
            {"id": "get_text", "description": "Texto visible de la pagina (o de un selector concreto).",
             "requires_confirmation": False, "params": {**tab, "selector": "string opcional"}},
            {"id": "open_in_default_browser", "description": (
                "Abre una URL en el navegador REAL por defecto del usuario (no en "
                "Playwright): el que ya tiene sesion iniciada, con autoplay y cookies "
                "resueltas. Prefierela sobre open_url cuando el objetivo sea REPRODUCIR "
                "un video/cancion o simplemente abrirle una pagina al usuario."),
             "requires_confirmation": False, "params": {"url": "string"}},
            {"id": "play_media", "description": (
                "Busca una cancion, video o pagina con la tool 'search' (nunca con "
                "'browser.google_search', que Google bloquea) y abre el primer "
                "resultado en el navegador REAL por defecto del usuario. Es el atajo "
                "correcto para 'pon/reproduce/abre X' -- resuelve la busqueda y la "
                "apertura en un solo paso."),
             "requires_confirmation": False, "params": {"query": "string"}},
            {"id": "find_and_click", "description": (
                "RESPALDO de 'click' cuando no sabes el selector CSS o el que "
                "probaste no encuentra nada: describe el elemento en lenguaje "
                "natural y un modelo con vision lo localiza en la pagina. Usa "
                "'click' con selector siempre que puedas (es mas barato y "
                "preciso); esto es para cuando el DOM no basta."),
             "requires_confirmation": True,
             "params": {**tab, "description": "string (ej. 'el boton de aceptar cookies')"}},
            {"id": "page_state", "description": (
                "Foto del estado de la pagina para navegar paso a paso: lista "
                "NUMERADA de los elementos con los que se puede interactuar "
                "(indice, etiqueta, rol, texto) + url + titulo + si se puede "
                "seguir bajando. Con 'screenshot': true anade la captura con las "
                "cajas numeradas dibujadas encima. Los indices se usan luego en "
                "'click_index'/'type_index'."),
             "requires_confirmation": False,
             "params": {**tab, "screenshot": "bool opcional (default false)",
                        "max": "int opcional (default 60)"}},
            {"id": "click_index", "description": (
                "Clic en el elemento NUMERO N de la ultima 'page_state'. Mas "
                "preciso que un selector CSS adivinado: el indice apunta a un "
                "elemento real que estaba visible."),
             "requires_confirmation": True,
             "params": {**tab, "index": "int (el numero de 'page_state')"}},
            {"id": "type_index", "description": (
                "Escribe texto en el campo NUMERO N de la ultima 'page_state'. "
                "Con 'enter': true pulsa Intro despues (para buscadores)."),
             "requires_confirmation": True,
             "params": {**tab, "index": "int", "text": "string",
                        "enter": "bool opcional (default false)"}},
            {"id": "browse", "description": (
                "NAVEGACION PROFUNDA de varios pasos en piloto automatico: le "
                "das un objetivo en lenguaje natural ('busca X en esta tienda y "
                "anadelo al carrito') y Aithera navega sola —mirar la pagina, "
                "elegir, pulsar, escribir— hasta conseguirlo o explicar por que "
                "no. Usala para FLUJOS de varios pasos; para una sola accion, "
                "usa 'open_url'/'click_index' directamente. Reconoce sola cinco "
                "flujos y para en su frontera: compra (hasta el carrito, el "
                "pago lo da el usuario), cita (hasta el resumen, sin "
                "confirmar), descarga (localiza el enlace, no instala), "
                "api_key (ensena donde se genera, no la crea) y foro (lee y "
                "sintetiza, sin publicar). NUNCA escribe contrasenas ni datos "
                "de pago."),
             "requires_confirmation": True,
             "params": {"goal": "string (el objetivo, en lenguaje natural)",
                        "start_url": "string opcional (por donde empezar)",
                        "playbook": ("string opcional: compra|cita|descarga|"
                                     "api_key|foro. Si no lo pones se deduce "
                                     "del objetivo"),
                        "max_steps": "int opcional (lo decide el flujo)"}},
        ]

    # ------------------------------------------------------------------

    async def _open_url(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = (params.get("url") or "").strip()
        if not url:
            return {"success": False, "result": None, "error": "falta parametro: url"}
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url
        tid, page = await _get_page(params.get("tab_id"), _session_id_of(params))
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # [A-3] El muro de cookies se cierra ANTES de reportar exito: llegar al
        # muro no es llegar a la pagina.
        consent = await _dismiss_consent(page)
        state = await _page_state(page, tid, consent=consent)
        state["status"] = response.status if response else None
        return {"success": True, "result": state, "error": None}

    async def _new_tab(self, params: Dict[str, Any]) -> Dict[str, Any]:
        sess = await _get_session(_session_id_of(params))
        new_id = uuid.uuid4().hex[:10]
        page = await sess.context.new_page()
        sess.pages[new_id] = page
        sess.current_tab = new_id
        url = (params.get("url") or "").strip()
        consent = None
        if url:
            if not (url.startswith("http://") or url.startswith("https://")):
                url = "https://" + url
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            consent = await _dismiss_consent(page)
        return {"success": True, "result": await _page_state(page, new_id, consent=consent),
                "error": None}

    async def _close_tab(self, params: Dict[str, Any]) -> Dict[str, Any]:
        sess = await _get_session(_session_id_of(params))
        tab_id = params.get("tab_id") or sess.current_tab
        if not tab_id or tab_id not in sess.pages:
            return {"success": False, "result": None, "error": f"pestana no encontrada: {tab_id}"}
        await sess.pages[tab_id].close()
        del sess.pages[tab_id]
        if sess.current_tab == tab_id:
            sess.current_tab = next(iter(sess.pages), None)
        return {"success": True, "result": {"tab_id": tab_id, "closed": True}, "error": None}

    async def _google_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = (params.get("query") or "").strip()
        if not query:
            return {"success": False, "result": None, "error": "falta parametro: query"}
        from urllib.parse import quote
        tid, page = await _get_page(params.get("tab_id"), _session_id_of(params))
        await page.goto(f"https://www.google.com/search?q={quote(query)}", wait_until="domcontentloaded", timeout=30000)
        consent = await _dismiss_consent(page)
        return {"success": True, "result": await _page_state(page, tid, consent=consent), "error": None}

    async def _click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        selector = params.get("selector")
        if not selector:
            return {"success": False, "result": None, "error": "falta parametro: selector"}
        tid, page = await _get_page(params.get("tab_id"), _session_id_of(params))
        # [A-3 fix 2026-07-21] El muro de cookies REAPARECE al interactuar (YouTube
        # lo reinyecta tras un rato / tras el primer clic). Se cierra ANTES de
        # clicar: si no, el clic caía sobre el overlay y la canción no se
        # reproducía (o se pausaba). Best-effort, no rompe si no hay muro.
        await _dismiss_consent(page)
        await page.click(selector, timeout=10000)
        return {"success": True, "result": {"tab_id": tid, "clicked": selector}, "error": None}

    async def _type(self, params: Dict[str, Any]) -> Dict[str, Any]:
        selector = params.get("selector")
        text = params.get("text", "")
        if not selector:
            return {"success": False, "result": None, "error": "falta parametro: selector"}
        tid, page = await _get_page(params.get("tab_id"), _session_id_of(params))
        await _dismiss_consent(page)   # [A-3 fix] el muro puede reaparecer antes de escribir
        await page.fill(selector, text, timeout=10000)
        return {"success": True, "result": {"tab_id": tid, "typed_into": selector}, "error": None}

    async def _scroll(self, params: Dict[str, Any]) -> Dict[str, Any]:
        direction = params.get("direction", "down")
        amount = int(params.get("amount", 500))
        delta = amount if direction == "down" else -amount
        tid, page = await _get_page(params.get("tab_id"), _session_id_of(params))
        await page.mouse.wheel(0, delta)
        return {"success": True, "result": {"tab_id": tid, "scrolled": delta}, "error": None}

    async def _wait_for_element(self, params: Dict[str, Any]) -> Dict[str, Any]:
        selector = params.get("selector")
        if not selector:
            return {"success": False, "result": None, "error": "falta parametro: selector"}
        timeout_ms = int(params.get("timeout_ms", 10000))
        tid, page = await _get_page(params.get("tab_id"), _session_id_of(params))
        try:
            await page.wait_for_selector(selector, timeout=timeout_ms)
        except Exception:
            return {"success": False, "result": None, "error": f"elemento no aparecio en {timeout_ms}ms: {selector}"}
        return {"success": True, "result": {"tab_id": tid, "found": selector}, "error": None}

    async def _download_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        selector = params.get("selector")
        path_str = params.get("path", "")
        if not selector or not path_str:
            return {"success": False, "result": None, "error": "faltan parametros: selector y path"}
        dest = _resolve_user_path(path_str)
        if not _is_path_allowed(dest):
            return {"success": False, "result": None, "error": f"destino fuera de zonas permitidas: {dest}"}

        tid, page = await _get_page(params.get("tab_id"), _session_id_of(params))
        try:
            async with page.expect_download(timeout=30000) as dl_info:
                await page.click(selector, timeout=10000)
            download = await dl_info.value
            dest.parent.mkdir(parents=True, exist_ok=True)
            await download.save_as(str(dest))
        except Exception as e:
            return {"success": False, "result": None, "error": f"la descarga no se disparo o fallo: {e}"}
        return {"success": True, "result": {"tab_id": tid, "path": str(dest)}, "error": None}

    async def _upload_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        selector = params.get("selector")
        path_str = params.get("path", "")
        if not selector or not path_str:
            return {"success": False, "result": None, "error": "faltan parametros: selector y path"}
        src = _resolve_user_path(path_str)
        if not _is_path_allowed(src) or not src.exists():
            return {"success": False, "result": None, "error": f"archivo no valido o fuera de HOME: {src}"}

        tid, page = await _get_page(params.get("tab_id"), _session_id_of(params))
        await page.set_input_files(selector, str(src), timeout=10000)
        return {"success": True, "result": {"tab_id": tid, "uploaded": str(src)}, "error": None}

    async def _screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tid, page = await _get_page(params.get("tab_id"), _session_id_of(params))
        png = await page.screenshot(type="png")
        return {"success": True, "result": {
            "tab_id": tid, "image_base64": base64.b64encode(png).decode(), "format": "png",
        }, "error": None}

    async def _get_html(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tid, page = await _get_page(params.get("tab_id"), _session_id_of(params))
        html = await page.content()
        MAX_HTML = 200_000
        truncated = len(html) > MAX_HTML
        return {"success": True, "result": {
            "tab_id": tid, "html": html[:MAX_HTML], "truncated": truncated,
        }, "error": None}

    async def _get_text(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tid, page = await _get_page(params.get("tab_id"), _session_id_of(params))
        selector = params.get("selector")
        if selector:
            text = await page.inner_text(selector, timeout=10000)
        else:
            text = await page.evaluate("document.body ? document.body.innerText : ''")
        MAX_TEXT = 20_000
        truncated = len(text) > MAX_TEXT
        return {"success": True, "result": {
            "tab_id": tid, "text": text[:MAX_TEXT], "truncated": truncated,
        }, "error": None}

    # ------------------------------------------------------------------
    # [B·WEB-1, doc 32] Navegador REAL del sistema -- ninguna de las dos
    # toca Playwright/_get_page: por eso no reciben tab_id ni pasan por
    # _dismiss_consent (el navegador del usuario ya resuelve sus propios
    # muros de cookies con la sesion que tiene abierta).

    async def _open_in_default_browser(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = (params.get("url") or "").strip()
        if not url:
            return {"success": False, "result": None, "error": "falta parametro: url"}
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url
        try:
            abierto = await asyncio.to_thread(_launch_default_browser, url)
        except Exception as e:
            return {"success": False, "result": None,
                    "error": f"no se pudo abrir el navegador por defecto: {type(e).__name__}: {e}"}
        if not abierto:
            return {"success": False, "result": None,
                    "error": f"el sistema no encontro un navegador por defecto para abrir: {url}"}
        return {"success": True, "result": {"url": url}, "error": None}

    async def _play_media(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = (params.get("query") or "").strip()
        if not query:
            return {"success": False, "result": None, "error": "falta parametro: query"}
        # search_tool, NUNCA browser.google_search (Google bloquea headless) ni
        # scraping por regex -- una API de busqueda real, ya probada.
        resultado = await _search("videos", query, 5)
        if not resultado.get("success"):
            return {"success": False, "result": None,
                    "error": resultado.get("error") or f"la busqueda de '{query}' fallo"}
        items = (resultado.get("result") or {}).get("items") or []
        primero = next((it for it in items if it.get("url")), None)
        if not primero:
            return {"success": False, "result": None,
                    "error": f"no se encontraron resultados reproducibles para: {query}"}
        abierto = await self._open_in_default_browser({"url": primero["url"]})
        if not abierto.get("success"):
            return abierto
        return {"success": True, "result": {
            "query": query, "url": primero["url"], "title": primero.get("title"),
        }, "error": None}

    # ------------------------------------------------------------------
    # [B·WEB-2, doc 32] Clic por VISION sobre la pagina — con set-of-mark.

    async def _find_and_click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Localiza un elemento por su descripcion y hace clic.

        DOS vias, en este orden (paso 3 del plan):
          1. SET-OF-MARK: se numeran los elementos interactivos VISIBLES, se
             dibujan sus cajas y el modelo elige un INDICE. El clic va entonces
             a un elemento REAL del DOM (`page.mouse.click` sobre su centro),
             no a una estimacion de pixeles.
          2. COORDENADAS: si el modelo dice que lo que busca no tiene caja
             (contenido dentro de un canvas, un elemento no estandar), responde
             x/y y se clica ahi.
        Las marcas se retiran SIEMPRE antes de clicar — si no, el clic caeria
        sobre el overlay y no sobre la pagina (mismo tipo de fallo que el muro
        de cookies de A-3)."""
        description = (params.get("description") or "").strip()
        if not description:
            return {"success": False, "result": None, "error": "falta parametro: description"}

        tid, page = await _get_page(params.get("tab_id"), _session_id_of(params))
        await _dismiss_consent(page)   # mismo criterio que _click: el muro reaparece

        marks: List[Dict[str, Any]] = []
        try:
            estado = await page.evaluate(_SET_OF_MARK_JS, {"max": 60, "paint": True})
            marks = (estado or {}).get("marks") or []
        except Exception as e:      # una pagina puede bloquear la inyeccion (CSP)
            logger.info(f"[browser] set-of-mark no disponible, sigo por coordenadas: {e!r}")

        try:
            png = await page.screenshot(type="png")
            b64 = base64.b64encode(png).decode()
            viewport = page.viewport_size or {}
            ancho = int(viewport.get("width") or 0)
            alto = int(viewport.get("height") or 0)
        finally:
            # Fuera las marcas pase lo que pase: dejarlas pintadas taparia la
            # pagina para el usuario Y para cualquier accion posterior.
            try:
                await page.evaluate(_CLEAR_MARKS_JS)
            except Exception:
                pass

        ubic, error = await vision_click.locate(
            description, b64, width=ancho or 1280, height=alto or 720, marks=marks)
        if ubic is None:
            return {"success": False, "result": None, "error": error}

        elegido = None
        if ubic.index is not None:
            elegido = next((m for m in marks if m.get("index") == ubic.index), None)
            if elegido is None:
                return {"success": False, "result": None,
                        "error": (f"el modelo eligió la caja [{ubic.index}], que no existe "
                                  f"en esta página (no se hace clic a ciegas)")}
            x, y = elegido["center"]
        else:
            x, y = vision_click.to_screen_coords(
                ubic.x, ubic.y, image_size=(ancho or 1280, alto or 720),
                screen_size=(ancho or 1280, alto or 720))

        await page.mouse.click(x, y)
        return {"success": True, "result": {
            "tab_id": tid, "description": description,
            "located_by": "set_of_mark" if elegido else "vision_coords",
            "clicked_at": [x, y],
            "element": (elegido or {}).get("text"),
        }, "error": None}

    # ------------------------------------------------------------------
    # [C·WEB-3, doc 32] Navegacion POR INDICE — observar / actuar.

    async def _page_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """La OBSERVACION del bucle agentic: qué hay en la página AHORA y con qué
        se puede interactuar, numerado.

        La captura con las cajas es OPCIONAL (`screenshot: true`) a propósito:
        en la inmensa mayoría de los pasos la lista de texto basta para elegir, y
        mandar una imagen en cada vuelta multiplicaría el coste por diez. La
        imagen se pide cuando la lista no aclara (paso ambiguo, componente
        gráfico) — misma filosofía que la visión en B·WEB-2: el último recurso,
        no el primero."""
        tid, page = await _get_page(params.get("tab_id"), _session_id_of(params))
        # Ventaja sobre Mark-L (doc 32): el muro de cookies se cierra ANTES de
        # mirar; si no, la "página" que el modelo ve es el muro, no el contenido.
        await _dismiss_consent(page)

        quiere_captura = bool(params.get("screenshot"))
        try:
            maximo = max(1, min(int(params.get("max", 60)), 120))
        except (TypeError, ValueError):
            maximo = 60

        try:
            estado = await page.evaluate(_SET_OF_MARK_JS,
                                         {"max": maximo, "paint": quiere_captura})
        except Exception as e:
            return {"success": False, "result": None,
                    "error": f"no se pudo leer el estado de la pagina: {type(e).__name__}: {e}"}
        estado = estado or {}
        marks = estado.get("marks") or []

        imagen = None
        try:
            if quiere_captura:
                png = await page.screenshot(type="png")
                imagen = base64.b64encode(png).decode()
        finally:
            if quiere_captura:
                try:
                    await page.evaluate(_CLEAR_MARKS_JS)
                except Exception:
                    pass

        resultado: Dict[str, Any] = {
            "tab_id": tid,
            "url": page.url,
            "title": await page.title(),
            "elements": marks,
            "elements_text": _serialize_marks(marks),
            "truncated": bool(estado.get("truncated")),
            "scroll": estado.get("scroll") or {},
        }
        if imagen:
            resultado["image_base64"] = imagen
        return {"success": True, "result": resultado, "error": None}

    async def _resolve_index(self, page, params: Dict[str, Any]):
        """El elemento numero N — se REMIRA la pagina en el momento de actuar.

        Por que se vuelve a mirar en vez de guardar el mapa de la ultima
        `page_state`: entre observar y actuar la pagina puede haber cambiado
        (un menu que se despliega, contenido que carga). Un indice guardado
        apuntaria entonces a otra cosa y el clic caeria donde no debe. Volver a
        pedir el estado cuesta milisegundos y garantiza que el numero N es el
        que el modelo acaba de ver."""
        try:
            idx = int(params.get("index"))
        except (TypeError, ValueError):
            return None, "falta parametro: index (numero entero de 'page_state')"
        if idx < 0:
            return None, f"indice invalido: {idx}"
        try:
            estado = await page.evaluate(_SET_OF_MARK_JS, {"max": 120, "paint": False})
        except Exception as e:
            return None, f"no se pudo releer la pagina: {type(e).__name__}: {e}"
        marks = (estado or {}).get("marks") or []
        elegido = next((m for m in marks if m.get("index") == idx), None)
        if elegido is None:
            return None, (f"el elemento [{idx}] ya no existe en la pagina "
                          f"(hay {len(marks)}); vuelve a pedir 'page_state'")
        return elegido, None

    async def _click_index(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tid, page = await _get_page(params.get("tab_id"), _session_id_of(params))
        await _dismiss_consent(page)
        elegido, error = await self._resolve_index(page, params)
        if elegido is None:
            return {"success": False, "result": None, "error": error}
        x, y = elegido["center"]
        await page.mouse.click(x, y)
        return {"success": True, "result": {
            "tab_id": tid, "index": elegido["index"], "element": elegido.get("text"),
            "clicked_at": [x, y],
        }, "error": None}

    async def _type_index(self, params: Dict[str, Any]) -> Dict[str, Any]:
        texto = params.get("text")
        if texto is None:
            return {"success": False, "result": None, "error": "falta parametro: text"}
        tid, page = await _get_page(params.get("tab_id"), _session_id_of(params))
        await _dismiss_consent(page)
        elegido, error = await self._resolve_index(page, params)
        if elegido is None:
            return {"success": False, "result": None, "error": error}
        x, y = elegido["center"]
        await page.mouse.click(x, y)          # foco en el campo
        await page.keyboard.type(str(texto))
        if params.get("enter"):
            await page.keyboard.press("Enter")
        return {"success": True, "result": {
            "tab_id": tid, "index": elegido["index"], "element": elegido.get("text"),
            "typed_chars": len(str(texto)), "enter": bool(params.get("enter")),
        }, "error": None}

    async def _browse(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """La puerta al bucle agentic de navegación (C·WEB-3).

        Import DIFERIDO de `app.tie` a propósito: el bucle llama al ToolManager
        (que a su vez conoce esta tool), así que importarlo a nivel de módulo
        crearía un ciclo en el arranque. Se importa la primera vez que alguien
        navega de verdad — mismo criterio que el import lazy de Playwright."""
        goal = (params.get("goal") or "").strip()
        if not goal:
            return {"success": False, "result": None, "error": "falta parametro: goal"}
        try:
            import app.tie as tie                     # API pública, nunca el interno
            from .tool_manager import tool_manager
        except Exception as e:
            return {"success": False, "result": None,
                    "error": f"el bucle de navegacion no esta disponible: {e}"}

        # `max_steps` ausente = que lo decida el flujo (un research en un foro
        # necesita mas vueltas que anadir algo a un carrito). Solo se acota lo
        # que llegue de fuera.
        max_steps = None
        if params.get("max_steps") is not None:
            try:
                max_steps = max(1, min(int(params["max_steps"]), 40))
            except (TypeError, ValueError):
                max_steps = None

        resultado = await tie.browse(
            goal, tool_manager=tool_manager,
            session_key=_session_id_of(params),
            approval_gate=params.get("_approval_gate"),
            mission_id=params.get("_mission_id"),
            max_steps=max_steps,
            start_url=(params.get("start_url") or "").strip() or None,
            playbook=(params.get("playbook") or "").strip() or None,
        )
        salida = {
            "goal": goal, "steps": resultado.steps, "final_url": resultado.final_url,
            "answer": resultado.answer, "actions": resultado.actions,
        }
        if resultado.playbook:
            salida["playbook"] = resultado.playbook
        if resultado.limitations:
            salida["limitations"] = resultado.limitations
        if resultado.notes:
            salida["notes"] = resultado.notes
        # [C·WEB-4] El flujo de descarga LOCALIZA el enlace; bajarlo es de
        # `download_tool`. El propio bucle dice cual es el siguiente paso, para
        # que el bucle general no tenga que adivinarlo (y para que esta tool no
        # tenga que importar un interno del TIE — doc 16).
        if resultado.handoff:
            salida["next_step"] = resultado.handoff
        return {"success": resultado.ok, "result": salida, "error": resultado.error}
