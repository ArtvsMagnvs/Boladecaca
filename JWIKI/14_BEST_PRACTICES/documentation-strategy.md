# Documentation Strategy

## Resumen

**Docs as code**: docs en markdown versionados con código. CLAUDE.md es el ejemplo canónico.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Tipos de docs Aithera

| Tipo | Ubicación | Audencia |
|---|---|---|
| **CLAUDE.md** | root | developers + AI |
| **Fase_X** | root | developers (diseño + implementación) |
| **Roadmap** | AOS_Arquitectura_y_Roadmap.md | product |
| **Phase docs** | PLAN_MAESTRO_2026/ | architects |
| **API docs** | OpenAPI auto-generated | integradores |
| **Wiki** | JWIKI/ | reference |

## Docs as code principles

1. ✅ **Versionado en git**.
2. ✅ **Markdown plain text** (no Word, no PDF).
3. ✅ **Links cruzados** (`[text](path.md)`).
4. ✅ **Single source of truth** (no duplicar).
5. ✅ **Update on commit** (cada commit actualiza docs).
6. ✅ **Wiki map** (CLAUDE.md §19).

## JWIKI structure

```
JWIKI/
├── 00_INDEX/         # wiki-map, status, README, CHANGELOG
├── 01_LANDSCAPE/     # overview projects
├── 02_ARCHITECTURE/  # design decisions
├── 03_BACKEND/       # backend patterns
├── 04_FRONTEND/      # frontend patterns
├── ...
├── 14_BEST_PRACTICES/
├── 15_KNOWN_PITFALLS/
├── 16_SOPS/
└── material/         # raw research
```

## Update flow

```
Code change
  ↓
Update CLAUDE.md (state actual)
  ↓
Update Fase_X doc (implementación)
  ↓
Update JWIKI/ (referencia)
  ↓
Commit all together
```

## Para Aithera

- ✅ V0.7.3: docs as code aplicado.
- ✅ JWIKI: 175+ docs (ver wiki-map).

## Referencias cruzadas

- CLAUDE.md §19

## Fuentes

1. https://www.writethedocs.org/
2. CLAUDE.md §19

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified