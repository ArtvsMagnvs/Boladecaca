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

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Optional

from app.core.logging_config import get_system_logger
from app.tie.authority import Authority
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
    un nodo fallido, NUNCA en una respuesta inventada.

    [Auditoría v0.9.5, A-1] `ok=True` exige FUNDAMENTO: al menos una tool
    ejecutada con éxito. Un answer sin ninguna tool detrás es, por contrato,
    un fallo — aunque suene convincente. Es la misma regla de honestidad de R1
    (doc 23 Δ2), cerrada ahora también por la vía del answer temprano."""
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
3. Las marcadas [PIDE PERMISO AL USUARIO] puedes pedirlas con normalidad: se le
   preguntará a él y decidirá. Si no las concede, respétalo y busca otra vía.
4. Si una herramienta falla o te la deniegan, léelo, y busca otra vía o explica el
   límite en tu respuesta final. No lo ocultes.
5. Cuando ya tengas lo necesario, responde con {"answer": ...} basándote SOLO en lo
   que las herramientas te devolvieron de verdad.
6. Para buscar algo en internet (una página, un vídeo, una canción, una noticia):
   usa "search.search_web" (o search_news/search_images/search_videos) para
   encontrar la URL, y LUEGO "browser.open_url" para abrirla. NUNCA uses
   "browser.google_search": Google bloquea la navegación automatizada y falla."""


def build_catalog(allowed_tools: list[str], tool_manager) -> list[dict]:
    """El catálogo de acciones que el modelo puede pedir en ESTE nodo:
    intersección de la whitelist del nodo con lo que hay registrado de verdad.

    Incluye TODAS las acciones permitidas al nodo, también las sensibles, cada
    una marcada con `needs_approval`. Ocultarlas sería denegar sin preguntar: el
    modelo ni siquiera podría proponerlas y el usuario no se enteraría de que
    hacían falta. Lo correcto es que el modelo pueda pedirlas y que la decisión
    la tome el USUARIO en el ApprovalGate (regla del usuario, 2026-07-19).

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
            catalog.append({
                "tool_id": tool["tool_id"],
                "action": action.get("id"),
                "description": action.get("description", ""),
                "params": action.get("params", {}),
                "needs_approval": _is_sensitive(tool, action),
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
        mark = "  [PIDE PERMISO AL USUARIO]" if entry.get("needs_approval") else ""
        lines.append(
            f'- tool_id="{entry["tool_id"]}" action="{entry["action"]}" — '
            f'{entry["description"]}' + (f" | params: {params}" if params else "") + mark
        )
    return "\n".join(lines)


async def _ask_permission(entry: dict, params: dict, approval_gate, *,
                          instruction: str, wait_s: int,
                          pre_approved: bool = False) -> tuple[bool, str]:
    """Pide permiso al USUARIO para una acción sensible y espera su respuesta.

    Por qué se pregunta en vez de denegar (regla del usuario, 2026-07-19): el
    planner marca los pasos sensibles que ANTICIPA, pero a mitad de ejecución el
    modelo puede descubrir que necesita uno que no estaba previsto. Denegarlo en
    silencio dejaría al usuario sin enterarse de que hacía falta. Así que se abre
    un ApprovalGate real: queda persistido, notificado y auditado.

    Si el usuario tiene ese permiso PRE-AUTORIZADO (A3b), el gate se auto-resuelve
    al instante y esto no añade fricción — es el caso común.

    Devuelve (concedido, motivo). La espera está acotada: si no contesta a
    tiempo, se sigue sin esa acción y la respuesta final lo dirá — la aprobación
    NO se cancela, sigue pendiente en la UI por si la quiere resolver luego."""
    # [Fix 2026-07-19] ¿El usuario aprobó YA este paso entero? Aprobar el PLAN
    # (o el gate de este nodo) autoriza sus acciones sensibles: vio la lista
    # completa y dijo que sí. Volver a preguntar acción por acción después de
    # eso es exactamente lo que hacía que aprobar el plan "no sirviera de nada".
    if pre_approved:
        return True, "ya lo aprobaste al dar el visto bueno a este paso"

    # ¿YA lo autorizó el usuario en Ajustes → Permisos?
    #
    # EL BUG: se abría un gate con `kind="tool.email.send_email"`, un id que NO
    # existe en el catálogo de permisos (que usa `email.send`). Como
    # `is_pre_authorized` es fail-closed, el perfil "Autónomo" con los 9
    # permisos activados no servía de nada: preguntaba igualmente, hasta para
    # enviar un email que el usuario acababa de pedir por el chat.
    #
    # Ahora se traduce la acción a su permiso real ANTES de molestar a nadie.
    # Sigue habiendo rastro: el gate se abre igual y se auto-resuelve dentro de
    # `request_approval` (A3b) — "pre-autorizado NUNCA significa silencioso".
    try:
        from app.automation import permission_service

        if permission_service.is_tool_action_pre_authorized(entry["tool_id"], entry["action"]):
            logger.info(
                f"[toolloop] {entry['tool_id']}.{entry['action']} ya está autorizado "
                f"en Ajustes → Permisos; no se pregunta"
            )
            return True, "autorizado de antemano por el usuario"
    except Exception as e:      # nunca bloquear por un fallo consultando permisos
        logger.info(f"[toolloop] no se pudo consultar el permiso (sigo preguntando): {e!r}")

    if approval_gate is None:
        return False, "no hay canal de aprobación disponible en este contexto"

    gate_id = await approval_gate.request_approval(
        kind=f"tool.{entry['tool_id']}.{entry['action']}",
        title=f"Permiso para {entry['tool_id']}.{entry['action']}",
        summary=(f"Un paso de la misión necesita ejecutar "
                 f"{entry['tool_id']}.{entry['action']} con: "
                 f"{json.dumps(params, ensure_ascii=False)[:300]}\n\nPaso: {instruction[:200]}"),
        # El gate ejecuta la acción solo si hay un ejecutor registrado para este
        # action_type; aquí NO lo hay a propósito: quien ejecuta es el bucle, con
        # el ToolManager y su whitelist. El gate solo aporta el SÍ/NO del usuario.
        action_type="tie_tool_permission",
        action_payload={"tool_id": entry["tool_id"], "action": entry["action"], "params": params},
    )

    deadline = asyncio.get_running_loop().time() + wait_s
    while asyncio.get_running_loop().time() < deadline:
        appr = approval_gate.get(gate_id)
        status = getattr(appr, "status", None)
        if status == "approved":
            return True, "aprobado por el usuario"
        if status == "rejected":
            return False, "el usuario ha rechazado esta acción"
        await asyncio.sleep(1.0)

    # [Auditoría v0.9.5, A-2] Timeout → la aprobación se EXPIRA, nunca se deja
    # `pending`. Antes quedaba viva en la UI pero aprobarla después no hacía
    # NADA (la misión ya había seguido y `tie_tool_permission` no tiene
    # ejecutor a propósito): el usuario aprobaba y el sistema lo ignoraba —
    # una aprobación cadáver. Expirarla es la semántica honesta: desaparece de
    # pendientes, queda auditada como caducada, y el modelo busca otra vía o
    # explica el límite. (La alternativa —pausar el nodo como gate de T3—
    # exigiría persistir el transcript del bucle en el checkpoint; anotada
    # como evolución V1.1 en el doc 25, no como parche aquí.)
    expired = await approval_gate.expire(
        gate_id, note="caducada: el paso siguió sin esta acción tras esperar sin respuesta"
    )
    if not expired:
        # El usuario resolvió JUSTO al final y ganó la carrera: honrar su veredicto.
        appr = approval_gate.get(gate_id)
        if getattr(appr, "status", None) == "approved":
            return True, "aprobado por el usuario (justo a tiempo)"
        return False, "el usuario ha rechazado esta acción"

    return False, (
        "pedí permiso al usuario y no respondió a tiempo; la solicitud ha caducado "
        "y he seguido sin esa acción"
    )


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
    approval_gate=None,
    approval_wait_s: int = 120,
    model_override: Optional[str] = None,
    project_id: Optional[int] = None,
    timeout_s: int = 60,
    authority: Optional["Authority"] = None,
    pre_approved: bool = False,
    session_key: Optional[str] = None,
) -> ToolLoopResult:
    """Ejecuta el ciclo elegir→ejecutar→observar.

    NO lanza: cualquier fallo se devuelve como `ToolLoopResult(ok=False)` para
    que el runtime decida su degradación. La única excepción que SÍ se propaga es
    `CancelledError`: el kill-switch del executor (T3) tiene que poder cortar un
    nodo en vuelo, y tragarse esa cancelación lo rompería."""
    from app.mel import Capability, ExecutionRequest, complete as mel_complete

    # [R4] Defensa en profundidad: el planner ya recortó `node.tools` a la
    # whitelist del agente ANTES de guardar el grafo, así que aquí normalmente
    # esto no quita nada. Se repite porque el coste es una línea y cubre los
    # caminos que no pasan por el planner (una misión reanudada, un grafo
    # construido a mano, un caller futuro que se olvide de recortar).
    if authority is not None and authority.allowed_tools is not None:
        from app.tie.authority import _internal_tool_ids

        permitidas = set(authority.allowed_tools) | _internal_tool_ids()
        allowed_tools = [t for t in allowed_tools if t in permitidas]

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
    by_pair = {(e["tool_id"], e["action"]): e for e in catalog}

    # [Opt latencia 2026-07-21] EL bucle domina la latencia (1 llamada/acción).
    # Se fuerza un modelo RÁPIDO: un modelo fijado (TIE_TOOL_MODEL) tiene máxima
    # prioridad; si no, la política TIE_TOOL_POLICY (default "economy",
    # local-primero). Nunca el modelo de calidad del usuario, que puede ser
    # opus/gpt y tardar 15s POR PASO. `model_override` (el usuario dijo "usa X
    # para esto") sigue mandando sobre todo.
    from app.core.config import settings as _settings
    _tool_model = model_override or (_settings.TIE_TOOL_MODEL or None)
    _tool_policy = None if _tool_model else _settings.TIE_TOOL_POLICY

    for iteration in range(1, max_iters + 1):
        # [Opt latencia · profiling] tiempo de la decisión del modelo por paso —
        # así se ve en el log del backend cuánto tarda CADA acción de la misión.
        _t_iter = asyncio.get_event_loop().time()
        res = await mel_complete(ExecutionRequest(
            capability=Capability.AGENTIC,
            prompt="\n\n".join(transcript),
            system_prompt=_SYSTEM_PROMPT,
            model_override=_tool_model,
            policy_override=_tool_policy,
            context_tags={"project_id": project_id} if project_id else {},
        ))
        _ms = int((asyncio.get_event_loop().time() - _t_iter) * 1000)
        logger.info(f"[tie-perfil] toolloop paso {iteration}: modelo {_ms}ms"
                    f" (served_by={getattr(res, 'served_by', '?')})")
        if not res.ok:
            return ToolLoopResult(ok=False, tool_calls=tool_calls, iterations=iteration,
                                  error=f"el modelo no respondió: {res.error}")

        # [A-1] ¿Hay FUNDAMENTO? Al menos una tool ejecutada con éxito. Sin esto,
        # ningún answer se acepta como éxito: sería una respuesta inventada con
        # forma de misión cumplida (el fallo A de la auditoría v0.9.5).
        grounded = any(c.get("ok") for c in tool_calls)
        attempted = len(tool_calls) > 0

        data = _extract_json(res.text)
        if not data:
            # El modelo respondió en prosa. En la última vuelta se conserva el
            # texto (mejor eso que nada), pero `ok` sigue exigiendo fundamento;
            # si no lo hay, el nodo falla con el texto como explicación.
            if iteration >= max_iters:
                text_out = res.text.strip()
                if grounded:
                    return ToolLoopResult(ok=bool(text_out), answer=text_out,
                                          tool_calls=tool_calls, iterations=iteration)
                return ToolLoopResult(
                    ok=False, answer=text_out, tool_calls=tool_calls, iterations=iteration,
                    error=(text_out[:500] if text_out else "sin respuesta")
                          + " [sin fundamento: ninguna herramienta se ejecutó con éxito]",
                )
            transcript.append(f"TU RESPUESTA:\n{res.text[:500]}")
            transcript.append('ERROR: responde SOLO con JSON, {"tool": {...}} o {"answer": "..."}.')
            continue

        if "answer" in data:
            answer = str(data["answer"]).strip()
            if grounded:
                return ToolLoopResult(ok=bool(answer), answer=answer,
                                      tool_calls=tool_calls, iterations=iteration,
                                      error=None if answer else "el modelo respondió vacío")
            # Sin fundamento. Dos casos, con trato distinto:
            # (a) NI SIQUIERA lo intentó → se le rechaza el answer y se le exige
            #     usar herramientas (hasta agotar vueltas).
            # (b) Lo intentó y TODO falló/fue denegado → su answer es con toda
            #     probabilidad la explicación honesta del límite; se acepta como
            #     FALLO con esa explicación — el responder la contará tal cual,
            #     nunca como éxito.
            if not attempted and iteration < max_iters:
                transcript.append(
                    "RECHAZADO: no has ejecutado NINGUNA herramienta todavía. Este paso "
                    "requiere datos reales del sistema: obténlos con una herramienta del "
                    "catálogo antes de responder. No inventes el resultado."
                )
                continue
            return ToolLoopResult(
                ok=False, answer=answer, tool_calls=tool_calls, iterations=iteration,
                error=(answer[:500] if answer else "el modelo respondió vacío")
                      + " [sin fundamento: ninguna herramienta se ejecutó con éxito]",
            )

        call = data.get("tool")
        if not isinstance(call, dict):
            transcript.append('ERROR: el JSON debe tener "tool" o "answer".')
            continue

        tool_id, action = call.get("tool_id"), call.get("action")
        params = call.get("params") or {}
        transcript.append(f"HAS PEDIDO: {json.dumps(call, ensure_ascii=False)[:400]}")

        # ¿Está en el catálogo de este nodo? Si no, es una tool inventada o fuera
        # de su whitelist: se rechaza con MOTIVO, y el motivo vuelve al modelo
        # para que busque otra vía — no se corta el bucle en seco.
        entry = by_pair.get((tool_id, action))
        if entry is None:
            reason = _denial_reason(tool_id, action, allowed_tools, tool_manager)
            transcript.append(f"DENEGADO: {reason}")
            tool_calls.append({"tool_id": tool_id, "action": action, "denied": True, "reason": reason})
            continue

        # [R4] ¿Está DENTRO del alcance del encargo? Esto NO es un permiso que el
        # usuario pueda conceder sobre la marcha (para eso está el gate de abajo),
        # es la frontera de autoridad de la misión: los agentes de otro proyecto,
        # las carpetas de otro proyecto. Se deniega, pero NUNCA en silencio — el
        # motivo vuelve al modelo y queda en `tool_calls`, así que sale en la
        # traza de la misión y en la respuesta final.
        if authority is not None:
            out_of_scope = authority.check(tool_id, action, params)
            if out_of_scope:
                transcript.append(f"FUERA DE TU ALCANCE: {out_of_scope}")
                tool_calls.append({"tool_id": tool_id, "action": action,
                                   "denied": True, "out_of_scope": True, "reason": out_of_scope})
                continue

        # [S2-extra, C-1b] ESCRITURA ETIQUETADA — la otra mitad del aislamiento
        # de proyecto: una memoria guardada DENTRO de una misión de proyecto
        # queda etiquetada con ese proyecto, determinista, sin depender de que
        # el modelo se acuerde de incluirlo. Así el filtro de lectura del MOS
        # tiene siempre la etiqueta que necesita y dos proyectos no se mezclan
        # ni al leer ni al escribir.
        if (tool_id == "memory" and action in ("save_memory", "save", "update_memory")
                and authority is not None and authority.project_id):
            meta = dict(params.get("metadata") or {})
            meta.setdefault("project_id", authority.project_id)
            params["metadata"] = meta

        # [S3, F-1] SESIÓN DE NAVEGADOR POR MISIÓN. El browser aísla pestañas y
        # cookies por `_session`: dos misiones concurrentes no pueden pisarse la
        # pestaña activa. Lo inyecta el bucle (no el modelo) desde el id de la
        # misión — el modelo ni lo ve ni puede falsearlo.
        if tool_id == "browser" and session_key:
            params["_session"] = session_key

        # Acción sensible → se PREGUNTA al usuario (nunca se deniega por
        # nuestra cuenta). Con el permiso pre-autorizado (A3b) esto es instantáneo.
        if entry.get("needs_approval"):
            granted, reason = await _ask_permission(
                entry, params, approval_gate,
                instruction=instruction, wait_s=approval_wait_s,
                pre_approved=pre_approved,
            )
            tool_calls.append({"tool_id": tool_id, "action": action,
                               "needed_approval": True, "granted": granted, "reason": reason})
            if not granted:
                transcript.append(f"SIN PERMISO para {tool_id}.{action}: {reason}")
                continue
            transcript.append(f"PERMISO CONCEDIDO para {tool_id}.{action}.")

        _tool_t0 = time.monotonic()
        result = await tool_manager.execute(
            tool_id=tool_id,
            action=action,
            params=params,
            allowed_tools=list(allowed_tools),     # la whitelist del nodo, otra vez
            timeout=timeout_s,
        )
        tool_calls.append({"tool_id": tool_id, "action": action,
                           "ok": bool(result.get("success")), "error": result.get("error")})
        # [2026-07-21, doc 31] Telemetría: cada tool ejecutada, con duración y
        # resultado (el error truncado, nunca el contenido). Best-effort.
        try:
            import app.telemetry as _telemetry

            _telemetry.record(
                "tool_call", name=f"{tool_id}.{action}",
                duration_ms=int((time.monotonic() - _tool_t0) * 1000),
                ok=bool(result.get("success")),
                detail={"error": str(result.get("error"))[:200]} if result.get("error") else None,
            )
        except Exception:
            pass

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
    return f"'{tool_id}' no tiene la acción '{action}'. Usa solo las del catálogo."
