# moltis — MCP-first OSS

## Resumen

**moltis** (moltis-org/moltis) es un proyecto OSS reciente (2026) que implementa un asistente personal **MCP-first puro** (sin LLM framework). Aithera借鉴.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Overview

- **Stars**: ~1k (julio 2026, baja tracción temprana).
- **License**: MIT.
- **Lenguaje**: TypeScript / Node.js.
- **Concepto**: MCP nativo, multi-LLM, memory built-in.

## Differentiators

| Aspecto | moltis | OpenClaw |
|---|---|---|
| **MCP first** | ✅ core | ✅ integrations |
| **LLM framework** | ❌ ninguno | LangChain |
| **Stars** | ~1k | 382k |
| **License** | MIT | MIT |
| **Maturity** | nuevo (2026) | maduro (2025) |

## Arquitectura

```
moltis
  ├── MCP server (exposes memory, tools, prompts)
  ├── MCP client (consume external MCP servers)
  ├── LLM providers (OpenAI, Anthropic, local)
  ├── Memory (built-in)
  └── CLI / web UI
```

## Para Aithera借鉴

Aithera V1.1+ podría借鉴:
- ✅ **MCP server** (exponer memory como MCP server).
- ✅ **MCP client** (consumir servers externos).
- ❌ **No framework**: Aithera tiene su propio AgentManager.

## Comparativa landscape

| Proyecto | MCP support | Framework | Aithera借鉴 |
|---|---|---|---|
| OpenClaw | integrations | LangChain | arquitectura |
| Hermes | native | propio | skills system |
| CrewAI | nativo v1.x | propio | crew pattern |
| AutoGen | native Teams | propio | MCP |
| moltis | core (puro) | ❌ ninguno | MCP-first approach |
| **Aithera** | ⏳ V1.1+ | propio | — |

## Discovery context

Descubierto durante el audit de JWIKI-008 (Clawdbot). Mencionado en docs como alternativa low-traction pero conceptualmente interesante por su MCP-first approach.

## Referencias cruzadas

- [JWIKI-008 clawdbot.md](./clawdbot.md)
- [JWIKI-113 mcp.md](./mcp.md)
- [JWIKI-136 mcp-integration.md](../07_MEMORY/mcp-integration.md)

## Fuentes

1. https://github.com/moltis-org/moltis
2. https://moltis.dev/

## Nivel de confianza

**70%** — proyecto nuevo, poca data.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified