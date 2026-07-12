# SOP — Cambiar proveedor IA activo

## Cuándo
Quieres cambiar el provider principal (e.g., de OpenAI a DeepSeek por costo).

## Pasos

1. **Vía UI**: Settings → AI Providers → Activar nuevo.

2. **Vía API**:
```bash
curl -X POST http://localhost:8000/api/ai/activate \
  -d '{"provider": "deepseek"}'
```

3. **Verificar**:
```bash
curl http://localhost:8000/api/ai/status
# → { "active": "deepseek", "models": [...] }
```

4. **Test chat**:
```bash
curl -X POST http://localhost:8000/api/chat \
  -d '{"message": "test"}'
```

## Verificación

- [ ] Status muestra nuevo provider.
- [ ] Chat usa nuevo provider.

## Referencias cruzadas

- [JWIKI-044 selection-guide.md](../05_AI_PROVIDERS/selection-guide.md)

---

*Estado: 🟢 verified*