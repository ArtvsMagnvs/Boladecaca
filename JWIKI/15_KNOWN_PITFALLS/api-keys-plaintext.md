# API Keys Plaintext BD — V0.7.3

## Resumen

**API keys en plaintext** en BD fueron un riesgo crítico de V0.7.3. **Fixed en V0.8** con DPAPI.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Risk

- ⚠️ Robo de BD → todas las API keys expuestas.
- ⚠️ Insider threat → DBA con acceso ve keys.
- ⚠️ Backup leaks.

## Fix V0.8 (CLAUDE.md §1)

```python
# AIManager
def _enc(self, value: str) -> bytes:
    return encrypt(value)

def _dec(self, encrypted: bytes) -> str:
    try:
        return decrypt(encrypted)
    except Exception:
        return encrypted.decode("utf-8")  # legacy compat
```

## Migration

`alembic/versions/d4e5f6a7b8c9_v08_encrypt_api_keys.py`:
- Re-cifra todas las keys existentes (idempotente).

## Para Aithera

- ✅ V0.8: DPAPI cifrado.

## Referencias cruzadas

- [JWIKI-181 api-keys-encrypted-db.md](../11_SECURITY/api-keys-encrypted-db.md)
- CLAUDE.md §1, §16

## Fuentes

1. CLAUDE.md §16

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified