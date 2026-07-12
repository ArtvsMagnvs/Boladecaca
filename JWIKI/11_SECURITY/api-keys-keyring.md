# OS Keyring — Alternativa a DPAPI

## Resumen

**OS Keyring** (Windows Credential Manager, macOS Keychain, GNOME libsecret) es alternativa cross-platform a DPAPI para almacenar secrets. **NO usado en Aithera V0.8.0** (solo DPAPI Windows). V0.85+ considera.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## keyring library (Python)

```bash
pip install keyring
```

```python
import keyring

# Store
keyring.set_password("aithera", "openai_api_key", "sk-...")
keyring.set_password("aithera", "telegram_bot_token", "...")

# Retrieve
api_key = keyring.get_password("aithera", "openai_api_key")
```

## Backends

| OS | Backend | Security |
|---|---|---|
| **Windows** | Credential Manager | DPAPI |
| **macOS** | Keychain | Hardware-backed (Secure Enclave) |
| **Linux GNOME** | libsecret | Login keyring |
| **Linux KDE** | KWallet | login keyring |
| **Headless Linux** | python-keyring fallback (file) | ❌ weak |

## Aithera V0.85+ plan

```python
# backend/app/core/secrets.py (cross-platform)
import platform

def get_secret(key: str) -> str:
    if platform.system() == "Windows":
        from . import dpapi_backend
        return dpapi_backend.get(key)
    elif platform.system() == "Darwin":
        from . import keychain_backend
        return keychain_backend.get(key)
    else:
        from . import libsecret_backend
        return libsecret_backend.get(key)
```

## Pros vs DPAPI

| Aspecto | DPAPI | OS Keyring |
|---|---|---|
| Cross-platform | ❌ Windows only | ✅ Win/Mac/Linux |
| Hardware-backed | ❌ | ✅ Mac Secure Enclave |
| UX | transparent | may prompt for password |

## Para Aithera

- ❌ V0.8.0: DPAPI Windows only.
- ⏳ V0.85+: cross-platform keyring.
- ⏳ V1.0+: macOS/Linux oficiales.

## Referencias cruzadas

- [JWIKI-181 api-keys-encrypted-db.md](./api-keys-encrypted-db.md)
- [JWIKI-190 secrets-managers.md](./secrets-managers.md)

## Fuentes

1. https://pypi.org/project/keyring/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified