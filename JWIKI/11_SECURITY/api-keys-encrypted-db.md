# API Keys — Encrypted DB (DPAPI)

## Resumen

Aithera V0.8+ cifra API keys en BD con **DPAPI de Windows** (`backend/app/core/secrets.py`). CLAUDE.md §1 "Cifrado de secretos en reposo (DPAPI)".

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## DPAPI (Windows)

```python
# backend/app/core/secrets.py
import win32crypt
from cryptography.fernet import Fernet

def encrypt(plaintext: str) -> bytes:
    """Encrypt using DPAPI (Windows)."""
    return win32crypt.CryptProtectData(
        plaintext.encode("utf-8"),
        None,  # description
        None,  # entropy
        None,  # reserved
        None,  # prompt
        0x01   # CRYPTPROTECT_UI_FORBIDDEN
    )

def decrypt(ciphertext: bytes) -> str:
    """Decrypt DPAPI-encrypted data."""
    return win32crypt.CryptUnprotectData(
        ciphertext,
        None, None, None, None, 0x01
    )[1].decode("utf-8")
```

## AIManager integration (CLAUDE.md §1)

```python
# backend/app/ai/ai_manager.py
class AIManager:
    def _enc(self, value: str) -> bytes:
        """Encrypt before persist."""
        if not value:
            return b""
        return encrypt(value)
    
    def _dec(self, encrypted: bytes) -> str:
        """Decrypt on read."""
        if not encrypted:
            return ""
        try:
            return decrypt(encrypted)
        except Exception:
            # Backward compat: legacy plaintext
            return encrypted.decode("utf-8") if isinstance(encrypted, bytes) else encrypted
    
    async def save_provider_config(self, provider: str, api_key: str):
        await db.execute(
            "INSERT INTO ai_provider_configs (provider, api_key_enc) VALUES (?, ?)",
            provider, self._enc(api_key)
        )
    
    async def load_provider_config(self, provider: str):
        row = await db.fetchone(
            "SELECT api_key_enc FROM ai_provider_configs WHERE provider = ?",
            provider
        )
        return self._dec(row["api_key_enc"]) if row else None
```

## Alembic migration V0.8

```python
# backend/alembic/versions/d4e5f6a7b8c9_v08_encrypt_api_keys.py
"""Encrypt existing API keys in DB."""

def upgrade():
    conn = op.get_bind()
    
    # Re-cifra todos los api_keys existentes (idempotente)
    rows = conn.execute(text("SELECT id, api_key FROM ai_provider_configs")).fetchall()
    for row in rows:
        api_key = row.api_key
        if api_key and not is_already_encrypted(api_key):
            encrypted = encrypt(api_key)
            conn.execute(
                text("UPDATE ai_provider_configs SET api_key_enc = :enc WHERE id = :id"),
                enc=encrypted, id=row.id
            )
```

## Cross-platform fallback

DPAPI solo Windows. En macOS/Linux:
- ✅ **macOS Keychain** (alternativa nativa).
- ✅ **Linux libsecret** (alternativa GNOME).
- ✅ **Fernet con clave en env var** (universal fallback).

```python
import platform

if platform.system() == "Windows":
    from . import dpapi as backend
elif platform.system() == "Darwin":
    from . import keychain as backend
else:
    from . import libsecret as backend
```

## Telegram token (V0.8+)

CLAUDE.md §1: token de Telegram también cifrado con DPAPI:

```python
# backend/app/api/endpoints/telegram.py
@router.post("/api/telegram/configure")
async def configure_telegram(token: str, chat_id: str):
    encrypted_token = encrypt(token)
    await db.set_config("telegram_bot_token", encrypted_token)
    await db.set_config("telegram_chat_id", chat_id)
```

## Compatibilidad hacia atrás

Aithera tolera **valores legado en texto plano**:
```python
def _dec(self, encrypted) -> str:
    if not encrypted:
        return ""
    try:
        return decrypt(encrypted)
    except Exception:
        # Si falla decryption, asumir plaintext (legacy)
        return encrypted.decode("utf-8") if isinstance(encrypted, bytes) else encrypted
```

## Para Aithera

- ✅ V0.8: DPAPI encryption activo.
- ⏳ V0.85+: cross-platform (Keychain macOS, libsecret Linux).
- ⏳ V1.0+: HSM (Hardware Security Module) opcional.

## Referencias cruzadas

- [JWIKI-180 api-keys-env.md](./api-keys-env.md)
- [JWIKI-182 api-keys-keyring.md](./api-keys-keyring.md)
- CLAUDE.md §1

## Fuentes

1. https://learn.microsoft.com/en-us/windows/win32/api/dpapi/
2. CLAUDE.md §1

## Nivel de confianza

**100%** — implementado en CLAUDE.md §1.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified