# Material crudo JWIKI-002 — Comparativa proyectos OSS principales

## Hechos verificados

1. **OpenClaw** — 376k stars, TypeScript, MCP-based, multi-platform (Discord/Telegram/WhatsApp/Slack). MIT. Activo.
   - Fuente: github.com/openclaw/openclaw
2. **Superpowers** — 215k stars, Shell (skill framework). Compatible con Claude Code, Codex. Obra/superpowers. MIT.
   - Fuente: github.com/obra/superpowers
3. **OpenHuman** — 7.8k stars, Rust+TS, desktop-first. Tinyhumansai. v0.53.43 (mayo 2026).
   - Fuente: github.com/tinyhumansai/openhuman
4. **Hermes Agent** — 53k stars, Python+Node.js, Nous Research, self-evolving. MIT.
   - Fuente: github.com/Hermes-AI/Hermes-Agent
5. **OpenJarvis** — repo open-jarvis/OpenJarvis (Stanford). Python, local-first, 5 primitivos.
   - Fuente: github.com/open-jarvis/OpenJarvis
6. **JarvisAgent** — myismu/JarvisAgent. Tauri 2 + Vue 3 + Rust. 20+ LLMs. Dual-axis mode.
   - Fuente: github.com/myismu/JarvisAgent
7. **Clawdbot** — clawdbot/clawdbot. MCP-based. Privacidad local-first.
   - Fuente: github.com/clawdbot/clawdbot

## Datos técnicos

- **Stars (junio 2026)**: OpenClaw 376k > Superpowers 215k > Hermes 53k > OpenHuman 7.8k
- **Lenguaje principal**:
  - TypeScript: OpenClaw
  - Rust: OpenHuman, JarvisAgent
  - Python: Hermes, OpenJarvis
  - Shell: Superpowers
- **Multi-platform**:
  - Cloud multi-channel: OpenClaw (Discord/Telegram/WhatsApp/Slack)
  - Desktop-first: OpenHuman, JarvisAgent
  - Local-only: OpenJarvis, Superpowers (CLI)
- **Wake word**: ninguno documentado en estos proyectos (sería feature de voice, separado)
- **LLMs soportados**: 20+ en JarvisAgent, los demás usan el que el usuario configure
- **Tool ecosystem**: OpenClaw MCP, JarvisAgent custom tools, Hermes open
- **Memory**: variable (RAG en varios, persistente en OpenHuman)

## Comparativa por categoría

### Multi-platform cloud (OpenClaw)
- ✅ Más maduro, 376k stars
- ✅ MCP protocol estándar
- ❌ Requiere cloud para algunos canales
- ❌ Más complejo de mantener

### Desktop-first (OpenHuman, JarvisAgent)
- ✅ Privacidad (datos locales)
- ✅ Performance (Rust)
- ❌ Menos estrellas
- ❌ Setup más manual

### Skill framework (Superpowers)
- ✅ Compatible con Claude Code, Codex
- ✅ Skill format estandarizado
- ❌ Solo framework, no app completa
- ❌ Requiere un agente host

### Coding-focused (JarvisAgent)
- ✅ Dual-axis mode (Audience × WorkMode)
- ✅ Snapshot engine, sub-agent delegation
- ❌ Más complejo que otros
- ❌ Enfoque muy específico

### Self-evolving (Hermes Agent)
- ✅ Aprende de uso
- ✅ Multi-modal
- ❌ Más experimental

## Diferencias clave

- **OpenClaw vs OpenHuman**: cloud-multi vs desktop-local. OpenClaw es el más popular; OpenHuman el más privacy-first.
- **Hermes vs Superpowers**: agent completo vs framework de skills. Complementarios.
- **OpenJarvis vs todos**: Stanford academic con primitivos teóricos vs OSS prácticos.

## Pendientes de validación

- Confirmar latest release dates
- Verificar issues activas vs cerradas
- Buscar benchmarks de performance
- Comprobar documentación (algunos tienen poca)