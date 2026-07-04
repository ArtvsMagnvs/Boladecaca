# tests/test_secrets.py
#
# V0.8 (PLAN_MAESTRO_2026, hardening): cifrado de secretos en reposo. En el
# entorno de test no hay DPAPI (no es Windows), asi que se ejercita la ruta
# fallback 'plain:' — la logica de formato/idempotencia/legado es la misma que
# en produccion; solo cambia el motor de cifrado. En Windows el round-trip usa
# DPAPI de forma transparente por el mismo prefijo.

from app.core import secrets


def test_round_trip():
    assert secrets.decrypt(secrets.encrypt("hola-token-123")) == "hola-token-123"


def test_encrypt_cambia_el_valor_almacenado():
    stored = secrets.encrypt("secreto")
    assert stored != "secreto"          # no queda en claro
    assert secrets.is_encrypted(stored)  # lleva prefijo reconocible


def test_idempotente_no_recifra():
    once = secrets.encrypt("abc")
    twice = secrets.encrypt(once)        # ya cifrado -> se devuelve igual
    assert once == twice
    assert secrets.decrypt(twice) == "abc"


def test_legado_texto_plano_se_devuelve_tal_cual():
    # valores guardados antes del cifrado (sin prefijo) siguen leyendose
    assert secrets.decrypt("token-viejo-sin-cifrar") == "token-viejo-sin-cifrar"


def test_vacios():
    assert secrets.encrypt("") == ""
    assert secrets.decrypt("") == ""
    assert secrets.encrypt(None) == ""


def test_mask_no_revela_el_secreto():
    m = secrets.mask("1234567890abcd")
    assert "1234567890" not in m
    assert m.endswith("abcd")
