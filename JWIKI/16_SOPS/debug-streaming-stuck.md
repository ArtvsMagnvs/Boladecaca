# SOP — Debug streaming stuck

## Síntomas
- Chat queda colgado en "..." sin recibir respuesta.
- SSE stream no envía chunks.

## Pasos

1. **Verificar backend responde**:
```bash
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"hi","stream":true}'
```

2. **Revisar logs** del backend:
```bash
# Buscar "stream" en logs
grep -i "stream" backend.log
```

3. **Verificar provider activo**:
```bash
curl http://localhost:8000/api/ai/status
```

4. **Test con provider alternativo**:
```bash
# Settings → cambiar a "deepseek-flash"
```

5. **Verificar network** (si es provider cloud):
```bash
ping api.openai.com
```

6. **Si persiste**: revisar `app/ai/reasoning_filter.py` (B21 puede truncar).

## Fix comunes

- ✅ Cambio de provider.
- ✅ Restart backend.
- ✅ Limpiar cache de sentence-transformers.

## Referencias cruzadas

- [JWIKI-230 streaming-closure-bug.md](../15_KNOWN_PITFALLS/streaming-closure-bug.md)

---

*Estado: 🟢 verified*