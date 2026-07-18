# app/tie/toolloop.py — el bucle de tool-use del TIE (V1.0, R1)
#
# EL HUECO QUE CIERRA (doc 23 Δ2, hallazgo del 2026-07-18): hasta aquí el TIE
# NUNCA había ejecutado una herramienta. `NullRuntime` solo llamaba al
# ToolManager si el nodo traía `metadata.tool_call`, y NADIE escribía jamás ese
# campo — el planner solo emite `tools: [nombres]`, que es una whitelist, no una
# llamada. Resultado verificado en vivo: la misión "lista los archivos de mi
# carpeta y dime cuántos hay" terminó `done` con 0 tools ejecutadas y 5 archivos
# INVENTADOS. Era un fallo de honestidad, no solo de funcionalidad.
#
# QUÉ HACE: el ciclo estándar de uso de herramientas —
#   elegir (LLM) → ejecutar (ToolManager) → observar (resultado) → repetir
# hasta que el modelo tiene datos suficientes para responder, o se agotan las
# iteraciones.
#
# QUIÉN ELIGE LA HERRAMIENTA (doc 23 Δ11): el TIE, y concretamente AQUÍ, en
# tiempo de ejecución — no el planner. Los parámetros de una llamada dependen del
# resultado del paso anterior ("lee el archivo que acabas de encontrar"), así que
# fijarlos por adelantado es frágil. El planner sigue acotando QUÉ tools puede
# tocar cada nodo (`node.tools`): esa es la frontera de seguridad, y se respeta
# en dos sitios (el catálogo que ve el modelo y el `allowed_tools` del manager).
#
# LO QUE ESTE MÓDULO **NO** HACE (y por qué): no valida params, no impone
# timeouts, no aplica whitelist ni escribe el log de auditoría. Todo eso ya es
# responsabilidad del `ToolManager` y se le delega tal cual — reimplementarlo
# aquí duplicaría la superficie de seguridad, que es justo lo contrario de lo que
# se quiere.
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.logging_config import get_system_logger
from app.tie.intents import _extract_json

logger = get_system_logger("tie.toolloop")

# Cuánto texto de un resultado se le devuelve al modelo como observación. Un
# `list_dir` de una carpeta grande o un `read_file` pueden ser enormes; sin tope,
# una sola observación se come la ventana de contexto y las iteraciones
# siguientes pierden el objetivo original.
_MAX_OBSERVATION_CHARS = 4000


@dataclass
class ToolLoopResult:
    """Lo que el bucle le devuelve al runtime. `answer` vacío con `ok=False`
    significa 'no pude fundamentar una respuesta' — el runtime lo convierte en
    un nodo fallido, NUNCA en una respuesta inventada."""
    ok: bool
    answer: str = ""
    tool_calls: list[dict] = field(default_factory=list)   # rastro para AgentResult
    iterations: int = 0
    error: Optional[str] = None


_SYSTEM_PROMPT = """Eres el ejecutor de un paso de Aithera. Tienes herramientas REALES a tu
disposición: lo que pidas se ejecuta de verdad en el ordenador del usuario.

Responde SIEMPRE con UN objeto JSON, sin texto alrededor y sin markdown:

- Para usar una herramienta:
  {"tool": {"tool_id": "...", "action": "...", "params": {...}}}
- Para dar la respuesta final, cuando YA tengas los datos que necesitas:
  {"answer": "tu respuesta al usuario"}

Reglas que no puedes saltarte:
1. Usa SOLO las herramientas y acciones del catálogo de abajo. No inventes ninguna.
2. NO inventes datos. Si necesitas un dato del sistema (archivos, emails, procesos,
   contenido web...), OBTENLO con una herramienta. Nunca supongas su valor.
3. Si una herramienta falla o te la deniegan, léelo, y busca otra vía o explica el
   límite en tu respuesta final. No lo ocultes.
4. Cuando ya tengas lo necesario, responde con {"answer": ...} basándote SOLO en lo
   que las herramientas te devolvieron de verdad."""


def build_catalog(allowed_tools: list[str], tool_manager) -> list[dict]:
    """El catálogo de acciones que el modelo puede pedir en ESTE nodo:
    intersección de la whitelist del nodo con lo que hay registrado de verdad.

    Solo se exponen acciones NO sensibles: las que requieren confirmación se
    filtran aquí (ver `_is_sensitive`), de modo que el modelo ni siquiera las ve
    como opción. La segunda barrera está en `run()`, por si el modelo se
    inventara una.

    Una whitelist VACÍA significa "este nodo no tiene herramientas", nunca
    "todas": ante la duda, ninguna. (La convención opuesta de `ToolManager`
    —`allowed_tools=None` = sin filtro— es para sus propios tests; aquí sería un
    agujero: un nodo sin tools acabaría con acceso al catálogo entero.)"""
    if not allowed_tools:
        return []

    catalog: list[dict] = []
    for tool in tool_manager.list_tools():
        if tool["tool_id"] not in allowed_tools:
            continue
        for action in tool.get("actions", []):
            if _is_sensitive(tool, action):
                continue
            catalog.append({
                "tool_id": tool["tool_id"],
                "action": action.get("id"),
                "description": action.get("description", ""),
                "params": action.get("params", {}),
            })
    return catalog


def _is_sensitive(tool: dict, action: dict) -> bool:
    """¿Esta acción necesita el visto bueno del usuario?

    LÍMITE DE SEGURIDAD ACORDADO CON EL USUARIO (2026-07-18): el bucle es
    autónomo SOLO para acciones de lectura/consulta. Las que escriben o actúan
    sobre el mundo (enviar un email, ejecutar shell/PowerShell, clicar el
    escritorio, borrar archivos) NO las ejecuta por su cuenta: siguen pasando por
    el ApprovalGate del plan (T4a) o del nodo (T3), donde el usuario las ve
    juntas y decide.

    La acción manda sobre la tool: `email` no es sensible en bloque (leer el
    inbox no lo es), pero `email.send_email` sí."""
    if action.get("requires_confirmation") is not None:
        return bool(action["requires_confirmation"])
    return bool(tool.get("requires_confirmation"))


def _format_catalog(catalog: list[dict]) -> str:
    lines = []
    for entry in catalog:
        params = ", ".join(f"{k}: {v}" for k, v in (entry["params"] or {}).items())
        lines.append(
            f'- tool_id="{entry["tool_id"]}" action="{entry["action"]}" — '
            f'{entry["description"]}' + (f" | params: {params}" if params else "")
        )
    return "\n".join(lines)


