# SOP — Configurar OAuth

## Cuándo
Configurar OAuth2 + PKCE para un provider nuevo (Google ya está, Microsoft no).

## Pasos

1. **Crear app en provider console**:
   - Google: https://console.cloud.google.com/apis/credentials
   - Microsoft: https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps

2. **Configurar redirect URI**: `http://localhost:8000/api/{provider}/auth/callback`

3. **Configurar scopes** (mínimo necesario):
   - Google: `gmail.readonly gmail.send calendar`
   - Microsoft: `Mail.Read Mail.Send Calendars.ReadWrite`

4. **Guardar credentials en Aithera**:
```bash
curl -X POST http://localhost:8000/api/email/auth/credentials \
  -H "Content-Type: application/json" \
  -d '{"client_id": "...", "client_secret": "..."}'
```

5. **Iniciar flow**:
```bash
curl -X POST http://localhost:8000/api/email/auth/start
# → { auth_url: "https://..." }
```

6. **User autoriza** (browser).

7. **Callback intercambia code por tokens**.

## Verificación

- [ ] Token guardado cifrado (DPAPI).
- [ ] Refresh token funciona.

## Referencias cruzadas

- [JWIKI-152 google-oauth-flow.md](../09_INTEGRATIONS/google-oauth-flow.md)

---

*Estado: 🟢 verified*