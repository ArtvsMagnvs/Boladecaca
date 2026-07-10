# MCP — Model Context Protocol

## Resumen

**MCP** (Model Context Protocol) es standard abierto para conectar LLMs con tools y data sources. Anthropic lanzó 2024.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Concepto

MCP define un protocolo cliente-servidor:
- **MCP server**: expone tools, resources, prompts.
- **MCP client**: el LLM (o agent) consume.

```
LLM Agent (MCP client)
  ↓
MCP protocol (JSON-RPC)
  ↓
MCP server
  ├─ Tools (web search, file system, db, etc.)
  ├─ Resources (files, data)
  └─ Prompts (templates)
```

## Hello World (MCP server)

```python
from mcp.server import Server, Tool

server = Server("my-tools")

@server.tool()
def get_weather(location: str) -> str:
    """Get current weather."""
    return f"Weather in {location}: sunny, 25°C"

server.run()
```

## MCP clients

- **Claude Desktop**: MCP nativo.
- **Cursor**: MCP support.
- **Continue.dev**: MCP support.
- **Hermes Agent** (V0.8.2+): MCP nativo.

## Para Aithera

Aithera V0.8+ podría añadir MCP client:

```python
# cliente MCP en Aithera Gateway
from mcp.client import Client

client = Client("stdio", command="mcp-server-filesystem")
tools = await client.list_tools()

# Integrar con AgentManager
agent_manager.register_mcp_tools(client)
```

## Servers populares

- `@modelcontextprotocol/server-filesystem` — filesystem access.
- `@modelcontextprotocol/server-github` — GitHub API.
- `@modelcontextprotocol/server-postgres` — PostgreSQL queries.
- `@modelcontextprotocol/server-slack` — Slack.
- `@modelcontextprotocol/server-puppeteer` — browser automation.

## Ventajas

- ✅ **Standard**: cualquier LLM puede usar.
- ✅ **Reusar tools**: community-maintained servers.
- ✅ **Ecosystem creciente**: 100+ servers oficiales.

## Para Aithera V0.85+

Añadir MCP client a Aithera:
- Aprovechar servers de filesystem, GitHub, etc.
- Reducir código custom de tools.

## Referencias cruzadas

- [JWIKI-112 tool-use-function-calling.md](../06_AGENTS/tool-use-function-calling.md)
- [JWIKI-007 hermes-agent.md](../01_LANDSCAPE/hermes-agent.md) — V0.8.2+ MCP nativo
- [JWIKI-014 google-adk.md](../05_AI_PROVIDERS/google-adk.md) — V2.4+ MCP core

## Fuentes

1. https://modelcontextprotocol.io/
2. https://github.com/modelcontextprotocol

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified