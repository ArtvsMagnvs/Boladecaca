# Convenciones — Code Structure

## Resumen

**Convenciones de estructura** para Aithera backend + frontend. Ver CLAUDE.md §3.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Backend (Python)

```
backend/
├── app/
│   ├── main.py               # FastAPI app + lifespan
│   ├── core/                 # config, logging, secrets
│   ├── db/                   # database, models, schemas
│   ├── api/
│   │   └── endpoints/        # routers (1 per resource)
│   ├── ai/                   # AI providers + ai_manager
│   ├── agents/               # AgentManager + ArchitectAgent
│   ├── tools/                # ToolManager + tools (1 file per tool)
│   ├── voice/                # TTS/STT engines
│   ├── integrations/         # google_auth, etc.
│   ├── services/             # email_service, etc.
│   └── gateway/              # Gateway + adapters (V0.8+)
├── tests/                    # pytest
├── alembic/                  # migrations
├── scripts/                  # utility scripts
├── requirements.txt
└── alembic.ini
```

## Frontend (React)

```
frontend/
├── electron/                 # main.cjs, preload.cjs
├── src/
│   ├── pages/                # 9 pages (Hub, Chat, ...)
│   ├── components/
│   │   ├── hub/              # AICore.tsx, HubPanel.tsx
│   │   └── layout/           # AppLayout, Sidebar
│   ├── hooks/                # custom hooks
│   ├── lib/api.ts            # HTTP client
│   ├── services/             # business logic
│   ├── store/                # Zustand stores
│   ├── styles/               # CSS
│   └── types/                # TypeScript types
├── package.json
└── tailwind.config.js
```

## Naming

- **Files**: snake_case (Python), PascalCase (React components).
- **Classes**: PascalCase.
- **Functions**: snake_case (Python), camelCase (TS).
- **Constants**: UPPERCASE_SNAKE.
- **DB tables**: snake_case plural.
- **Endpoints**: kebab-case.

## Para Aithera

- ✅ V0.7.3: convenciones aplicadas (ver CLAUDE.md §3).

## Fuentes

1. CLAUDE.md §3

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified