# backend/app/integrations/google_auth.py
#
# V0.7 (Fase 4 Email + Calendar): gestion centralizada de OAuth 2.0
# para Google APIs (Gmail + Calendar).
#
# Token guardado en: %APPDATA%/Aithera/google_token.json
# Credenciales del cliente OAuth (client_id, client_secret) se guardan
# en la tabla `config` de PostgreSQL, no en este modulo.
#
# DISENO:
# - Importar este modulo NUNCA rompe el backend. Si los google libs
#   no estan instalados o el token no existe, is_connected() devuelve False
#   y los endpoints devuelven 503 con un mensaje claro.
# - Las credenciales se leen SIEMPRE desde la BD (tabla config), no
#   desde variables de entorno, para que el usuario pueda configurarlas
#   desde la UI sin reiniciar el backend.
import json
import os
import threading
from pathlib import Path
from typing import Optional, Dict, Any

TOKEN_PATH = Path(os.environ.get("APPDATA") or ".") / "Aithera" / "google_token.json"

# Scopes necesarios: Gmail (read, compose, send) + Calendar (read, events).
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

# Lock para evitar race conditions cuando dos hilos llaman a OAuth a la vez.
_oauth_lock = threading.Lock()


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _google_libs_available() -> bool:
    """Devuelve True si las librerias de Google estan instaladas."""
    try:
        from google.auth.transport.requests import Request  # noqa: F401
        from google.oauth2.credentials import Credentials  # noqa: F401
        from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: F401
        return True
    except ImportError:
        return False


def _load_client_credentials() -> Optional[Dict[str, str]]:
    """Lee client_id / client_secret de la tabla `config` de PostgreSQL.

    Las claves que buscamos son:
      - google_client_id
      - google_client_secret

    Se ponen como entradas separadas (no JSON) porque asi son mas faciles
    de editar desde la UI de Settings.
    """
    try:
        from app.db.database import SessionLocal
        from app.db.models import Config
        db = SessionLocal()
        try:
            cid_row = db.query(Config).filter(Config.key == "google_client_id").first()
            cs_row = db.query(Config).filter(Config.key == "google_client_secret").first()
            if cid_row and cs_row and cid_row.value and cs_row.value:
                return {
                    "client_id": cid_row.value,
                    "client_secret": cs_row.value,
                }
            return None
        finally:
            db.close()
    except Exception as e:
        # Si la BD falla o el modelo no existe, devolvemos None.
        print(f"[google_auth] error leyendo credenciales: {e}")
        return None


def save_client_credentials(client_id: str, client_secret: str) -> bool:
    """Guarda client_id / client_secret en la tabla config."""
    try:
        from app.db.database import SessionLocal
        from app.db.models import Config
        db = SessionLocal()
        try:
            for key, value in (("google_client_id", client_id),
                               ("google_client_secret", client_secret)):
                row = db.query(Config).filter(Config.key == key).first()
                if row:
                    row.value = value
                else:
                    db.add(Config(key=key, value=value))
            db.commit()
            return True
        finally:
            db.close()
    except Exception as e:
        print(f"[google_auth] error guardando credenciales: {e}")
        return False


# ----------------------------------------------------------------------
# API publica
# ----------------------------------------------------------------------

def is_google_libs_available() -> bool:
    """True si las google libs estan instaladas."""
    return _google_libs_available()


def has_client_credentials() -> bool:
    """True si hay client_id / client_secret en la BD."""
    return _load_client_credentials() is not None


# ----------------------------------------------------------------------
# AUTH-1 (2026-07-23): estados de conexion + refresco robusto.
#
# El flujo previo tenia dos limitaciones que el usuario ya sufrio:
#   1. Un token REVOCADO (borrado desde la cuenta de Google, o con el
#      refresh_token invalidado) se veia EXACTAMENTE igual que "nunca
#      conectado": ambos daban is_connected()=False, sin pista de que la
#      solucion era "vuelve a conectar" y no "configura credenciales".
#   2. Cada refresco hacia `TOKEN_PATH.write_text(creds.to_json())`, que
#      SOBREESCRIBE el json entero y BORRA el campo cacheado "email" ->
#      forzaba una llamada extra a Gmail getProfile en el siguiente /status.
#
# `_load_and_refresh()` centraliza carga+refresco UNA vez y clasifica el
# resultado. `connection_state()` lo expone al /status. `get_credentials()`
# pasa a delegar aqui (mismo contrato: creds valido o None).
#
# Estados posibles (str, estables para el frontend):
#   connected      token valido (o refrescado con exito)
#   no_token       nunca se conecto (no hay token guardado)
#   revoked        el refresh_token ya no sirve -> hay que RECONECTAR
#   expired        el token expiro pero el refresco fallo por algo transitorio
#                  (sin internet, timeout) -> reintentar luego, NO reconectar
#   no_credentials falta client_id / client_secret
#   libs_missing   las google libs no estan instaladas

