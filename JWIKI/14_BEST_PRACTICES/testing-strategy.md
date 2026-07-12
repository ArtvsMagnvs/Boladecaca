# Testing Strategy

## Resumen

**Testing strategy** Aithera V0.7.3+ incluye smoke + contracts + integration. Ver CLAUDE.md §1 (tests list).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Tests Aithera V0.7.3+

```
backend/tests/
├── test_smoke.py            # boot test
├── test_email_contracts.py  # API frozen routes
├── test_email_triage.py     # 7-category classifier
├── test_email_autonomy_digest.py  # auto-reply + digest
├── test_email_assistant.py  # meeting detection
├── test_reasoning_filter.py # B21 (V0.8)
├── test_gateway.py          # Gateway (V0.8)
├── test_telegram_adapter.py # Telegram (V0.8)
└── test_secrets.py          # DPAPI (V0.8)
```

## Levels

| Level | Use | Speed |
|---|---|---|
| **Smoke** | boot, imports | < 1s |
| **Unit** | funciones individuales | < 100ms |
| **Contract** | API routes frozen | < 1s |
| **Integration** | multiple components | < 5s |
| **E2E** | full flow (Playwright) | < 30s |

## Test patterns

```python
# Contract test
def test_get_email_inbox_returns_200():
    response = client.get("/api/email/inbox?max_results=20")
    assert response.status_code == 200
    assert "messages" in response.json()

# Integration test
async def test_send_email_with_approval():
    # Setup
    rule = create_rule(pattern="from:boss@", autonomy="propose")
    
    # Action
    response = await send_email(to="boss@co.com", subject="...", body="...")
    
    # Verify
    assert response.status_code == 202  # pending approval
    assert ApprovalRequest.objects.count() == 1
```

## Coverage

Aithera V0.7.3+ target: **>70% coverage** en routers críticos (email).

## Para Aithera

- ✅ V0.7.3: smoke + contracts + email triage.
- ✅ V0.8: B21 + gateway + telegram + secrets.

## Referencias cruzadas

- CLAUDE.md §1

## Fuentes

1. https://docs.pytest.org/
2. CLAUDE.md §1

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified