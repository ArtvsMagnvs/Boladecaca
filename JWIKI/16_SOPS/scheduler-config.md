# SOP — Configurar scheduler

## Cuándo
Configurar automation rules V0.9+ con APScheduler.

## Pasos

1. **Definir regla**:
```json
{
    "name": "Daily digest",
    "trigger": {"type": "cron", "expression": "0 9 * * *"},
    "action": {"type": "email.send", "args": {...}},
    "approval_required": false
}
```

2. **Guardar via API**:
```bash
curl -X POST http://localhost:8000/api/automation/rules \
  -d @rule.json
```

3. **Verificar**:
```bash
curl http://localhost:8000/api/automation/rules
```

4. **Testear manualmente**:
```bash
curl -X POST http://localhost:8000/api/automation/rules/1/run
```

## Verificación

- [ ] Job aparece en `apscheduler.get_jobs()`.
- [ ] Job se ejecuta al horario.
- [ ] Logs en automation_logs.

## Referencias cruzadas

- [JWIKI-170 apscheduler.md](../10_AUTOMATION/apscheduler.md)

---

*Estado: 🟢 verified*