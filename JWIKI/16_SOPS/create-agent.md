# SOP — Crear agente Aithera

## Cuándo
Necesitas un agent nuevo (e.g., "Researcher", "Coder").

## Pasos

1. **Crear agente** via API:
```bash
curl -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Researcher",
    "description": "You are a research assistant. Use web_search and memory_search.",
    "allowed_tools": ["memory_search", "web_search"],
    "max_execution_time": 3600
  }'
```

2. **Testear**:
```bash
curl -X POST http://localhost:8000/api/agents/1/execute \
  -d '{"input": "Research X"}'
```

3. **Verificar**:
- [ ] Agent creado en BD.
- [ ] Tools validados contra whitelist.
- [ ] Execution persiste en `agent_executions`.

## Para Aithera

- ✅ CRUD completo en `agent_manager.py` (CLAUDE.md §1).

## Referencias cruzadas

- [JWIKI-106 aithera-agent-manager.md](../06_AGENTS/aithera-agent-manager.md)

---

*Estado: 🟢 verified*