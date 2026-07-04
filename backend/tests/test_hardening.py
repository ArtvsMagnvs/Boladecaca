# tests/test_hardening.py
#
# V0.8 Security Hardening (PLAN_MAESTRO_2026): las API keys se guardan CIFRADAS
# en reposo y el CORS deja de ser wildcard. Estos tests fijan ambos invariantes.

from app.core import secrets


# ----------------------------------------------------------------------
# API keys cifradas en reposo
# ----------------------------------------------------------------------

def test_add_or_update_provider_cifra_la_key(db_session):
    """La key se guarda cifrada en la BD pero el proveedor se instancia con la
    key en claro (invariante del hardening)."""
    from app.ai.ai_manager import ai_manager
    from app.db.database import SessionLocal
    from app.db.models import AIProviderConfig

    ok = ai_manager.add_or_update_provider(
        "openai", model="gpt-4", api_key="sk-super-secret-9999"
    )
    assert ok

    db = SessionLocal()
    try:
        row = db.query(AIProviderConfig).filter_by(provider="openai").first()
        assert row is not None
        assert row.api_key != "sk-super-secret-9999"        # NO en texto plano
        assert secrets.is_encrypted(row.api_key)            # lleva prefijo cifrado
        assert secrets.decrypt(row.api_key) == "sk-super-secret-9999"
    finally:
        db.close()

    # el proveedor vivo tiene la key descifrada, listo para llamar a la API
    assert ai_manager.providers["openai"].api_key == "sk-super-secret-9999"


def test_provider_preview_usa_la_key_descifrada(db_session):
    """El preview '...abcd' debe mostrar los ultimos 4 de la key REAL, no del
    blob cifrado."""
    from app.ai.ai_manager import ai_manager

    ai_manager.add_or_update_provider("grok", model="grok-4", api_key="key-XYZ-abcd")
    configured = {p["provider"]: p for p in ai_manager.list_configured()}
    grok = configured["grok"]
    assert grok["has_api_key"] is True
    assert grok["api_key_preview"] == "...abcd"


# ----------------------------------------------------------------------
# CORS restringido (ya no wildcard)
# ----------------------------------------------------------------------

def test_cors_no_es_wildcard():
    import app.main as m
    assert "*" not in m._default_cors_origins
    # localhost dev y build local permitidos; Electron (file://) via 'null'
    assert "http://localhost:5173" in m._default_cors_origins
    assert "null" in m._default_cors_origins
