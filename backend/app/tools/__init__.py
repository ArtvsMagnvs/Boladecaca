# backend/app/tools/__init__.py
#
# V0.4 (Fase 2 AgentManager + ToolSystem) + V0.5:
# Re-exports publicos del sistema de herramientas.
#
# El auto-registro de las tools por defecto se hace al importar
# `tool_manager.py` (aqui, el singleton `tool_manager` ya tiene
# filesystem/shell/git registradas). Esto permite que:
#
#   from app.tools import tool_manager
#   await tool_manager.execute("filesystem", "list_dir", {"path": "."})
#
# funcione desde cualquier modulo sin necesidad de tocar _register_default_tools.

from .base import BaseTool
from .filesystem_tool import FilesystemTool
from .shell_tool import ShellTool
from .git_tool import GitTool
from .powershell_tool import PowerShellTool
from .tool_manager import ToolManager, tool_manager


__all__ = [
    "BaseTool",
    "FilesystemTool",
    "ShellTool",
    "GitTool",
    "PowerShellTool",
    "ToolManager",
    "tool_manager",
]