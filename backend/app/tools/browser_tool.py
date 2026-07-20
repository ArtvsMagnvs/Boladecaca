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
# wait_for_element, download_file, upload_file, screenshot, get_html, get_text.

import base64
import uuid
from typing import Dict, Any, List, Optional

from app.core.config import settings
from .base import BaseTool
from .filesystem_tool import _resolve_user_path, _is_path_allowed

# Estado del navegador -- un unico proceso Chromium.
_playwright = None
_browser = None

# [Auditoria v0.9.5, F-1] SESION POR MISION. Antes las pestanas vivian en un
# unico dict global y `_current_tab` era una sola variable: con
# ORCH_MAX_CONCURRENT=3, dos misiones que usaran el navegador a la vez se
# pisaban la pestana activa (la mision A navegaba, la B clicaba en la pagina de
# A). Ahora cada mision tiene su propio BrowserContext de Playwright — pestanas,
# cookies y sesion aisladas — y su propia pestana activa.
#
# Clave "default" = sin mision (chat directo, tests): mismo comportamiento de
# siempre, cero regresion.
_DEFAULT_SESSION = "default"


class _Session:
    """Pestanas + pestana activa de UNA mision, sobre su propio BrowserContext."""

    def __init__(self, context: Any) -> None:
        self.context = context
        self.pages: Dict[str, Any] = {}
        self.current_tab: Optional[str] = None


_sessions: Dict[str, _Session] = {}


async def _ensure_browser():
    global _playwright, _browser
    if _browser is not None:
        return
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        raise RuntimeError(
            "Playwright no esta instalado (pip install playwright && "
            "playwright install chromium)"
        ) from e
    _playwright = await async_playwright().start()
    try:
        # [Fix 2026-07-19] VISIBLE, no headless. Aithera decia "he abierto el
        # navegador" y el usuario no veia ninguna ventana: el navegador existia
        # de verdad, pero invisible. Si Aithera navega POR TI, tienes que poder
        # mirar lo que hace y tomar el control cuando quieras — un agente que
        # actua a ciegas en tu ordenador es justo lo contrario de lo que se
        # busca aqui.
        #
        # Ademas funciona MEJOR: Google y otros sitios bloquean el trafico
        # headless por sospechoso (ya documentado en CLAUDE.md §8 como
        # limitacion real de `browser.google_search`).
        _browser = await _playwright.chromium.launch(headless=settings.BROWSER_HEADLESS)
    except Exception as e:
        raise RuntimeError(
            f"no se pudo lanzar Chromium (¿falta 'playwright install chromium'?): {e}"
        ) from e


async def _get_session(session_id: Optional[str]) -> _Session:
    """La sesion de navegador de una mision (su BrowserContext propio)."""
    await _ensure_browser()
    sid = session_id or _DEFAULT_SESSION
    sess = _sessions.get(sid)
    if sess is None:
        sess = _Session(await _browser.new_context())
        _sessions[sid] = sess
    return sess


def _session_id_of(params: Dict[str, Any]) -> Optional[str]:
    """La mision duena de esta llamada. El toolloop la inyecta en los params
    (`_session`) desde la autoridad de la mision; sin ella se usa "default"."""
    sid = params.get("_session") or params.get("mission_id")
    return str(sid) if sid else None


async def _get_page(tab_id: Optional[str], session_id: Optional[str] = None):
    """Resuelve la pestana DENTRO de la sesion de esta mision: la pedida, o la
    activa, o crea una nueva si no hay ninguna abierta todavia."""
    sess = await _get_session(session_id)
    tid = tab_id or sess.current_tab
    if tid and tid in sess.pages:
        return tid, sess.pages[tid]
    new_id = uuid.uuid4().hex[:10]
    page = await sess.context.new_page()
    sess.pages[new_id] = page
    sess.current_tab = new_id
    return new_id, page


async def close_session(session_id: str) -> bool:
    """Cierra la sesion de navegador de una mision (libera su contexto y todas
    sus pestanas). La llama el executor al terminar una mision: sin esto, cada
    mision que abriera el navegador dejaria un contexto vivo para siempre."""
    sess = _sessions.pop(session_id, None)
    if sess is None:
        return False
    try:
        await sess.context.close()
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
)
_CONSENT_TIMEOUT_MS = 1200
_CONSENT_MAX_TRIES = 3


async def _dismiss_consent(page) -> Optional[str]:
    """Intenta cerrar un muro de consentimiento. Devuelve el selector que
    funciono, o None si no habia muro (o no se pudo cerrar).

    Nunca lanza: un muro no cerrado no debe impedir que la navegacion siga —
    el modelo lo vera igualmente en `page_state` y podra decidir otra via."""
    intentos = 0
    for selector in _CONSENT_SELECTORS:
        if intentos >= _CONSENT_MAX_TRIES:
            break
        try:
            loc = page.locator(selector).first
            if await loc.count() == 0:
                continue
            intentos += 1
            await loc.click(timeout=_CONSENT_TIMEOUT_MS)
            # Deja que la pagina reaccione al consentimiento (recarga/overlay).
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=3000)
            except Exception:
                pass
            return selector
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
        "confirmacion; navegar y leer no."
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
            }.get(action)
            if not handler:
                return {
                    "success": False, "result": None,
                    "error": f"Accion desconocida: {action}. Disponibles: {', '.join(sorted(['open_url','new_tab','close_tab','google_search','click','type','scroll','wait_for_element','download_file','upload_file','screenshot','get_html','get_text']))}",
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
        await page.click(selector, timeout=10000)
        return {"success": True, "result": {"tab_id": tid, "clicked": selector}, "error": None}

    async def _type(self, params: Dict[str, Any]) -> Dict[str, Any]:
        selector = params.get("selector")
        text = params.get("text", "")
        if not selector:
            return {"success": False, "result": None, "error": "falta parametro: selector"}
        tid, page = await _get_page(params.get("tab_id"), _session_id_of(params))
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
