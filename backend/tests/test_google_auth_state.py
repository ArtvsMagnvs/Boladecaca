# tests/test_google_auth_state.py
#
# AUTH-1 (2026-07-23): estados de conexión de Google + refresco robusto +
# preservación del email cacheado. Sin red: se falsean las google-libs y el
# refresco vía monkeypatch. TOKEN_PATH se redirige a un tmp para no tocar
# %APPDATA%/Aithera/google_token.json del usuario real.

import json
import pytest

from app.integrations import google_auth as ga


@pytest.fixture
def tmp_token(tmp_path, monkeypatch):
    """Redirige TOKEN_PATH a un archivo temporal por test."""
    p = tmp_path / "google_token.json"
    monkeypatch.setattr(ga, "TOKEN_PATH", p)
    return p


# ---------------------------------------------------------------------------
# connection_state(): clasificación por escenario
# ---------------------------------------------------------------------------

def test_state_libs_missing(monkeypatch):
    monkeypatch.setattr(ga, "_google_libs_available", lambda: False)
    assert ga.connection_state() == "libs_missing"


def test_state_no_credentials(monkeypatch):
    monkeypatch.setattr(ga, "_google_libs_available", lambda: True)
    monkeypatch.setattr(ga, "has_client_credentials", lambda: False)
    assert ga.connection_state() == "no_credentials"


def test_state_no_token(monkeypatch, tmp_token):
    monkeypatch.setattr(ga, "_google_libs_available", lambda: True)
    monkeypatch.setattr(ga, "has_client_credentials", lambda: True)
    # tmp_token no existe todavía -> nunca se conectó
    assert not tmp_token.exists()
    assert ga.connection_state() == "no_token"


def test_state_connected_token_valido(monkeypatch, tmp_token):
    monkeypatch.setattr(ga, "_google_libs_available", lambda: True)
    monkeypatch.setattr(ga, "has_client_credentials", lambda: True)
    tmp_token.write_text(json.dumps({"token": "x", "email": "yo@example.com"}))

    class _Creds:
        valid = True
        expired = False
        refresh_token = "r"

    monkeypatch.setattr(ga, "_load_and_refresh", lambda: (_Creds(), "connected"))
    # (probamos connection_state con el helper real más abajo; aquí sólo el atajo)
    assert ga.connection_state() == "connected"


def test_state_revoked_por_invalid_grant(monkeypatch, tmp_token):
    """Token expirado + refresh_token inválido (invalid_grant) -> revoked."""
    monkeypatch.setattr(ga, "_google_libs_available", lambda: True)
    monkeypatch.setattr(ga, "has_client_credentials", lambda: True)
    tmp_token.write_text(json.dumps({"token": "x", "email": "yo@example.com"}))

    class _Creds:
        valid = False
        expired = True
        refresh_token = "r"
        def refresh(self, _req):
            raise Exception("('invalid_grant: Token has been expired or revoked.')")

    class _CredsFactory:
        @staticmethod
        def from_authorized_user_file(path, scopes):
            return _Creds()

    import sys, types
    fake_mod = types.ModuleType("google.oauth2.credentials")
    fake_mod.Credentials = _CredsFactory
    monkeypatch.setitem(sys.modules, "google.oauth2.credentials", fake_mod)
    monkeypatch.setattr(ga, "_timeout_request", lambda: object())

    assert ga.connection_state() == "revoked"


def test_state_expired_por_fallo_transitorio(monkeypatch, tmp_token):
    """Token expirado + refresco falla por red (timeout) -> expired (reintentar)."""
    monkeypatch.setattr(ga, "_google_libs_available", lambda: True)
    monkeypatch.setattr(ga, "has_client_credentials", lambda: True)
    tmp_token.write_text(json.dumps({"token": "x", "email": "yo@example.com"}))

    class _Creds:
        valid = False
        expired = True
        refresh_token = "r"
        def refresh(self, _req):
            raise Exception("timed out")

    class _CredsFactory:
        @staticmethod
        def from_authorized_user_file(path, scopes):
            return _Creds()

    import sys, types
    fake_mod = types.ModuleType("google.oauth2.credentials")
    fake_mod.Credentials = _CredsFactory
    monkeypatch.setitem(sys.modules, "google.oauth2.credentials", fake_mod)
    monkeypatch.setattr(ga, "_timeout_request", lambda: object())

    assert ga.connection_state() == "expired"


def test_state_revoked_sin_refresh_token(monkeypatch, tmp_token):
    """Token expirado y SIN refresh_token -> revoked (no hay forma de recuperar)."""
    monkeypatch.setattr(ga, "_google_libs_available", lambda: True)
    monkeypatch.setattr(ga, "has_client_credentials", lambda: True)
    tmp_token.write_text(json.dumps({"token": "x"}))

    class _Creds:
        valid = False
        expired = True
        refresh_token = None

    class _CredsFactory:
        @staticmethod
        def from_authorized_user_file(path, scopes):
            return _Creds()

    import sys, types
    fake_mod = types.ModuleType("google.oauth2.credentials")
    fake_mod.Credentials = _CredsFactory
    monkeypatch.setitem(sys.modules, "google.oauth2.credentials", fake_mod)

    assert ga.connection_state() == "revoked"


def test_state_token_ilegible_es_revoked(monkeypatch, tmp_token):
    """Token json corrupto -> revoked (hay que reconectar)."""
    monkeypatch.setattr(ga, "_google_libs_available", lambda: True)
    monkeypatch.setattr(ga, "has_client_credentials", lambda: True)
    tmp_token.write_text("{ esto no es json valido")

    class _CredsFactory:
        @staticmethod
        def from_authorized_user_file(path, scopes):
            raise ValueError("bad json")

    import sys, types
    fake_mod = types.ModuleType("google.oauth2.credentials")
    fake_mod.Credentials = _CredsFactory
    monkeypatch.setitem(sys.modules, "google.oauth2.credentials", fake_mod)

    assert ga.connection_state() == "revoked"


# ---------------------------------------------------------------------------
# _write_token_preserving_email(): el refresco NO debe borrar el email cacheado
# ---------------------------------------------------------------------------

def test_refresh_preserva_email_cacheado(tmp_token):
    # Estado previo: token con email cacheado.
    tmp_token.write_text(json.dumps({"token": "viejo", "email": "yo@example.com"}))

    class _Creds:
        def to_json(self):
            # Lo que devuelve google-auth tras refrescar: SIN nuestro campo email.
            return json.dumps({"token": "nuevo", "refresh_token": "r"})

    ga._write_token_preserving_email(_Creds())

    data = json.loads(tmp_token.read_text())
    assert data["token"] == "nuevo", "el token debe actualizarse"
    assert data["email"] == "yo@example.com", "el email cacheado NO debe perderse"


def test_get_credentials_delega_en_load_and_refresh(monkeypatch):
    """get_credentials() sigue devolviendo creds|None vía el helper compartido."""
    sentinel = object()
    monkeypatch.setattr(ga, "_load_and_refresh", lambda: (sentinel, "connected"))
    assert ga.get_credentials() is sentinel

    monkeypatch.setattr(ga, "_load_and_refresh", lambda: (None, "revoked"))
    assert ga.get_credentials() is None
