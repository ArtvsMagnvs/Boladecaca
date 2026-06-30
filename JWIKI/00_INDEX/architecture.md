# Arquitectura de la JWIKI

> Cómo está organizada la knowledge base, qué cubre cada dominio y cómo se relacionan.

## Principio organizativo

La JWIKI se organiza en **17 dominios** (00 a 16), ordenados para que la
investigación pueda proceder de forma **secuencial y por dependencias**:

```
Nivel 1 (Fundamentos)
├── 01_LANDSCAPE       Qué existe en el ecosistema
└── 05_AI_PROVIDERS    Con quién podemos hablar (modelos)

Nivel 2 (Stack técnico)
├── 02_ARCHITECTURE    Patrones generales
├── 03_BACKEND         Cómo se construye el servidor
└── 04_FRONTEND        Cómo se construye la UI

Nivel 3 (Inteligencia)
├── 06_AGENTS          Cómo razonan los agentes
└── 07_MEMORY          Cómo recuerdan

Nivel 4 (Conectividad)
├── 08_VOICE           Cómo hablan/escuchan
└── 09_INTEGRATIONS    Cómo conectan con el mundo externo

Nivel 5 (Producción)
├── 10_AUTOMATION      Qué hacen solos
├── 11_SECURITY        Cómo se protegen
└── 12_TOOLING         Cómo ejecutan acciones

Nivel 6 (Operación)
├── 13_DEPLOYMENT      Cómo se distribuyen
├── 14_BEST_PRACTICES  Cómo se hacen bien
└── 15_KNOWN_PITFALLS  Qué falla y cómo evitarlo

Nivel 7 (SOPs)
└── 16_SOPS            Procedimientos paso-a-paso
```

## Mapeo dominio → proyecto Aithera

| Dominio JWIKI | Relación con Aithera |
|---|---|
| 01_LANDSCAPE | Inspiración y comparativa con proyectos OSS |
| 02_ARCHITECTURE | Documenta los patrones usados por Aithera (cliente + backend) |
| 03_BACKEND | FastAPI + SQLAlchemy + PostgreSQL + Alembic (todo está en Aithera) |
| 04_FRONTEND | React + Vite + Three.js + Framer Motion (todo está en Aithera) |
| 05_AI_PROVIDERS | Los 8 proveedores en `backend/app/ai/providers/` |
| 06_AGENTS | `backend/app/agents/agent_manager.py` + ExecutionEngine |
| 07_MEMORY | `backend/app/memory/memory_manager.py` (ChromaDB) |
| 08_VOICE | `backend/app/voice/` (ElevenLabs + eSpeak) |
| 09_INTEGRATIONS | `backend/app/integrations/google_auth.py` (OAuth Gmail/Calendar) |
| 10_AUTOMATION | Fase 6 (V0.9, pendiente) |
| 11_SECURITY | Whitelist del ToolManager, validación de paths |
| 12_TOOLING | `backend/app/tools/` (8 herramientas) |
| 13_DEPLOYMENT | `electron-builder` config en `package.json` |
| 14_BEST_PRACTICES | Convenciones del proyecto en `CLAUDE.md` |
| 15_KNOWN_PITFALLS | Bugs y workarounds documentados |
| 16_SOPS | Procedimientos para extender Aithera |

## Modelo de datos de un documento

Cada doc tiene los mismos campos (ver `TEMPLATE.md`):

```
- Identidad:   Título, Resumen, Objetivo, Estado (🟢🟡🔴⚫)
- Compatibilidad: Versiones, Proyectos
- Contenido:   Arquitectura, Descripción técnica, Flujo interno
- Evidencia:   Código relacionado, Ejemplos, Fuentes
- Calidad:     Buenas prácticas, Errores comunes, Nivel de confianza
- Contexto:    Referencias cruzadas, Impacto sobre otros sistemas
- Pendientes:  Qué falta verificar
```

---

*Documento vivo. Mantenedor: Aithera Escriba.*