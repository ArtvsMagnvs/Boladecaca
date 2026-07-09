# Client-Server — Arquitectura cliente único backend único (Aithera)

## Resumen

**Aithera** sigue una arquitectura **cliente único / backend único**: Electron (frontend) ↔ FastAPI (backend). El cliente Telegram adapter es una variante channel-agnostic.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Diagrama

```
┌──────────────────────────┐    HTTP/JSON    ┌─────────────────────────┐
│   Electron + React       │ ◄────────────► │   FastAPI (uvicorn)    │
│   Aithera Desktop App    │                 │   Aithera Backend        │
│                          │                 │                          │
│   HashRouter + Zustand   │                 │   lifespan startup      │
│   pages/ (9 pages)       │                 │   routers (20)           │
│   components/            │                 │   ai/providers/ (8)      │
│   lib/api.ts             │                 │   memory/ (ChromaDB)     │
│   services/              │                 │   agents/, tools/        │
│   stores/                │                 │   gateway/, voice/       │
└──────────────────────────┘                 │   integrations/          │
                                             │   services/email_service │
                                             │                          │
                                             │   PostgreSQL (fallback   │
                                             │   SQLite) + ChromaDB     │
                                             └─────────────────────────┘
```

## Cliente — Electron

- **Framework**: Electron 29 + React 18 + TypeScript 5.3.
- **Routing**: HashRouter (necesario para `file://`).
- **State**: Zustand 4.
- **UI**: Tailwind + 3D (AICore con three.js).
- **Páginas**: 9 (Hub, Chat, Projects, Tasks, Calendar, Agents, EmailAssistant, VoiceCenter, Settings).
- **API client**: `frontend/src/lib/api.ts` (fetch wrapper con auth).

## Backend — FastAPI

- **Framework**: FastAPI + lifespan.
- **ORM**: SQLAlchemy 2.0 + Pydantic v2.
- **DB**: PostgreSQL (fallback SQLite) + ChromaDB.
- **AI**: 8 proveedores en `backend/app/ai/providers/`.
- **Tools**: 8 tools en `backend/app/tools/`.
- **Memory**: ChromaDB collections.
- **Routers**: 20 routers en `backend/app/api/endpoints/`.
- **Auth**: Google OAuth + API keys cifradas DPAPI.

## Comunicación

- **Protocolo**: HTTP/JSON.
- **Auth**: API key header (`Authorization: Bearer <key>`).
- **Streaming**: SSE para chat.
- **CORS**: restringido a localhost + Electron (V0.8 hardening).

## Multi-cliente (V0.8+)

V0.8 introduce el patrón **Gateway multi-canal**:
- Cliente Electron (principal).
- Canal Telegram (primer adapter).
- Futuros: Discord, Slack, WhatsApp.

El Gateway channel-agnostic desacopla la lógica de negocio del canal. Ver [JWIKI-047 multi-client.md](./multi-client.md).

## Ventajas de cliente único

- ✅ Simple de desarrollar.
- ✅ Auth unificado.
- ✅ Datos compartidos sin sync.
- ✅ Baja latencia (in-process).

## Desventajas

- ❌ No multi-dispositivo (Electron solo en un PC).
- ❌ No multi-usuario (es personal).
- ❌ V0.7.3 NO sincroniza entre dispositivos.

## Para V1.0+

Si Aithera se vuelve multi-dispositivo:
- Web app (React + Vite, separado).
- Mobile (React Native, separado).
- Backend FastAPI compartido (sync via DB).

## Referencias cruzadas

- [JWIKI-045 monolith-vs-microservices.md](./monolith-vs-microservices.md)
- [JWIKI-047 multi-client.md](./multi-client.md)
- [JWIKI-058 fastapi.md](../03_BACKEND/fastapi.md)

## Fuentes

1. Aithera V0.7.3 codebase (CLAUDE.md §1-4).
2. FastAPI docs.

## Nivel de confianza

**95%** — Arquitectura bien documentada en el codebase.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified