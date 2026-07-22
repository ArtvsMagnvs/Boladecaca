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


async def _ensure_browser():
    global _playwright, _browser, _persistent_context
    if _browser is not None or _persistent_context is not None:
        return
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
    profile_dir = settings.BROWSER_PROFILE_DIR
    # Sin la barra "Chrome esta siendo controlado por software automatizado":
    # es el navegador DEL USUARIO trabajando para el, no un banco de pruebas.
    launch_kwargs = dict(headless=headless, ignore_default_args=["--enable-automation"])

    # Cadena de degradacion honesta (cada nivel se loguea):
    #   1) Chrome REAL + perfil persistente de Aithera   ← lo pedido
    #   2) Chromium bundled + perfil persistente         (no hay Chrome)
    #   3) Chromium efimero (modo antiguo)               (perfil bloqueado)
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
    En modo respaldo: BrowserContext efimero propio (comportamiento antiguo)."""
    await _ensure_browser()
    sid = session_id or _DEFAULT_SESSION
    sess = _sessions.get(sid)
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
