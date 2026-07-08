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


def get_credentials() -> Optional[Any]:
    """Obtiene credenciales validas. Refresca si han expirado.

    Devuelve None si:
      - las google libs no estan instaladas
      - no hay token guardado (el usuario no ha hecho OAuth aun)
      - las credenciales expiraron y no hay refresh_token
    """
    if not _google_libs_available():
        return None
    if not TOKEN_PATH.exists():
        return None
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), GOOGLE_SCOPES)
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json())
            return creds
        return None
    except Exception as e:
        print(f"[google_auth] error refrescando credenciales: {e}")
        return None


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
            creds.refresh(Request())
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