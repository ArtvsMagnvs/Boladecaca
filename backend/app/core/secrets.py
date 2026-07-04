# app/core/secrets.py
#
# V0.8 (PLAN_MAESTRO_2026, hardening): cifrado de secretos en reposo para la
# BD local. Motor por defecto: DPAPI de Windows (win32crypt), que ata el
# descifrado a la cuenta de usuario de Windows — no hay fichero de clave que
# proteger. Primer inquilino: el token del bot de Telegram; despues las API
# keys de los proveedores IA reutilizaran este mismo helper.
#
# Formato almacenado (prefijo -> como descifrar):
#   "dpapi:<b64>"  cifrado con DPAPI (Windows).
#   "plain:<b64>"  fallback reversible (entornos sin DPAPI: tests, Linux).
#   "<sin prefijo>"  legado en texto plano -> se devuelve tal cual (migracion).
#
# Asi, leer un valor guardado antes del cifrado sigue funcionando, y un valor
# nuevo se descifra por su prefijo sin ambiguedad.

from __future__ import annotations

import base64

_DPAPI = "dpapi:"
_PLAIN = "plain:"
_ENTROPY = b"aithera-secrets-v1"  # entropia adicional de DPAPI (no es la clave)


def _dpapi_available() -> bool:
    try:
        import win32crypt  # noqa: F401  (pywin32, solo Windows)
        return True
    except Exception:
        return False


def is_encrypted(stored: str) -> bool:
    """True si el valor ya esta en formato cifrado/marcado de este helper."""
    return bool(stored) and stored.startswith((_DPAPI, _PLAIN))


def encrypt(plaintext: str) -> str:
    """Cifra un secreto para guardarlo en la BD. Idempotente: si ya viene en
    formato de este helper, lo devuelve sin recifrar."""
    if not plaintext:
        return ""
    if is_encrypted(plaintext):
        return plaintext
    data = plaintext.encode("utf-8")
    if _dpapi_available():
        import win32crypt
        blob = win32crypt.CryptProtectData(data, "aithera", _ENTROPY, None, None, 0)
        return _DPAPI + base64.b64encode(blob).decode("ascii")
    # fallback (no Windows / sin pywin32): marcado pero NO seguro. En Windows
    # real nunca se llega aqui. Sirve para que la app arranque en dev/test.
    return _PLAIN + base64.b64encode(data).decode("ascii")


def decrypt(stored: str) -> str:
    """Descifra un valor guardado. Tolera: formato dpapi, plain, o legado en
    texto plano (sin prefijo, se devuelve tal cual)."""
    if not stored:
        return ""
    if stored.startswith(_DPAPI):
        raw = base64.b64decode(stored[len(_DPAPI):])
        import win32crypt
        _desc, data = win32crypt.CryptUnprotectData(raw, _ENTROPY, None, None, 0)
        return data.decode("utf-8")
    if stored.startswith(_PLAIN):
        return base64.b64decode(stored[len(_PLAIN):]).decode("utf-8")
    # legado: valor en texto plano previo al cifrado
    return stored


def mask(plaintext: str, visible: int = 4) -> str:
    """Representacion segura para logs/UI: '••••abcd' (nunca el secreto entero)."""
    if not plaintext:
        return ""
    tail = plaintext[-visible:] if len(plaintext) > visible else ""
    return "•" * 8 + tail