def _truncate(text: str, limit: int = _MAX_OBSERVATION_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n… [truncado: {len(text)} caracteres en total]"


async def run(
    *,
    instruction: str,
    context: str,
    allowed_tools: list[str],
    tool_manager,
    max_iters: int,
    model_override: Optional[str] = None,
    project_id: Optional[int] = None,
    timeout_s: int = 60,
) -> ToolLoopResult:
    """Ejecuta el ciclo elegir→ejecutar→observar.

    NO lanza: cualquier fallo se devuelve como `ToolLoopResult(ok=False)` para
    que el runtime decida su degradación. La única excepción que SÍ se propaga es
    `CancelledError`: el kill-switch del executor (T3) tiene que poder cortar un
    nodo en vuelo, y tragarse esa cancelación lo rompería."""
    from app.mel import Capability, ExecutionRequest, complete as mel_complete

    catalog = build_catalog(allowed_tools, tool_manager)
    if not catalog:
        # Sin herramientas utilizables no hay nada que orquestar: el runtime
        # sigue por su camino de chat de siempre (cero regresión).
        return ToolLoopResult(ok=False, error="sin herramientas disponibles para este paso")

    transcript: list[str] = [f"OBJETIVO DEL PASO:\n{instruction}"]
    if context:
        transcript.append(f"CONTEXTO DISPONIBLE:\n{context}")
    transcript.append(f"HERRAMIENTAS DISPONIBLES:\n{_format_catalog(catalog)}")

    tool_calls: list[dict] = []
    allowed_pairs = {(e["tool_id"], e["action"]) for e in catalog}

    for iteration in range(1, max_iters + 1):
        res = await mel_complete(ExecutionRequest(
            capability=Capability.AGENTIC,
            prompt="\n\n".join(transcript),
            system_prompt=_SYSTEM_PROMPT,
            model_override=model_override,
            context_tags={"project_id": project_id} if project_id else {},
        ))
        if not res.ok:
            return ToolLoopResult(ok=False, tool_calls=tool_calls, iterations=iteration,
                                  error=f"el modelo no respondió: {res.error}")

        data = _extract_json(res.text)
        if not data:
            # El modelo respondió en prosa. Si es la última vuelta lo damos por
            # respuesta (mejor eso que nada); si no, se le recuerda el formato.
            if iteration >= max_iters:
                return ToolLoopResult(ok=bool(res.text.strip()), answer=res.text.strip(),
                                      tool_calls=tool_calls, iterations=iteration)
            transcript.append(f"TU RESPUESTA:\n{res.text[:500]}")
            transcript.append('ERROR: responde SOLO con JSON, {"tool": {...}} o {"answer": "..."}.')
            continue

        if "answer" in data:
            answer = str(data["answer"]).strip()
            return ToolLoopResult(ok=bool(answer), answer=answer,
                                  tool_calls=tool_calls, iterations=iteration,
                                  error=None if answer else "el modelo respondió vacío")

        call = data.get("tool")
        if not isinstance(call, dict):
            transcript.append('ERROR: el JSON debe tener "tool" o "answer".')
            continue

        tool_id, action = call.get("tool_id"), call.get("action")
        params = call.get("params") or {}
        transcript.append(f"HAS PEDIDO: {json.dumps(call, ensure_ascii=False)[:400]}")

        # Segunda barrera del límite de seguridad: aunque el catálogo ya excluye
        # las sensibles, el modelo podría inventarse una. Se rechaza con MOTIVO,
        # y el motivo vuelve al modelo para que busque otra vía — no se corta el
        # bucle en seco.
        if (tool_id, action) not in allowed_pairs:
            reason = _denial_reason(tool_id, action, allowed_tools, tool_manager)
            transcript.append(f"DENEGADO: {reason}")
            tool_calls.append({"tool_id": tool_id, "action": action, "denied": True, "reason": reason})
            continue

        result = await tool_manager.execute(
            tool_id=tool_id,
            action=action,
            params=params,
            allowed_tools=list(allowed_tools),     # la whitelist del nodo, otra vez
            timeout=timeout_s,
        )
        tool_calls.append({"tool_id": tool_id, "action": action,
                           "ok": bool(result.get("success")), "error": result.get("error")})

        if result.get("success"):
            payload = json.dumps(result.get("result"), ensure_ascii=False, default=str)
            transcript.append(f"RESULTADO REAL de {tool_id}.{action}:\n{_truncate(payload)}")
        else:
            transcript.append(f"FALLÓ {tool_id}.{action}: {result.get('error')}")

    # Se agotaron las vueltas sin respuesta fundamentada. Se devuelve el fallo
    # con su rastro: el nodo quedará FAILED y el usuario verá qué se intentó.
    # NUNCA se fabrica una respuesta para salir del paso.
    return ToolLoopResult(
        ok=False, tool_calls=tool_calls, iterations=max_iters,
        error=f"no se pudo completar el paso en {max_iters} iteraciones con las herramientas disponibles",
    )


def _denial_reason(tool_id, action, allowed_tools: list[str], tool_manager) -> str:
    """Motivo legible de por qué no se ejecuta algo. Se le devuelve al modelo,
    así que tiene que ser accionable: debe poder decidir otra vía a partir de
    esto."""
    tool = tool_manager.get_tool(tool_id) if tool_id else None
    if tool is None:
        return f"la herramienta '{tool_id}' no existe. Usa solo las del catálogo."
    if allowed_tools and tool_id not in allowed_tools:
        return f"'{tool_id}' no está permitida en este paso. Permitidas: {', '.join(allowed_tools)}."
    for a in tool.list_actions():
        if a.get("id") == action:
            return (
                f"'{tool_id}.{action}' necesita la aprobación del usuario y no puedo "
                f"ejecutarla por mi cuenta. Busca otra vía o indícalo en tu respuesta final."
            )
    return f"'{tool_id}' no tiene la acción '{action}'. Usa solo las del catálogo."
