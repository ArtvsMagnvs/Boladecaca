# backend/app/integrations/__init__.py
#
# V0.7 (Fase 4): integraciones externas de Aithera.
# - Google (Gmail + Calendar) OAuth 2.0

from .google_auth import (
    is_connected as google_is_connected,
    has_client_credentials as google_has_client_credentials,
    is_google_libs_available as google_is_libs_available,
    get_connected_email as google_get_connected_email,
    start_oauth_flow as google_start_oauth,
    disconnect as google_disconnect,
    save_client_credentials as google_save_client_credentials,
    get_credentials_source as google_get_credentials_source,
)


__all__ = [
    "google_is_connected",
    "google_has_client_credentials",
    "google_is_libs_available",
    "google_get_connected_email",
    "google_start_oauth",
    "google_disconnect",
    "google_save_client_credentials",
    "google_get_credentials_source",
]