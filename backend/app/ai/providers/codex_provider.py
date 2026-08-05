# Codex (CLI) AI Provider — V1.0
#
# El SEGUNDO proveedor de Aithera que no habla por HTTP con una API: ejecuta el
# binario `codex` (OpenAI Codex CLI) que el usuario tiene instalado y logueado en
# su equipo. Es el gemelo exacto de `claude_code_provider.py`, para OpenAI.
#
# Por qué existe (petición del usuario, 2026-07-24): una suscripción de ChatGPT
# no expone una API key utilizable desde una app de terceros, pero el CLI de
# Codex SÍ está autenticado con esa suscripción (`codex login`) y tiene un modo
# NO interactivo (`codex exec "<prompt>"`) pensado para que otro programa lo
# conduzca. Así Aithera usa los modelos de OpenAI vía Codex sin pedir ninguna API
# key y sin inventar un login propio: reutiliza la sesión que el usuario ya abrió
# en su terminal. (Quien prefiera facturación por API puede autenticar el CLI con
# `codex login --with-api-key`; a Aithera le da igual cuál de los dos use.)
#
# Repositorio oficial VERIFICADO: https://github.com/openai/codex (org `openai`,
# Apache-2.0, paquete npm `@openai/codex`). Instalación para el usuario final:
#   npm i -g @openai/codex   ·   brew install --cask codex   ·   installer oficial
#   (Windows: `irm https://chatgpt.com/codex/install.ps1 | iex`). Ver la sección
#   "Codex CLI" de Ajustes → Proveedores de IA para la guía dentro de la app.
#
# DISPONIBILIDAD POR PLAN (fuente: página de precios oficial de OpenAI,
# learn.chatgpt.com/docs/pricing, 2026-07-24): «ChatGPT Work and Codex are
# included in your ChatGPT Free, Go, Plus, Pro, Business, Edu, or Enterprise
# plan» — es decir, según OpenAI TODOS los planes lo incluyen, con límites de uso
# que escalan por plan. Matiz honesto: el README del repo lista un conjunto más
# estrecho (Plus/Pro/Business/Edu/Enterprise, sin nombrar Free/Go) y el artículo
# definitivo del centro de ayuda no fue legible al investigar. Por eso la UI dice
# "incluido en tu plan de ChatGPT (Free/Go/Plus/Pro…)" y añade que, si el login
# con ChatGPT no funcionara en tu plan, siempre puedes usar una API key de OpenAI.
#
# Consecuencias honestas de este diseño (el mismo trato que claude_code):
#   - Requiere `codex` en el PATH y con sesión iniciada (`codex login`). Si no,
#     este proveedor se reporta NO disponible y el MEL lo salta.
#   - Sin streaming token-a-token: `codex exec` entrega la respuesta completa;
#     `generate_stream` la emite de una vez (cumple el contrato, no finge).
#   - Más lento que una API directa (arranca un proceso por llamada). Por eso está
#     marcado NO APTO para chat/clasificar/bucle-de-tools en el MEL (mel/catalog).
#   - `cwd` importa: si se le pasa la carpeta de un proyecto, Codex trabaja EN ese
#     repositorio. Se ejecuta en modo SANDBOX de solo lectura (el default de
#     `codex exec`): genera texto/código, no toca ficheros por su cuenta.
import asyncio
import os
import shutil
from typing import Any, AsyncIterator, Dict, List, Optional

from .base import BaseAIProvider, normalize_history

# Flag para elegir modelo en `codex exec` (OpenAI usa `--model`/`-m`). Solo se
# pasa si el usuario configuró un modelo EXPLÍCITO; por defecto NO se pasa y Codex
# usa el modelo de la cuenta — así no fijamos un id de modelo que podría no existir.
_MODEL_FLAG = "--model"

# Techo de seguridad: una llamada del CLI colgada no puede bloquear a Aithera para
# siempre. Generoso porque Codex, como agente, puede tardar en tareas largas.
DEFAULT_TIMEOUT_S = 300


def _find_cli() -> Optional[str]:
    """Ruta del binario `codex`, o None si no está instalado/en PATH."""
    return shutil.which("codex")


class CodexProvider(BaseAIProvider):
    """Usa el CLI de OpenAI Codex como si fuera un proveedor de IA más."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 base_url: Optional[str] = None):
        # `api_key` se ignora a propósito: la autenticación la aporta el CLI
        # (`codex login`, sesión de ChatGPT, o `--with-api-key`). `base_url` se
        # reutiliza como DIRECTORIO DE TRABAJO por defecto (el AIManager solo sabe
        # pasar estos tres campos; documentarlo evita inventar un esquema nuevo).
        super().__init__(api_key=None, model=model)
        self.workdir: Optional[str] = base_url or None

    def get_default_model(self) -> str:
        # "" = usar el modelo por defecto de la cuenta de Codex (no forzamos id).
        return ""

    @property
    def provider_name(self) -> str:
        return "codex"

    # ------------------------------------------------------------------

    async def _run(self, prompt: str, system_prompt: Optional[str] = None,
                   cwd: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT_S) -> Dict[str, Any]:
        cli = _find_cli()
        if not cli:
            return {"response": "Codex CLI no encontrado. Instálalo (`npm i -g @openai/codex`) "
                                "y verifica que `codex` esté en el PATH.", "error": True}

        # Codex `exec` no tiene un flag de system-prompt por invocación (usa
        # AGENTS.md/config): se pliega la instrucción del sistema DELANTE del
        # prompt, como transcripción. Degradación honesta, misma que el historial.
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"[Instrucciones del sistema]\n{system_prompt}\n\n{prompt}"

        # `codex exec` = modo NO interactivo: el mensaje final va a stdout, el
        # progreso a stderr. `-s read-only` (el default de exec, pero EXPLÍCITO a
        # propósito): este proveedor SOLO genera texto/código; jamás debe editar
        # ficheros ni tocar la red como efecto colateral de "responder". Nunca se
        # pasan `--full-auto`/`workspace-write`/`danger-full-access`.
        args = [cli, "exec", "-s", "read-only"]
        # Modelo: solo si el usuario lo fijó EXPLÍCITAMENTE. Por defecto NO se pasa
        # y Codex usa el modelo recomendado de la cuenta — su lista de ids cambia
        # rápido (y los ids `*-codex` los rechaza el login por ChatGPT), así que
        # fijar uno a ciegas rompería más de lo que ayuda.
        if self.model:
            args += [_MODEL_FLAG, self.model]
        args += [full_prompt]

        workdir = cwd or self.workdir
        if workdir and not os.path.isdir(workdir):
            workdir = None   # carpeta inválida: mejor ejecutar sin cwd que fallar

        try:
            proc = await asyncio.create_subprocess_exec(
                *args, cwd=workdir,
                # `codex exec` intenta LEER de stdin ("Reading additional input
                # from stdin…", verificado en vivo con codex-cli 0.145.0). Sin
                # cerrar stdin, si el proceso padre tiene un stdin abierto, codex
                # se quedaría esperando EOF y COLGARÍA hasta el timeout. Con
                # DEVNULL recibe EOF al instante y ejecuta solo con el prompt.
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as e:
            return {"response": f"No se pudo lanzar Codex: {e}", "error": True}

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"response": f"Codex no respondió en {timeout}s.", "error": True}

        out = (stdout or b"").decode("utf-8", errors="replace").strip()
        err = (stderr or b"").decode("utf-8", errors="replace").strip()

        if proc.returncode != 0:
            raw = (err or out or f"exit code {proc.returncode}").strip()
            # El error REAL está al FINAL del stderr (codex imprime primero un
            # banner de arranque); se muestra la COLA, no la cabecera. La pista de
            # login se detecta sobre el texto completo y se añade DESPUÉS de
            # truncar, para que nunca la corte el límite (verificado en vivo: sin
            # sesión, el stderr trae "401 Unauthorized"/"authentication").
            low = raw.lower()
            hint = ""
            if any(k in low for k in ("login", "auth", "sign in", "not authenticated", "unauthorized", "401")):
                hint = " — parece que no has iniciado sesión: abre una terminal y ejecuta `codex login` (o hazlo con el botón de Ajustes → Proveedores)."
            return {"response": f"Codex falló: {raw[-400:]}{hint}", "error": True}

        # `codex exec` (sin --json) entrega el mensaje final en stdout. Si por
        # alguna versión saliera vacío, se usa el stderr como último recurso.
        text = out or err
        return {
            "response": text,
            "model": self.model or "codex",
            "provider": self.provider_name,
        }

    @staticmethod
    def _with_history(prompt: str, history: Optional[List[Dict[str, Any]]]) -> str:
        """El CLI recibe UN texto: no tiene API de mensajes con roles. El historial
        se aplana como transcripción delante del turno actual (misma degradación
        honesta que claude_code). Sin historial devuelve el prompt TAL CUAL."""
        turnos = normalize_history(history)
        if not turnos:
            return prompt
        etiqueta = {"user": "Usuario", "assistant": "Tú"}
        transcripcion = "\n".join(
            f"{etiqueta[m['role']]}: {m['content']}" for m in turnos
        )
        return (
            "Conversación hasta ahora:\n"
            f"{transcripcion}\n\n"
            f"Usuario: {prompt}"
        )

    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                       messages: Optional[List[Dict[str, Any]]] = None,
                       workdir: Optional[str] = None) -> Dict[str, Any]:
        """[2026-08-04] `workdir`: la carpeta del proyecto donde Codex debe
        trabajar con SUS propias herramientas (mismo trato que Claude Code)."""
        return await self._run(self._with_history(prompt, messages), system_prompt,
                               cwd=workdir)

    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None,
                              messages: Optional[List[Dict[str, Any]]] = None) -> AsyncIterator[str]:
        """`codex exec` entrega la respuesta completa: se emite en un solo chunk.
        Cumple el contrato sin fingir un streaming que no existe."""
        result = await self._run(self._with_history(prompt, messages), system_prompt)
        text = result.get("response", "")
        if text:
            yield text

    async def health_check(self) -> bool:
        """Disponible si el binario existe y responde a --version. NO comprueba la
        sesión (eso costaría una llamada real); un fallo de login se reporta con
        mensaje claro en la primera generación."""
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
