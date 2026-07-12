# Secrets Managers

## Resumen

**Secrets managers** son herramientas dedicadas para almacenar secrets (HashiCorp Vault, AWS Secrets Manager, etc.). **NO usado en Aithera** (overkill para single-user local).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Comparativa

| Manager | Type | Cost | Aithera |
|---|---|---|---|
| **HashiCorp Vault** | self-hosted OSS | free + infra | ⏳ overkill |
| **AWS Secrets Manager** | cloud managed | $0.40/secret/mes | ❌ |
| **HashiCorp Cloud** | managed | tiered | ❌ |
| **Azure Key Vault** | cloud managed | $0.03/10k ops | ❌ |
| **Doppler** | SaaS | $0/seat (free tier) | ⏳ |
| **1Password CLI** | consumer | $3/mes | ❌ |
| **Infisical** | OSS + cloud | free | ⏳ |

## Para Aithera

- ❌ **NO** usa secrets manager externo (overkill).
- ✅ DPAPI + Keychain + libsecret (OS-level).

## Cuándo usar secrets manager

- ✅ Multi-user SaaS (secrets centralizados).
- ✅ Distributed systems (microservices).
- ❌ Single-user desktop.

## Fuentes

1. https://www.vaultproject.io/
2. https://infisical.com/

## Nivel de confianza

**85%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified