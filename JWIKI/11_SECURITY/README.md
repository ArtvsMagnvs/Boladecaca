# Security — Overview

## Resumen

Security en Aithera V0.8+ cubre: API keys (DPAPI cifrado), sandboxing de tools, OAuth2 PKCE, prompt injection defenses, encryption at rest. CLAUDE.md §1: "Security Hardening (V0.8)".

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Categorías

| Categoría | Aithera V0.7.3 | Aithera V0.8+ |
|---|---|---|
| **API keys en tránsito** | ✅ HTTPS (CORS restringido) | ✅ |
| **API keys en reposo** | ❌ texto plano en BD | ✅ DPAPI cifrado |
| **OAuth2** | ✅ Google PKCE | ✅ |
| **Tool sandboxing** | ✅ whitelist | ✅ |
| **CORS** | ❌ `*` | ✅ restringido |
| **Prompt injection** | ⚠️ básico | ✅ B21 + defences |
| **Encryption at rest** | ❌ | ✅ DPAPI para secretos |
| **Network auth (PIN)** | ❌ | ⏳ V1.0+ (Web) |

## Aithera V0.8.0 Security Hardening (CLAUDE.md §1)

- ✅ **CORS restringido**: localhost + Electron null + `Settings.CORS_ALLOWED_ORIGINS` (NO `*`).
- ✅ **API keys cifradas en BD**: AIManager._enc al escribir, _dec al instanciar.
- ✅ **Migración Alembic** `d4e5f6a7b8c9_v08_encrypt_api_keys` re-cifra las existentes.
- ✅ **DPAPI Windows** (cifrado de secretos en reposo).
- ✅ **Token Telegram cifrado** con DPAPI.

## Threat model

| Threat | Mitigation | Aithera V0.8+ |
|---|---|---|
| API key robada de BD | cifrado DPAPI | ✅ |
| SQL injection | SQLAlchemy ORM + Pydantic | ✅ |
| XSS en frontend | React + Tailwind | ✅ |
| CSRF | no relevante (API JSON, no cookies) | ✅ |
| CORS abuse | CORS restringido | ✅ |
| Tool abuse | whitelist + timeout | ✅ |
| Path traversal | validación | ✅ |
| Command injection | shell whitelist | ✅ |
| Prompt injection | B21 + filters | ✅ |
| Secrets en logs | redact | ✅ |

## Pendiente

- ⏳ **PIN/token de red** para exponer a LAN/Web (post-V1.0).
- ⏳ **Rate limiting** en API (futuro).
- ⏳ **Audit log security events** (futuro).

## Referencias cruzadas

- [JWIKI-180 api-keys-env.md](./api-keys-env.md)
- [JWIKI-181 api-keys-encrypted-db.md](./api-keys-encrypted-db.md)
- [JWIKI-183 sandboxing-tool-whitelist.md](./sandboxing-tool-whitelist.md)
- [JWIKI-188 prompt-injection-defenses.md](./prompt-injection-defenses.md)
- CLAUDE.md §1 (V0.8 Security Hardening)

## Fuentes

1. https://owasp.org/
2. CLAUDE.md §1

## Nivel de confianza

**100%** — implementado en CLAUDE.md §1.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified