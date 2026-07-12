# SOP — Rollback Alembic

## Cuándo
Una migration causa problemas en producción.

## Pasos

1. **Ver versión actual**:
```bash
cd backend
alembic current
```

2. **Rollback 1 step**:
```bash
alembic downgrade -1
```

3. **Rollback a versión específica**:
```bash
alembic downgrade <revision_id>
```

4. **Rollback all** (cuidado!):
```bash
alembic downgrade base
```

## ⚠️ Importante

- ❌ **NO** rollback si la migration eliminó datos.
- ✅ **Backup antes** de rollback (ver SOP-253).
- ✅ **Test en staging primero**.

## Verificación

- [ ] App arranca sin errores.
- [ ] Datos accesibles.

## Referencias cruzadas

- [JWIKI-253 backup-restore-aithera.md](./backup-restore-aithera.md)

---

*Estado: 🟢 verified*