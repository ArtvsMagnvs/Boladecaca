# Best Practices — Overview

## Resumen

Best practices derivadas del Plan Maestro 2026 y experiencia Aithera V0.7.3. Categorías: architecture, performance, UX, conventions, observability, testing, documentation.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Categorías

- **Architecture** (218): ADRs, decisiones clave.
- **Performance** (219-220): streaming, caching.
- **UX** (221-222): feedback loops, error handling.
- **Conventions** (223-224): code structure, naming.
- **Observability** (225-226): logs, metrics.
- **Testing** (227): strategy + smoke + integration.
- **Documentation** (228): docs as code.

## Aithera V0.7.3 best practices (de CLAUDE.md)

- ✅ **8 principios** invariantes (CLAUDE.md §18):
  1. No romper lo que funciona.
  2. Evolución, no reescritura.
  3. Un backend, múltiples clientes.
  4. La IA razona, Aithera decide.
  5. Ejecución controlada (whitelist).
  6. Optimizar para un usuario.
  7. Cada fase deja producto usable.
  8. Sin sobreingeniería.

- ✅ **Patterns validados** (Plan Maestro §2):
  1. Rule engine + IA con autonomía gradual.
  2. Message envelope único channel-agnostic.
  3. Ingesta proactiva de contexto.
  4. Checkpointing + approval gates.
  5. Routing por complejidad + traces.

## Para Aithera

- ✅ V0.7.3: best practices aplicados.
- ⏳ V0.85+: medir + iterar.

## Referencias cruzadas

- [JWIKI-218 architecture-decisions.md](./architecture-decisions.md)
- [JWIKI-227 testing-strategy.md](./testing-strategy.md)
- CLAUDE.md §18

## Fuentes

1. CLAUDE.md §18
2. Plan Maestro 2026

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified