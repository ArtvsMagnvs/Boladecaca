# tests/mcp_mini_server.py — mini-servidor MCP stdio REAL para los tests de C1
#
# No es un mock: es un servidor MCP de verdad (el SDK oficial) lanzado como
# subproceso por stdio, exactamente como el usuario lanzaria uno de npx. Los
# tests de integracion de test_mcp_client.py conectan el cliente de Aithera
# contra el — la cadena completa (spawn + initialize + list_tools + call_tool)
# sin red y sin depender de nada externo al venv.
#
# Tools a proposito minimas:
#   - echo(text): devuelve el texto — el round-trip basico.
#   - suma(a, b): con schema tipado — ejercita la validacion de argumentos.
#   - sucio(): devuelve texto con caracteres invisibles (U+FFFC) — ejercita
#     que el proxy SANEA la respuesta externa (S9c) antes de entregarla.
from mcp.server import MCPServer

server = MCPServer(name="aithera-mini-test")


@server.tool()
def echo(text: str) -> str:
    """Devuelve el mismo texto."""
    return f"eco: {text}"


@server.tool()
def suma(a: int, b: int) -> str:
    """Suma dos enteros."""
    return str(a + b)


@server.tool()
def sucio() -> str:
    """Texto con invisibles, como una web real."""
    return "enlace￼limpio"


if __name__ == "__main__":
    server.run("stdio")
