# SOP — Debug OAuth refresh fail

## Síntomas
- "Token expired" errors después de 1h.
- Calendar/Gmail tools dejan de funcionar.

## Pasos

1. **Verificar token expiry**:
```bash
curl -X POST http://localhost:8000/api/email/auth/refresh
```

2. **Si falla**:
```bash
# Re-authorize
curl -X POST http://localhost:8000/api/email/auth/start
# → User opens URL in browser, authorizes
```

3. **Verificar refresh_token existe**:
```sql
SELECT refresh_token_enc FROM config WHERE key = 'google_refresh_token';
```

4. **Si vacío**: user debe re-autorizar completamente.

5. **Verificar client_id/secret correctos**:
```bash
curl http://localhost:8000/api/email/auth/credentials
```

## Causas comunes

- ❌ Refresh token revocado en Google console.
- ❌ User cambió password.
- ❌ Scopes insufficient (offline access no granted).

## Referencias cruzadas

- [JWIKI-152 google-oauth-flow.md](../09_INTEGRATIONS/google-oauth-flow.md)

---

*Estado: 🟢 verified*