def _write_token_preserving_email(creds) -> None:
    """Escribe el token refrescado SIN perder el campo `email` ya cacheado.

    `creds.to_json()` no incluye nuestro campo extra `email`; si lo volcamos
    tal cual, el siguiente /status tendria que volver a preguntarlo a Gmail.
    """
    try:
        prev_email = None
        if TOKEN_PATH.exists():
            try:
                prev_email = json.loads(TOKEN_PATH.read_text()).get("email")
            except Exception:
                prev_email = None
        data = json.loads(creds.to_json())
        if prev_email and not data.get("email"):
            data["email"] = prev_email
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(json.dumps(data))
    except Exception as e:  # best-effort: si falla, al menos deja el token base
        print(f"[google_auth] no se pudo preservar el email al refrescar: {e}")
        try:
            TOKEN_PATH.write_text(creds.to_json())
        except Exception:
            pass


def _load_and_refresh() -> tuple:
    """Carga el token y lo refresca si hace falta.

    Devuelve (creds|None, state). Es el UNICO punto que hace I/O de red para
    el refresco; tanto get_credentials() como connection_state() pasan por
    aqui, asi que el token se refresca como mucho una vez por llamada.
    """
    if not _google_libs_available():
        return None, "libs_missing"
    if not TOKEN_PATH.exists():
        return None, "no_token"
    try:
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), GOOGLE_SCOPES)
    except Exception as e:
        # Token corrupto / json ilegible: tratarlo como "hay que reconectar".
        print(f"[google_auth] token ilegible: {e}")
        return None, "revoked"

    if creds and creds.valid:
        return creds, "connected"

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(_timeout_request())
            _write_token_preserving_email(creds)
            return creds, "connected"
        except Exception as e:
            # invalid_grant = el refresh_token ya no vale (revocado, cambio de
            # contrasena, app retirada del consentimiento) -> reconectar.
            # Cualquier otra cosa (timeout, DNS, 5xx) es transitoria.
            msg = str(e).lower()
            if "invalid_grant" in msg or "invalid_token" in msg or "unauthorized" in msg:
                print(f"[google_auth] refresh_token invalido (revocado): {e}")
                return None, "revoked"
            print(f"[google_auth] error transitorio al refrescar: {e}")
            return None, "expired"

    # Expirado y sin refresh_token utilizable -> no hay forma de recuperarlo solo.
    return None, "revoked"


def get_credentials() -> Optional[Any]:
    """Obtiene credenciales validas. Refresca si han expirado.

    Devuelve None si:
      - las google libs no estan instaladas
      - no hay token guardado (el usuario no ha hecho OAuth aun)
      - las credenciales expiraron y no se pudieron refrescar

    (AUTH-1) Delega en _load_and_refresh(); el contrato publico no cambia
    —sigue devolviendo creds valido o None— pero ahora comparte la logica
    de refresco y la preservacion del email cacheado.
    """
    creds, _state = _load_and_refresh()
    return creds


def connection_state() -> str:
    """(AUTH-1) Estado de la conexion con Google, para mensajes claros en la UI.

    Uno de: connected | expired | revoked | no_token | no_credentials | libs_missing.
    Refresca el token si esta expirado (mismo coste que is_connected()); el Hub
    lo sondea cada 30 s, pero el refresco de red solo ocurre cuando el token ya
    ha caducado (~1 vez/hora), no en cada sondeo.
    """
    if not _google_libs_available():
        return "libs_missing"
    if not has_client_credentials():
        return "no_credentials"
    _creds, state = _load_and_refresh()
    return state


# [Fix 2026-07-19] Refresco de token con TIMEOUT EXPLICITO.
#
# `Request()` de google-auth usa 120 s por defecto. Sin internet, refrescar el
# token —que dispara `GET /api/email/status`, y el Hub lo pide al montar y cada
# 30 s— ocupaba un hilo del pool hasta DOS MINUTOS. Como el token de Google
# caduca cada ~1 h, el sintoma aparecia de vez en cuando y era dificil de atar a
# su causa. 15 s sobra para un refresco que normalmente tarda menos de uno.
GOOGLE_REFRESH_TIMEOUT_S = 15


