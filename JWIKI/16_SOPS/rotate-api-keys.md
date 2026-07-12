# SOP — Rotación API keys

## Cuándo
Cada 90 días (seguridad) o si se compromete una key.

## Pasos

1. **Generar nueva API key** en provider console:
   - OpenAI: https://platform.openai.com/api-keys
   - Anthropic: https://console.anthropic.com/

2. **Update en Aithera** (Settings UI o API):
```bash
curl -X POST http://localhost:8000/api/ai/configure \
  -d '{"provider": "openai", "api_key": "sk-NEW..."}'
```

3. **Verificar** nueva key funciona:
```bash
curl -X POST http://localhost:8000/api/chat \
  -d '{"message": "test", "provider": "openai"}'
```

4. **Revocar old key** en provider console.

5. **Backup BD** (snapshot post-rotación).

## Verificación

- [ ] Chat funciona con nueva key.
- [ ] Old key revocada en provider.

## Referencias cruzadas

- [JWIKI-181 api-keys-encrypted-db.md](../11_SECURITY/api-keys-encrypted-db.md)

---

*Estado: 🟢 verified*