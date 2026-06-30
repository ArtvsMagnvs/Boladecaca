# 00 — INDEX

> El mapa completo de la JWIKI. Aquí vive la información meta: qué hay, qué falta, qué cambió.

## Contenido

| Doc | Propósito |
|---|---|
| [README.md](./README.md) | Este archivo (mapa y arquitectura) |
| [architecture.md](./architecture.md) | Arquitectura high-level de la JWIKI |
| [dependencies.md](./dependencies.md) | Dependencias entre dominios |
| [status.md](./status.md) | Estado actual por fase |
| [TEMPLATE.md](./TEMPLATE.md) | Plantilla obligatoria de documento |
| [WORKFLOW.md](./WORKFLOW.md) | Loop autónomo de documentación |
| [task_queue.md](./task_queue.md) | Cola activa de tareas |
| [wiki-map.md](./wiki-map.md) | Mapa vivo de la JWIKI (todo lo que existe) |

## Arquitectura de la JWIKI

```
JWIKI/
├── README.md                    Entry point
├── CONSTITUTION.md              Ley (master prompt)
├── ROADMAP.md                   Plan de investigación por fases
├── CONTRIBUTING.md              Cómo contribuir
├── CHANGELOG.md                 Historial
├── 00_INDEX/                    Este directorio
├── 01_LANDSCAPE/                Proyectos OSS, comparativas
├── 02_ARCHITECTURE/             Patrones de arquitectura
├── 03_BACKEND/                  Frameworks backend, ORMs, DB
├── 04_FRONTEND/                 UI frameworks, 3D, animaciones
├── 05_AI_PROVIDERS/             Proveedores IA, APIs, pricing
├── 06_AGENTS/                   Frameworks de agentes, patterns
├── 07_MEMORY/                   Vector stores, embeddings, RAG
├── 08_VOICE/                    TTS, STT, voice pipelines
├── 09_INTEGRATIONS/             OAuth, Gmail, Calendar, Telegram
├── 10_AUTOMATION/               Schedulers, rules engines
├── 11_SECURITY/                 Sandboxing, API keys, OAuth security
├── 12_TOOLING/                  Execution engines, tool managers
├── 13_DEPLOYMENT/               Electron, Tauri, Docker, PWA
├── 14_BEST_PRACTICES/           Convenciones, escalabilidad
├── 15_KNOWN_PITFALLS/           Bugs, regresiones, workarounds
└── 16_SOPS/                     Procedimientos paso-a-paso
```

## Cómo se referencian entre sí los documentos

- Cada documento incluye una sección **Referencias cruzadas** que apunta a otros docs JWIKI por path relativo (`./01_LANDSCAPE/projects.md#openclaw`).
- Las referencias a código externo usan URL con commit SHA pinneado cuando es posible (`https://github.com/openclaw/openclaw/blob/<sha>/path/to/file.ts`).

## Reglas de nombrado

- **Carpetas de dominio**: `NN_DOMAIN` (NN = número, DOMAIN = nombre en mayúsculas con guiones bajos).
- **Archivos**: `kebab-case.md` (todo minúsculas, palabras separadas por guión).
- **Subcarpetas permitidas**: solo cuando un dominio tiene >10 docs.

## Versionado

- La JWIKI usa git para versionado.
- Cambios significativos (nuevo dominio, modificación de la constitución) requieren tag anotado (`v1.1`, `v2.0`).
- El changelog vive en cada documento (sección al final) y en commits de git.

---

*Sección 00 — INDEX. Mantenedor: Aithera Escriba (`aithera-wiki-escriba`).*