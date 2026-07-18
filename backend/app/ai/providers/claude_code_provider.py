# Claude Code (CLI) AI Provider — V1.0
#
# El ÚNICO proveedor de Aithera que no habla por HTTP con una API: ejecuta el
# binario `claude` que el usuario ya tiene instalado y logueado en su equipo.
#
# Por qué existe (petición del usuario, 2026-07-18): una suscripción Pro/Max de
# Claude no expone una API key utilizable desde una app de terceros. Pero el CLI
# de Claude Code SÍ está autenticado con esa suscripción y tiene un modo
# no-interactivo (`claude -p "<prompt>" --output-format json`). Así Aithera usa
# Claude sin pedir ninguna API key y sin inventar un login propio: reutiliza la
# sesión que el usuario ya abrió en su terminal.
#
# Consecuencias honestas de este diseño (no son bugs, son el trato):
#   - Requiere que `claude` esté en el PATH y con sesión iniciada. Si no, este
#     proveedor se reporta como NO disponible y el MEL simplemente lo salta.
#   - No hay streaming token-a-token real: el CLI en modo -p entrega la
#     respuesta completa. `generate_stream` emite el resultado de una vez (el
#     contrato se cumple; la UI no se rompe, pero no verás escribir letra a
#     letra con este proveedor).
#   - Es más lento que una API directa (arranca un proceso por llamada).
#   - `cwd` importa: si se le pasa la carpeta de un proyecto, Claude Code
#     trabaja EN ese repositorio (lee sus ficheros, su CLAUDE.md). Es justo lo
#     que se quiere para tareas de código sobre un proyecto de Aithera.
import asyncio
import json
import os
import shutil
from typing import Any, AsyncIterator, Dict, Optional

from .base import BaseAIProvider

# Modelos que acepta `--model` (alias oficiales del CLI).
AVAILABLE_MODELS = ["sonnet", "opus", "haiku", "fable"]

# Techo de seguridad: una llamada del CLI que se cuelgue no puede bloquear a
# Aithera para siempre. Generoso porque Claude Code puede tardar en tareas largas.
DEFAULT_TIMEOUT_S = 300


def _find_cli() -> Optional[str]:
    """Ruta del binario `claude`, o None si no está instalado/en PATH."""
    return shutil.which("claude")


class ClaudeCodeProvider(BaseAIProvider):
    """Usa el CLI de Claude Code como si fuera un proveedor de IA más."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 base_url: Optional[str] = None):
        # `api_key` se ignora a propósito: la autenticación la aporta el CLI.
        # `base_url` se reutiliza como DIRECTORIO DE TRABAJO por defecto (el
        # AIManager solo sabe pasar estos tres campos; documentarlo aquí evita
        # inventar un esquema de configuración nuevo para un solo caso).
        super().__init__(api_key=None, model=model)
        self.workdir: Optional[str] = base_url or None

    def get_default_model(self) -> str:
        return "sonnet"

    @property
    def provider_name(self) -> str:
        return "claude_code"

    # ------------------------------------------------------------------

    async def _run(self, prompt: str, system_prompt: Optional[str] = None,
                   cwd: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT_S) -> Dict[str, Any]:
        cli = _find_cli()
        if not cli:
            return {"response": "Claude Code CLI no encontrado. Instálalo y verifica que "
                                "`claude` esté en el PATH.", "error": True}

        args = [cli, "-p", prompt, "--output-format", "json"]
        if self.model:
            args += ["--model", self.model]
        if system_prompt:
            args += ["--append-system-prompt", system_prompt]

        workdir = cwd or self.workdir
        if workdir and not os.path.isdir(workdir):
            workdir = None   # carpeta inválida: mejor ejecutar sin cwd que fallar

        try:
            proc = await asyncio.create_subprocess_exec(
                *args, cwd=workdir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as e:
            return {"response": f"No se pudo lanzar Claude Code: {e}", "error": True}

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"response": f"Claude Code no respondió en {timeout}s.", "error": True}

        out = (stdout or b"").decode("utf-8", errors="replace").strip()
        err = (stderr or b"").decode("utf-8", errors="replace").strip()

        if proc.returncode != 0:
            detail = err or out or f"exit code {proc.returncode}"
            # Mensaje accionable para el fallo más probable: sesión caducada.
            if "login" in detail.lower() or "auth" in detail.lower():
                detail += " — abre una terminal, ejecuta `claude` e inicia sesión."
            return {"response": f"Claude Code falló: {detail[:500]}", "error": True}

        # `--output-format json` devuelve un objeto con el resultado y su coste.
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return {"response": out, "model": self.model, "provider": self.provider_name}

        text = data.get("result") or data.get("response") or ""
        usage = data.get("usage") or {}
        tokens = None
        if isinstance(usage, dict):
            tokens = (usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0) or None

        if data.get("is_error"):
            return {"response": text or "Claude Code devolvió un error.", "error": True}

        return {
            "response": text,
            "model": data.get("model") or self.model,
            "provider": self.provider_name,
            "tokens": tokens,
            "session_id": data.get("session_id"),
        }

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        return await self._run(prompt, system_prompt)

    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncIterator[str]:
        """El modo -p del CLI entrega la respuesta completa: se emite en un solo
        chunk. Cumple el contrato sin fingir un streaming que no existe."""
        result = await self._run(prompt, system_prompt)
        text = result.get("response", "")
        if text:
            yield text

    async def health_check(self) -> bool:
        """Disponible si el binario existe y responde a --version. NO comprueba
        la sesión (eso costaría una llamada real); un fallo de login se reporta
        con mensaje claro en la primera generación."""
        cli = _find_cli()
        if not cli:
            return False
        try:
            proc = await asyncio.create_subprocess_exec(
                cli, "--version",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=15)
            return proc.returncode == 0
        except Exception:
            return False