def _timeout_request():
    """Un `Request` de google-auth que impone nuestro timeout en cada llamada."""
    from google.auth.transport.requests import Request

    class _TimeoutRequest(Request):
        def __call__(self, url, method="GET", body=None, headers=None,
                     timeout=GOOGLE_REFRESH_TIMEOUT_S, **kwargs):
            return super().__call__(url, method, body, headers, timeout, **kwargs)

    return _TimeoutRequest()


def get_credentials_source() -> str:
    """V0.7 extra: devuelve 'env' o 'db' o 'none' segun de donde vienen las credenciales."""
    creds = _load_client_credentials()
    if not creds:
        return "none"
    return creds.get("source", "none")


def is_connected() -> bool:
    """True si el usuario esta conectado a Google (token valido)."""
    return get_credentials() is not None


def get_connected_email() -> Optional[str]:
    """Devuelve el EMAIL de la cuenta Google conectada (nunca el client_id).

    El token de OAuth no trae el email (los scopes no incluyen `openid`), asi
    que la primera vez lo pedimos al perfil de Gmail (`getProfile`, permitido
    por el scope gmail.readonly) y lo cacheamos en el propio token json para
    no repetir la llamada en cada /email/status.
    """
    if not TOKEN_PATH.exists():
        return None
    try:
        data = json.loads(TOKEN_PATH.read_text())
    except Exception:
        return None

    cached = data.get("email")
    if cached:
        return cached

    email = _fetch_email_via_gmail()
    if email:
        try:  # cachear en el token json (best-effort)
            data["email"] = email
            TOKEN_PATH.write_text(json.dumps(data))
        except Exception:
            pass
    return email


def _fetch_email_via_gmail() -> Optional[str]:
    """Obtiene el email de la cuenta llamando a Gmail users.getProfile.
    Usa el scope gmail.readonly que ya tenemos; no requiere reconectar."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), GOOGLE_SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(_timeout_request())
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress")
    except Exception:
        return None


def start_oauth_flow() -> Dict[str, Any]:
    """Inicia el flujo OAuth abriendo el browser. Guarda el token al terminar.

    Devuelve un dict con {success, email, error}. Si error, success=False.
    El flujo abre el browser en http://localhost:8080 para que el usuario
    autorice; InstalledAppFlow captura el codigo automaticamente.
    """
    with _oauth_lock:
        if not _google_libs_available():
            return {
                "success": False,
                "error": "google-api-python-client no esta instalado. Ejecuta: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2",
            }
        creds_dict = _load_client_credentials()
        if not creds_dict:
            return {
                "success": False,
                "error": "Falta configurar client_id / client_secret en Settings (seccion Google).",
            }
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow

            client_config = {
                "installed": {
                    "client_id": creds_dict["client_id"],
                    "client_secret": creds_dict["client_secret"],
                    "redirect_uris": ["http://localhost:8080"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, GOOGLE_SCOPES)
            # open_browser=True abre el browser del sistema automaticamente.
            # El usuario autoriza y Google redirige a localhost:8080.
            creds = flow.run_local_server(
                port=8080,
                open_browser=True,
                success_message="Aithera conectado a Google correctamente. Puedes cerrar esta ventana.",
            )
            TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            TOKEN_PATH.write_text(creds.to_json())
            # El email real: primero intentamos el id_token, si no via Gmail.
            # Lo cacheamos en el token json para /email/status posterior.
            email = _extract_email_from_token(creds) or _fetch_email_via_gmail()
            if email:
                try:
                    data = json.loads(TOKEN_PATH.read_text())
                    data["email"] = email
                    TOKEN_PATH.write_text(json.dumps(data))
                except Exception:
                    pass
            return {
                "success": True,
                "email": email,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"{type(e).__name__}: {e}",
            }


def _extract_email_from_token(creds) -> Optional[str]:
    """Intenta sacar el email del token. Si falla, devuelve el client_id."""
    try:
        if hasattr(creds, "id_token") and creds.id_token:
            # El id_token es JWT, el email esta en el payload.
            import base64
            payload_b64 = creds.id_token.split(".")[1]
            # Padding
            payload_b64 += "=" * (-len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            return payload.get("email")
    except Exception:
        pass
    return None


def disconnect() -> bool:
    """Borra el token. Devuelve True si se borro algo."""
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
        return True
    return False