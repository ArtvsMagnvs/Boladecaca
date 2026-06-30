# CONSTITUCIÓN DE LA JWIKI

> El master prompt. Este documento es la **ley** que rige toda la Jarvis Wiki.
> Cualquier desviación requiere justificación explícita en el documento afectado.

---

## 1. MISIÓN

Construir una Jarvis Wiki (JWIKI) que documente de forma **verificable** el 100% del
conocimiento relevante para construir asistentes personales AI tipo JARVIS, incluyendo:

- Proyectos OSS existentes y sus decisiones arquitectónicas
- Frameworks y librerías (frontend, backend, AI, agentes, memoria, voz)
- Proveedores de IA y sus APIs (precios, límites, function calling, streaming)
- Patrones de arquitectura (FastAPI + Electron, Tauri, monolith vs microservicios)
- Integraciones (Google, Microsoft, Telegram, Discord, WhatsApp)
- Pipelines de voz (TTS, STT, wake word)
- Seguridad y sandboxing
- Pipelines de despliegue (Electron, Docker, PWA)
- Mejores prácticas, anti-patterns y pitfalls conocidos

La documentación debe servir como **memoria técnica permanente** y como **base de
datos para futuros agentes de desarrollo** del proyecto Aithera y otros similares.

---

## 2. PRINCIPIOS RECTORES (Inviolables)

| # | Principio |
|---|---|
| 1 | **Nunca inventar información.** |
| 2 | **Nunca rellenar huecos mediante suposiciones.** Si falta info, marcar como `VERIFICACIÓN PENDIENTE`. |
| 3 | **Priorizar siempre el código fuente** sobre cualquier tutorial o post de foro. |
| 4 | **Toda afirmación** debe estar respaldada por una o varias **fuentes citadas**. |
| 5 | **Cuando existan diferencias entre proyectos o versiones**, documentar **todas** ellas. |
| 6 | **Cuando no exista certeza**, marcar el contenido como `VERIFICACIÓN PENDIENTE` con instrucciones de qué falta. |
| 7 | **Nunca copies documentación literalmente**; **sintetízala y relaciónala**. |
| 8 | **Toda decisión** (qué framework elegir, qué patrón aplicar) debe ser **trazable** a una fuente. |
| 9 | **Las plantillas y convenciones** son obligatorias. La inconsistencia rompe la navegabilidad. |
| 10 | **Ninguna afirmación pasa sin validación cruzada** (código + al menos 2 fuentes, idealmente). |

---

## 3. FUENTES PRIORITARIAS (en orden de autoridad)

### 3.1. Proyectos OSS de referencia (máxima autoridad)

Investigar sistemáticamente los repos públicos activos (>500 stars, último commit <6 meses):

1. **Asistentes personales completos**:
   - `github.com/openclaw/openclaw` — OpenClaw (376k stars, TypeScript, multi-plataforma)
   - `github.com/tinyhumansai/openhuman` — OpenHuman (Rust + TS, desktop-first)
   - `github.com/open-jarvis/OpenJarvis` — OpenJarvis (Stanford, local-first)
   - `github.com/myismu/JarvisAgent` — JarvisAgent (Tauri + Vue 3 + Rust)
   - `github.com/Hermes-AI/Hermes-Agent` — Hermes Agent (Nous Research)
   - `github.com/clawdbot/clawdbot` — Clawdbot (MCP-based)
   - `github.com/obra/superpowers` — Superpowers (Skill framework)

2. **Frameworks de AI agents**:
   - `github.com/langchain-ai/langgraph` — LangGraph
   - `github.com/crewAIInc/crewAI` — CrewAI
   - `github.com/microsoft/autogen` — AutoGen
   - `github.com/google/adk-python` — Google ADK
   - `github.com/openai/openai-agents-python` — OpenAI Agents SDK
   - `github.com/microsoft/semantic-kernel` — Semantic Kernel
   - `github.com/run-llama/llama_index` — LlamaIndex
   - `github.com/Smolagents/smolagents` — Smolagents

3. **Frameworks auxiliares**:
   - `github.com/chroma-core/chroma` — ChromaDB
   - `github.com/UKPLab/sentence-transformers` — embeddings
   - `github.com/anthropics/anthropic-sdk-python`
   - `github.com/google-gemini/generative-ai-python`
   - `github.com/tautaute/fastapi-best-practices`
   - `github.com/electron/electron`

4. **Proyectos históricos / abandonados** (para entender evolución):
   - Jarvis早期Python projects (`jarvis-assistant`, `kishanrajput23/Jarvis-Desktop-Voice-Assistant`)
   - Old-school voice assistants pre-LLM
   - Project S.A.T.U.R.D.A.Y (Reddit)

### 3.2. Comunidades y foros

- **Reddit**: r/AI_Agents, r/LocalLLaMA, r/MachineLearning, r/SelfHosted
- **Hacker News**: búsquedas por "personal AI assistant", "JARVIS", "agent framework"
- **Discord**: LangChain, OpenAI, AI Agents (varios)
- **GitHub Discussions**: en cada repo OSS relevante
- **YouTube**: canales técnicos (Latent Space, AI Engineer, ThePrimeagen, etc.)

### 3.3. Documentación oficial

- Docs de cada proveedor IA (OpenAI, Anthropic, Gemini, MiniMax, etc.)
- Papers de arXiv sobre agentes y orquestación
- FastAPI docs, React docs, Electron docs, Three.js docs
- Model Context Protocol (MCP) spec
- Sentence-Transformers docs

### 3.4. Tipos de código a estudiar directamente

- Python (`.py`) — backend, AI providers, agents
- TypeScript (`.ts`, `.tsx`) — frontends Electron/web
- Rust (`.rs`) — backends Tauri, performance crítico
- SQL (`.sql`) — schemas, migraciones
- Docker (Dockerfile, docker-compose.yml)
- Binarios y formatos (ChromDB store, ONNX models)
- Config (YAML, TOML, .env)

---

## 4. ALCANCE TEMÁTICO MÍNIMO

Incluir como mínimo documentación sobre:

### Asistentes completos
- OpenClaw, OpenHuman, OpenJarvis, JarvisAgent, Hermes Agent, Clawdbot
- Cualquier fork con >500 stars y commits en los últimos 6 meses

### Frameworks AI
- LangGraph, CrewAI, AutoGen, Google ADK, OpenAI Agents SDK, Semantic Kernel
- LlamaIndex, Smolagents, Strands (AWS)

### Proveedores IA (cubrir los principales)
- OpenAI (GPT-5, o-series), Anthropic (Claude 4), Google (Gemini), Meta (Llama)
- DeepSeek, Mistral, xAI (Grok), Cohere, Perplexity
- Modelos chinos: Qwen, DeepSeek, GLM, MiniMax, Doubao
- Locales: Ollama, LM Studio, llama.cpp

### Frameworks auxiliares
- Backend: FastAPI, Flask, Express, Tauri
- Frontend: React, Vue, Svelte, SolidJS
- 3D/Animación: Three.js, React Three Fiber, Framer Motion, GSAP
- State: Zustand, Redux, Jotai, Pinia
- DB: PostgreSQL, SQLite, ChromaDB, Pinecone, Qdrant, Weaviate
- Voice: ElevenLabs, OpenAI TTS, eSpeak, Whisper, Deepgram, Azure Speech

### Herramientas
- LangSmith, Langfuse (observabilidad)
- Playwright (browser automation)
- n8n, Zapier-like (automation visual)
- Voiceflow (voice prototyping)

---

## 5. PROCESO DE INVESTIGACIÓN

Para cada tema:

1. **Buscar** todas las fuentes relevantes (GitHub, Reddit, HN, papers, YouTube).
2. **Compararlas** entre sí.
3. **Analizar el código fuente** directamente (clonar el repo, leer el código).
4. **Identificar diferencias** entre proyectos similares.
5. **Identificar diferencias** entre versiones.
6. **Validar ejemplos** mediante código ejecutable o referencia exacta.
7. **Relacionar** con otros sistemas / documentos de la JWIKI.
8. **Redactar** documentación siguiendo la plantilla estándar.
9. **Revisar** por un segundo agente (Aithera Investigador + agente de dominio).
10. **Aprobar** únicamente cuando toda la información esté verificada.

---

## 6. TAXONOMÍA (16 dominios + índice)

| # | Dominio | Alcance |
|---|---------|---------|
| 00 | INDEX | Mapa, arquitectura, roadmap, dependencias, status, cola, wiki-map |
| 01 | LANDSCAPE | Visión general del ecosistema JARVIS-like, proyectos OSS, comparativas |
| 02 | ARCHITECTURE | Patrones (client/server, monolith, multi-cliente, event-driven) |
| 03 | BACKEND | Frameworks (FastAPI, Express, Tauri), ORMs, bases de datos |
| 04 | FRONTEND | UI frameworks (React, Vue, Svelte), 3D (Three.js), animaciones |
| 05 | AI_PROVIDERS | Los 8+ proveedores IA, APIs, precios, comparativas, function calling |
| 06 | AGENTS | Frameworks (LangGraph, CrewAI, custom), patterns, agent loops |
| 07 | MEMORY | ChromaDB, embeddings, RAG, vector stores |
| 08 | VOICE | TTS, STT, engines, wake word, voice pipelines |
| 09 | INTEGRATIONS | OAuth, Gmail, Calendar, Telegram, Discord, WhatsApp, APIs externas |
| 10 | AUTOMATION | Cron jobs, schedulers (APScheduler), rules engines |
| 11 | SECURITY | Sandboxing, tool whitelists, API key management, secrets |
| 12 | TOOLING | Execution engines, tool managers, validators |
| 13 | DEPLOYMENT | Electron packaging, Docker, instaladores NSIS, PWA, auto-update |
| 14 | BEST_PRACTICES | Convenciones, escalabilidad, performance, anti-patterns |
| 15 | KNOWN_PITFALLS | Bugs, regresiones, workarounds, gotchas de cada framework |
| 16 | SOPS | Procedimientos paso-a-paso (añadir provider, crear tool, ...) |

---

## 7. PLANTILLA DE DOCUMENTO (Obligatoria)

Todos los artículos DEBEN seguir exactamente esta estructura. Saltarse secciones
requiere justificación explícita.

```markdown
# <Título>

## Resumen
(2-4 frases. Qué es, para qué sirve, dónde encaja.)

## Objetivo
(Qué pretende resolver este documento.)

## Estado
🟢 Verificado / 🟡 En progreso / 🔴 VERIFICACIÓN PENDIENTE / ⚫ Abandonado

## Versiones compatibles
(Tabla de versiones donde aplica: proyecto + versión)

## Proyectos compatibles
(Qué proyectos OSS lo soportan)

## Dependencias
(Qué otros sistemas o documentos se requieren)

## Arquitectura
(Descripción técnica, diagrama si aplica)

## Descripción técnica
(Profundización: cómo funciona, qué hace cada componente)

## Flujo interno
(Diagrama de secuencia o pasos)

## Call Stack / API
(Si es código: qué funciones/llama y en qué orden)

## Diagramas
(ASCII, mermaid, o links a imágenes)

## Código relacionado
(Paths exactos en los repos OSS con commit SHA si posible)

## Ejemplos
(Código copy-paste ready, con versión)

## Buenas prácticas
(Patrones recomendados)

## Errores comunes
(Qué no hacer)

## Breaking Changes
(Cambios incompatibles entre versiones)

## Cambios entre versiones
(Tabla diff de versiones)

## Impacto sobre otros sistemas
(Qué otros dominios se ven afectados)

## Referencias cruzadas
(links a otros docs de la JWIKI)

## Fuentes
(Lista de URLs, commits, papers, posts con fecha y autor)

## Nivel de confianza
(0-100% basado en cuántas fuentes corroboran y si hay código)

## Pendientes
(Qué falta verificar o documentar)
```

---

## 8. VALIDACIÓN (Ningún artículo se aprueba sin cumplir)

- [x] Código revisado (commit/branch específicos citados).
- [x] Fuentes contrastadas (mínimo 2 independientes para afirmaciones clave).
- [x] Compatibilidad documentada (qué proyectos + versiones).
- [x] Ejemplos verificados (testeados o con referencia a tests existentes).
- [x] Referencias cruzadas añadidas (links a otros docs JWIKI).
- [x] Revisión independiente realizada (por Aithera Auditor o agente distinto al autor).

---

## 9. OBJETIVO FINAL

Una base de conocimiento **navegable, versionada y coherente** que permita a cualquier
agente IA:

- Comprender el funcionamiento interno de cada componente de un asistente JARVIS.
- Decidir entre frameworks con datos reales (no hype).
- **Minimizar la necesidad de investigación adicional** al desarrollar Aithera.
- Mantener **trazabilidad completa** entre código, documentación y decisiones técnicas.

**Meta ambiciosa**: en 15-30 días, la mayor wiki existente sobre proyectos JARVIS-like.

---

## 10. CONTROL DE CAMBIOS

Esta constitución puede evolucionar. Cualquier modificación:

1. Debe ser propuesta en una issue / commit.
2. Debe mantener compatibilidad con documentos ya aprobados (o revalidarlos).
3. Debe quedar reflejada en el git log.

---

*Constitución v1.0 — establecida 2026-06-30 (Fase 0 bootstrap).*
*Mantenedores: equipo `aithera-wiki-*` (Investigador, Escriba, Auditor).*