# Reglas Ejemplo — Predefinidas

## Resumen

Aithera V0.9+ podría incluir **reglas predefinidas** que el user puede activar con 1-click. Ejemplos útiles para single-user productivity.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Reglas predefinidas (sugeridas)

### 1. Daily digest

```json
{
    "name": "Daily morning digest",
    "description": "Email diario 9am con resumen del día",
    "trigger": {"type": "cron", "expression": "0 9 * * *"},
    "action": {
        "type": "email.send",
        "args": {
            "to": "{{user.email}}",
            "subject": "Buenos días - resumen del día",
            "template": "daily_digest",
            "data": {"include": ["calendar.today", "tasks.due_today", "emails.unread_priority"]}
        }
    },
    "approval_required": false
}
```

### 2. Archive newsletters > 30 days

```json
{
    "name": "Archive old newsletters",
    "trigger": {"type": "cron", "expression": "0 2 * * *"},
    "condition": {
        "field": "email.labels",
        "op": "contains",
        "value": "CATEGORY_PROMOTIONS"
    },
    "action": {
        "type": "email.archive",
        "args": {
            "filter": "label:CATEGORY_PROMOTIONS older_than:30d"
        }
    },
    "approval_required": false
}
```

### 3. Auto-archive GitHub notifications

```json
{
    "name": "Auto-archive GitHub notifications",
    "trigger": {"type": "event", "topic": "email.received"},
    "condition": {
        "field": "email.from",
        "op": "regex",
        "value": "^noreply@github\\.com$"
    },
    "action": {
        "type": "email.archive"
    },
    "approval_required": false
}
```

### 4. Daily standup summary

```json
{
    "name": "Daily standup",
    "trigger": {"type": "cron", "expression": "0 8 * * 1-5"},  # weekdays 8am
    "action": {
        "type": "chat.query",
        "args": {
            "prompt": "Resume lo que hice ayer y lo que tengo pendiente hoy, basado en mis emails y commits",
            "deliver_to": "telegram"
        }
    },
    "approval_required": false
}
```

### 5. Meeting conflict check

```json
{
    "name": "Detect meeting conflicts",
    "trigger": {"type": "event", "topic": "email.received"},
    "condition": {
        "field": "email.body",
        "op": "regex",
        "value": "(meeting|reuni[óo]n|call)"
    },
    "action": {
        "type": "calendar.detect_conflicts",
        "args": {"notify_via": "hub"}
    },
    "approval_required": false
}
```

### 6. Weekly review

```json
{
    "name": "Weekly review",
    "trigger": {"type": "cron", "expression": "0 18 * * 0"},  # domingo 6pm
    "action": {
        "type": "chat.query",
        "args": {
            "prompt": "Review semanal: proyectos activos, tareas completadas, próximos hitos",
            "deliver_to": "hub"
        }
    },
    "approval_required": false
}
```

### 7. Birthday reminders

```json
{
    "name": "Birthday reminders",
    "trigger": {"type": "cron", "expression": "0 8 * * *"},
    "condition": {
        "field": "contacts.birthday",
        "op": "==",
        "value": "{{today}}"
    },
    "action": {
        "type": "notification.send",
        "args": {
            "message": "Hoy es el cumple de {{contact.name}}",
            "deliver_to": "hub"
        }
    }
}
```

### 8. Backup automático

```json
{
    "name": "Daily backup",
    "trigger": {"type": "cron", "expression": "0 3 * * *"},
    "action": {
        "type": "shell.execute",
        "args": {
            "command": "powershell -File scripts/backup-aithera.ps1",
            "cwd": "{{user.home}}/Aithera"
        }
    },
    "approval_required": true
}
```

## Setup UI

```tsx
function RuleGallery() {
    const rules = useRuleTemplates();
    
    return (
        <Grid>
            {rules.map(rule => (
                <RuleCard key={rule.id}>
                    <Title>{rule.name}</Title>
                    <Description>{rule.description}</Description>
                    <Preview action={rule.action} trigger={rule.trigger} />
                    <Button onClick={() => installRule(rule)}>
                        Activar (1-click)
                    </Button>
                </RuleCard>
            ))}
        </Grid>
    );
}
```

## Para Aithera

- ⏳ V0.9: 8+ reglas predefinidas en Ajustes.
- ⏳ V0.85+: community rules marketplace (futuro).
- ⏳ V1.0+: templates personalizables.

## Referencias cruzadas

- [JWIKI-169 README.md](./README.md)
- [JWIKI-174 rules-engines.md](./rules-engines.md)
- [JWIKI-176 approval-flows-automation.md](./approval-flows-automation.md)

## Fuentes

1. https://zapier.com/apps
2. https://ifttt.com/
3. Plan Maestro 2026 §11

## Nivel de confianza

**85%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified