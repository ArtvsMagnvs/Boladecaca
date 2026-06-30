# Dependencias entre dominios

> Qué dominios deben completarse antes que otros. Investigación secuencial.

## Grafo de dependencias

```
                    ┌─────────────────┐
                    │ 01_LANDSCAPE    │ (no tiene deps)
                    │ (proyectos OSS) │
                    └────────┬────────┘
                             │ referencia
                             ▼
        ┌────────────────────────────────────────┐
        │ 05_AI_PROVIDERS                        │
        │ (proveedores, APIs, pricing)           │
        └────┬───────────────────────────────────┘
             │ referencia (qué modelo usar)
             ▼
┌────────────────────────────┐    ┌────────────────────────────┐
│ 06_AGENTS                  │◄──►│ 07_MEMORY                  │
│ (frameworks, patterns)     │    │ (vector stores, RAG)       │
└────┬───────────────────────┘    └────────────────────────────┘
     │                                │
     │                                │
     ▼                                ▼
┌────────────────────────────┐    ┌────────────────────────────┐
│ 12_TOOLING                 │    │ 11_SECURITY                │
│ (execution engine)         │    │ (sandboxing)               │
└────────────────────────────┘    └────────────────────────────┘

┌────────────────────────────┐
│ 02_ARCHITECTURE            │ (no tiene deps, overview)
└────────┬───────────────────┘
         ▼
┌────────────────────────────┐    ┌────────────────────────────┐
│ 03_BACKEND                 │    │ 04_FRONTEND                │
│ (FastAPI, ORMs, DB)        │    │ (React, 3D, animations)    │
└────────┬───────────────────┘    └────────┬───────────────────┘
         │                                 │
         └────────────┬────────────────────┘
                      ▼
              ┌────────────────────────────┐
              │ 13_DEPLOYMENT              │
              │ (Electron, Docker, PWA)    │
              └────────────────────────────┘

┌────────────────────────────┐    ┌────────────────────────────┐
│ 08_VOICE                   │    │ 09_INTEGRATIONS            │
│ (TTS, STT)                 │    │ (OAuth, Gmail, Calendar)   │
└────────────────────────────┘    └────────────────────────────┘

┌────────────────────────────┐
│ 10_AUTOMATION              │
│ (schedulers, rules)        │
└────────────────────────────┘

┌────────────────────────────┐
│ 14_BEST_PRACTICES          │ (consolida hallazgos de todos)
└────────────────────────────┘

┌────────────────────────────┐
│ 15_KNOWN_PITFALLS          │ (recoge bugs reales)
└────────────────────────────┘

┌────────────────────────────┐
│ 16_SOPS                    │ (compila procedimientos probados)
└────────────────────────────┘
```

## Orden óptimo de investigación

1. **01_LANDSCAPE** + **05_AI_PROVIDERS** (en paralelo)
2. **02_ARCHITECTURE** (overview general)
3. **03_BACKEND** + **04_FRONTEND** (en paralelo)
4. **06_AGENTS** + **07_MEMORY** (en paralelo)
5. **08_VOICE** + **09_INTEGRATIONS** (en paralelo)
6. **10_AUTOMATION** + **11_SECURITY** (en paralelo)
7. **12_TOOLING** (depende de 06 + 11)
8. **13_DEPLOYMENT** (depende de 03 + 04)
9. **14_BEST_PRACTICES** + **15_KNOWN_PITFALLS** (consolidación)
10. **16_SOPS** (compilación final)

## Reglas de dependencia

- Un doc NO se considera `verified` hasta que sus docs dependientes estén al menos `done`.
- Si un doc necesita info de un dominio aún `pending`, marcar la sección correspondiente como `VERIFICACIÓN PENDIENTE`.
- El orquestador valida las dependencias antes de marcar un doc como `done`.

---

*Mantenedor: Mavis (orquestador).*