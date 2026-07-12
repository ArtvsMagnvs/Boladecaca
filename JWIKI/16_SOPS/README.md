# SOPs — Overview Procedimientos

## Resumen

**SOPs** (Standard Operating Procedures) son procedimientos paso-a-paso para tareas recurrentes. Críticos para que devs (humanos o AI) puedan contribuir a Aithera sin reinventar la rueda.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Categorías

- **Add features**: 244-246 (provider, tool, agent).
- **Setup**: 247-250 (OAuth, scheduler, build, PWA).
- **Maintenance**: 251-254 (migration, update, backup, rotate keys).
- **Debug**: 255-258 (streaming, ChromaDB, OAuth, Electron).
- **Code patterns**: 259-262 (endpoint, page, model, migration rollback).
- **Operations**: 263-266 (change provider, add collection, voice, split god).

## Formato SOP

```markdown
# SOP: <Acción>

## Cuándo
<Trigger que dispara esta SOP>

## Pasos
1. ...
2. ...

## Verificación
- [ ] ...
- [ ] ...

## Rollback
<Si algo falla>
```

## Para Aithera

- ✅ V0.7.3: SOPs implementados (este dominio).
- ✅ Use como guía para AI agents + nuevos devs.

## Referencias cruzadas

- [JWIKI-244 add-ai-provider.md](./add-ai-provider.md)
- [JWIKI-262 rollback-migration.md](./rollback-migration.md)

## Fuentes

1. https://en.wikipedia.org/wiki/Standard_operating_procedure

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified