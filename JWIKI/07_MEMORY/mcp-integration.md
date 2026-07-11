# MCP — Model Context Protocol (Memory perspective)

## Resumen

**MCP** (Model Context Protocol) estándar abierto para tools/data. Aithera V0.85+ puede usar como cliente. Perspectiva desde memory layer.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## MCP server for memory

Un MCP server puede exponer Aithera's memory:

```python
# mcp_server_aithera_memory.py
from mcp.server import Server
from mcp.types import Resource, Tool

server = Server("aithera-memory")

@server.resource("memory://{collection}/{id}")
async def get_memory(collection: str, id: str) -> Resource:
    item = await memory_manager.get(collection, id)
    return Resource(uri=f"memory://{collection}/{id}", text=item.text)

@server.tool()
async def memory_search(query: str, top_k: int = 5) -> list[dict]:
    results = await memory_manager.search(query, top_k)
    return [{"text": r.text, "metadata": r.metadata} for r in results]
```

## Aithera como MCP client

Aithera V0.85+ puede consumir MCP servers externos:

```python
from mcp.client import Client

# Conectar a filesystem MCP server
client = Client("stdio", command="npx", args=["-y", "@modelcontextprotocol/server-filesystem"])

# Listar tools
tools = await client.list_tools()

# Añadir al ToolManager
for tool in tools:
    tool_manager.register_mcp_tool(client, tool)
```

## Memory + MCP benefits

- ✅ **Standard**: cualquier LLM puede usar Aithera memory via MCP.
- ✅ **Composability**: Aithera memory + filesystem + GitHub + Postgres MCP servers.
- ✅ **Ecosystem**: 100+ MCP servers oficiales.

## Para Aithera V1.1+

V1.1 podría exponer Aithera memory como MCP server (Plugin estándar), permitiendo:
- Claude Desktop lee Aithera memory.
- Otros agentes consultan Aithera knowledge base.

## Referencias cruzadas

- [JWIKI-113 mcp.md](../06_AGENTS/mcp.md)
- [JWIKI-120 chromadb.md](./chromadb.md)

## Fuentes

1. https://modelcontextprotocol.io/
2. https://github.com/modelcontextprotocol

## Nivel de confianza

**85%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified