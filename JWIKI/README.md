# JWIKI — Jarvis Wiki

> La knowledge base definitiva sobre asistentes personales AI tipo JARVIS.
> Aplica la metodología OTKB al ecosistema Aithera.

## Qué es

La JWIKI es una **memoria técnica permanente** de todo lo relacionado con proyectos de
asistentes personales AI tipo JARVIS: arquitecturas cliente-servidor, proveedores IA,
frameworks de agentes, memoria semántica, integración con voz, OAuth, automation,
seguridad, despliegue desktop, etc.

Su objetivo NO es desarrollar funcionalidades (eso es Aithera), sino **comprender,
documentar, validar y relacionar todo el conocimiento disponible** para que cualquier
agente (humano o IA) pueda tomar decisiones técnicas sobre Aithera **sin tener que
volver a investigar**.

## Por qué existe

A diferencia del ecosistema Tibia (donde ya hay una wiki consolidada), el espacio
"asistente personal AI tipo JARVIS" está fragmentado entre docenas de proyectos OSS
(OpenClaw, OpenHuman, OpenJarvis, Hermes Agent, JarvisAgent, Mark-XL, etc.), cada uno
con su stack, sus proveedores IA favoritos, sus decisiones de arquitectura y sus
limitaciones. Re-descubrir qué herramienta usar para qué caso cada vez que
arrancamos una feature es un desperdicio enorme.

La JWIKI centraliza ese conocimiento con **trazabilidad completa** entre código
fuente real, documentación oficial, papers, vídeos y decisiones técnicas.

## Principios rectores

Estos principios son **inviolables** y están detallados en [CONSTITUTION.md](./CONSTITUTION.md):

1. **Nunca inventar información.**
2. **Nunca rellenar huecos con suposiciones** — marcar como `VERIFICACIÓN PENDIENTE`.
3. **Priorizar siempre el código fuente** sobre cualquier tutorial o vídeo.
4. **Toda afirmación** respaldada por una o varias fuentes citadas.
5. **Documentar todas las versiones** y forks, no solo el "main" actual.
6. **Sintetizar**, nunca copiar literalmente.

## Cómo navegar

| Si quieres... | Ve a... |
|---|---|
| Entender la estructura global | [00_INDEX/README.md](./00_INDEX/README.md) |
| Ver qué hay hecho y qué falta | [00_INDEX/status.md](./00_INDEX/status.md) |
| Conocer las reglas de la casa | [CONSTITUTION.md](./CONSTITUTION.md) |
| Saber el plan de investigación | [ROADMAP.md](./ROADMAP.md) |
| Ver cómo contribuir | [CONTRIBUTING.md](./CONTRIBUTING.md) |
| Ver el workflow del equipo | [00_INDEX/WORKFLOW.md](./00_INDEX/WORKFLOW.md) |
| Ver la cola activa de tareas | [00_INDEX/task_queue.md](./00_INDEX/task_queue.md) |
| Ver el wiki-map (mapa vivo) | [00_INDEX/wiki-map.md](./00_INDEX/wiki-map.md) |
| Profundizar en un dominio | [01_LANDSCAPE/](./01_LANDSCAPE/) ... [16_SOPS/](./16_SOPS/) |
| Crear/editar un documento | [00_INDEX/TEMPLATE.md](./00_INDEX/TEMPLATE.md) |

## Taxonomía

17 dominios (00 a 16) definidos en la constitución:

```
00_INDEX          Mapa, arquitectura, roadmap, dependencias, status, cola, wiki-map
01_LANDSCAPE      Visión general del ecosistema JARVIS-like, proyectos OSS, comparativas
02_ARCHITECTURE   Patrones de arquitectura (client/server, monolith, multi-cliente, etc.)
03_BACKEND        Frameworks (FastAPI, Express, Tauri), ORMs, bases de datos
04_FRONTEND       UI frameworks (React, Vue, Svelte), 3D (Three.js), animaciones
05_AI_PROVIDERS   Los 8+ proveedores IA, APIs, precios, comparativas, function calling
06_AGENTS         Frameworks de agentes (LangGraph, CrewAI, custom), patterns, agent loops
07_MEMORY         ChromaDB, embeddings, RAG, vector stores, sentence-transformers
08_VOICE          TTS (ElevenLabs, eSpeak, OpenAI TTS), STT (Whisper), engines
09_INTEGRATIONS   OAuth (Google, Microsoft), Telegram, Discord, WhatsApp, Gmail, Calendar
10_AUTOMATION     Cron jobs, schedulers (APScheduler), rules engines, triggers
11_SECURITY       Sandboxing, tool whitelists, API key management, secrets
12_TOOLING        Execution engines, tool managers, validators, file/shell/git tools
13_DEPLOYMENT     Electron packaging, Docker, instaladores NSIS, PWA, auto-update
14_BEST_PRACTICES Convenciones, escalabilidad, anti-patterns, performance
15_KNOWN_PITFALLS Bugs, regresiones, workarounds, gotchas de cada framework
16_SOPS           Procedimientos paso-a-paso (añadir provider, crear tool, ...)
```

## Equipo

Esta knowledge base es mantenida por el equipo `aithera-wiki-*`. Ver:

- **Aithera Investigador** (`aithera-wiki-investigador`) — investigación web, lectura
  de repos OSS, papers, vídeos, foros. Recopila material crudo con fuentes.
- **Aithera Escriba** (`aithera-wiki-escriba`) — organización, archivado, consistencia.
  Sintetiza el material del Investigador en documentos siguiendo la plantilla.
- **Aithera Auditor** (`aithera-wiki-auditor`) — validación final. Aplica los 6 criterios
  de aceptación antes de marcar un doc como `verified`.
- **Mavis** (este orquestador) — planificación de fases, despachos, cron loop,
  mantenimiento del wiki-map.

Adicionalmente, los agentes `aithera-*` (frontend, backend, ia, agentes, memoria,
voz, integraciones, devops) actúan como **validadores de dominio** cuando un doc
menciona código o APIs específicas de su área.

## Estado actual

Ver [00_INDEX/status.md](./00_INDEX/status.md) para el estado actualizado.

**Estado**: 🟡 Fase 0 (Bootstrap) — estructura creada, constitución y roadmap
publicados. Investigación pendiente.

---

*Documento vivo. Última revisión: 2026-06-30 (Fase 0 bootstrap).*