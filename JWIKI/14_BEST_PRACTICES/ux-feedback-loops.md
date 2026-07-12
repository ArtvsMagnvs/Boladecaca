# UX — Feedback Loops

## Resumen

**Feedback loops** son esenciales para que el user sepa qué está haciendo Aithera y pueda corregir.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Tipos de feedback

1. **Progress indicators**: spinner, progress bar.
2. **Streaming**: respuesta aparece gradualmente.
3. **Confirmation**: "I've sent 3 emails".
4. **Approval gates**: user debe aprobar acción sensible.
5. **Error messages**: claros y accionables.
6. **Auto-reply feedback**: ✓/✎/✗ counters (Aithera V0.7.3).

## Aithera V0.7.3 feedback

- ✅ **Streaming chat** (ver `useref-streaming.md`).
- ✅ **Auto-reply feedback** (`✓/✎/✗` counters, Aithera V0.7.3).
- ✅ **Activity log** (ver `email-activity-log.md`).
- ✅ **Approval gates** para auto-reply (propose → auto).

## Approval flow pattern

```
Aithera proposes action
  ↓
User sees in Hub: "🤖 Aithera wants to send this email:"
  [Card with email content]
  [✓ Approve] [✗ Deny] [✎ Edit]
  ↓
User decides → action executed or skipped
```

## Activity log

```
2026-07-09 14:30:15 | email.send | approved by user
2026-07-09 14:30:22 | email.archive | auto-approved
```

## Para Aithera

- ✅ V0.7.3: feedback loops implementados.
- ⏳ V0.85+: mejorar error messages + undo actions.

## Referencias cruzadas

- [JWIKI-176 approval-flows-automation.md](../10_AUTOMATION/approval-flows-automation.md)
- [JWIKI-168 email-activity-log.md](../09_INTEGRATIONS/email-activity-log.md)
- CLAUDE.md §1 (V0.7.3 autonomy)

## Fuentes

1. https://www.nngroup.com/articles/feedback-loops/
2. CLAUDE.md §1

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified