# Data Encryption at Rest

## Resumen

**Data encryption at rest** cifra datos cuando están en disco (no en tránsito). Aithera V0.8+ implementa para secrets (DPAPI). Datos completos (SQLite/PostgreSQL) **NO cifrados** todavía.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Aithera V0.7.3 → V0.8+

| Data | V0.7.3 | V0.8+ |
|---|---|---|
| API keys en BD | ❌ plaintext | ✅ DPAPI |
| Telegram token | ❌ plaintext | ✅ DPAPI |
| OAuth tokens | ❌ plaintext | ✅ DPAPI |
| User emails (cache) | ❌ plaintext | ❌ |
| Conversations | ❌ plaintext | ❌ |
| Documents | ❌ plaintext | ❌ |
| ChromaDB | ❌ plaintext | ❌ |

## Por qué no cifrarlo todo

- ⚠️ **Performance**: cifrar/descifrar cada query adds overhead.
- ⚠️ **Search**: no puedes hacer LIKE queries en texto cifrado.
- ⚠️ **Complexity**: key management es complejo.
- ✅ **Threat model**: single-user local, low attack surface.

## Encryption options

| Opción | Pros | Con |
|---|---|---|
| **Column-level** (DPAPI por campo) | granular | requiere app aware |
| **Tablespace** (PostgreSQL TDE) | transparente | enterprise only |
| **Volume** (BitLocker, FileVault) | OS-level | requiere hardware |
| **Full DB** (SQLCipher) | portable | performance hit |

## Aithera V0.85+ plan

- ✅ **V0.85**: cifrar PII específica (emails, conversations) con Fernet.
- ⏳ **V1.0**: opcional full DB encryption (SQLCipher).
- ⏳ **V1.5**: integration con OS keyring para key storage.

## Para Aithera

- ✅ V0.8: API keys cifrados.
- ⏳ V0.85+: PII cifrada.

## Referencias cruzadas

- [JWIKI-181 api-keys-encrypted-db.md](./api-keys-encrypted-db.md)
- [JWIKI-182 api-keys-keyring.md](./api-keys-keyring.md)

## Fuentes

1. https://en.wikipedia.org/wiki/Transparent_Data_Encryption

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified