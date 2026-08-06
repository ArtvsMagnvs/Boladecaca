# app/learner/stats.py — agregación de model_stats / tool_stats (V1.1 L2)
#
# DETERMINISTA y sin LLM: toma el timeline que la telemetría YA escribe (doc 31,
# cero instrumentación nueva — doc 15 §2) y lo suma a las medias históricas.
# Corre SIEMPRE, incluso en las misiones triviales donde no hay reflexión: los
# contadores son gratis, y una charla también dice qué modelo respondió y cuánto
# tardó (doc 15 §4, nota de coste).
#
# INCREMENTAL, nunca recalculado desde cero: `mission_events` se purga a los 30
# días (doc 31) y estas medias tienen que sobrevivir a esa purga. Una fila por
# (capability, provider, model) y por tool.
#
# IDEMPOTENCIA: agregar dos veces la misma misión duplicaría los contadores. Se
# evita con `learner_proposals`… no: con un registro propio y barato — el
# `MemoryJobRun` del MOS no vale aquí (es por job, no por misión), así que el
# guardián es el propio `mission_learning`, que solo llama una vez por evento y
# lleva un ring de misiones ya procesadas. Documentado ahí.
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.failures import (
    FailureKind,
    blame_of,
    dominant,
    is_excused,
    settings_hint as _settings_hint,
)
from app.core.logging_config import get_system_logger
from app.db.database import SessionLocal
from app.learner.models import FailureStat, ModelStat, ToolStat

logger = get_system_logger("learner.stats")

_MAX_SAMPLES = 10          # misiones de ejemplo por fila de failure_stats


def split_model_key(key: str) -> tuple[str, str]:
    """"provider:model" → (provider, model). La telemetría guarda la clave así
    (`f"{provider}:{model}"`); un modelo local puede llevar `:` en su nombre
    (`qwen2.5vl:7b`), así que se parte por el PRIMERO."""
    if ":" not in key:
        return ("?", key or "?")
    provider, _, model = key.partition(":")
    return (provider or "?", model or "?")


# Qué pieza del TIE corresponde a cada etapa de la telemetría, para cuando el
# fallo no tiene ni tool ni modelo a los que apuntar.
_PIEZA_POR_ETAPA = {
    "planning": "tie:planner",
    "toolloop": "tie:toolloop",
    "tool_call": "tie:toolloop",
    "node_end": "tie:executor",
    "llm_call": "mel",
}


def _pieza_del_tie(stage: str) -> str:
    return _PIEZA_POR_ETAPA.get(stage or "", stage or "?")


def _mensaje_y_tool(detalle: dict) -> tuple:
    """El texto REAL del fallo y la herramienta a la que se refiere.

    Los tres primeros son la forma normal. El cuarto es el PREFLIGHT (doc 40
    Sesión A), que guarda su motivo bajo `{"tools": {"<id>": "<mensaje>"}}` —
    y ahí está justo lo que hace accionable el aviso: qué falta y en qué
    herramienta. Sin leer esa forma, la propuesta de configuración salía sin
    destino ni nombre: un aviso que solo sabe quejarse. Lo encontró el test de
    punta a punta, porque es el único que pasa por el evento REAL del preflight
    en vez de por un `detail` escrito a mano."""
    for clave in ("error", "reason", "notes"):
        if detalle.get(clave):
            return str(detalle[clave])[:300], detalle.get("tool")
    faltan = detalle.get("tools")
    if isinstance(faltan, dict) and faltan:
        tool = next(iter(faltan))
        return str(faltan[tool])[:300], tool
    return "", detalle.get("tool")


def failures_in(timeline: dict) -> list[dict]:
    """[L2b] Los fallos ATRIBUIDOS de un timeline, extraídos de los eventos que
    los hooks ya anotaron con `failure_kind`/`blame`. Función pura: no toca BD.

    Devuelve una lista de `{kind, blame, component, model_key, tool, event_key,
    detail}` — todo lo que `failure_stats` necesita para una fila, más el `kind`
    suelto para que el llamador calcule el dominante."""
    out: list[dict] = []
    for ev in (timeline or {}).get("events") or []:
        detalle = ev.get("detail") or {}
        kind = detalle.get("failure_kind")
        if not kind:
            continue
        stage = ev.get("stage") or ""
        nombre = ev.get("name") or ""
        culpa = detalle.get("blame") or blame_of(kind)
        model_key = (f"{ev.get('provider')}:{ev.get('model')}"
                     if ev.get("provider") and ev.get("model") else None)
        mensaje, tool_detalle = _mensaje_y_tool(detalle)
        tool = tool_detalle or (nombre.split(".", 1)[0]
                                if stage == "tool_call" and "." in nombre else None)

        # De DÓNDE viene. LA ÚNICA REGLA DURA: si la culpa es del MODELO, el
        # componente jamás es una tool. Esa es la corrección de la revisión —
        # una petición de tool INVENTADA se graba como `tool_call` denegado, y
        # derivando el componente de la etapa cada nombre que el modelo se
        # sacara de la manga creaba una fila `tool:<alucinación>` permanente,
        # con la culpa apuntando a algo que ni existe.
        #
        # El resto sí quiere el nombre de la tool aunque la culpa sea externa o
        # de config: "falta la API key de SEARCH" es exactamente lo que hace
        # accionable la propuesta. Sin el nombre, el aviso sería "algo del
        # bucle de herramientas no está configurado" — inútil.
        if culpa == "model":
            componente = f"model:{model_key}" if model_key else _pieza_del_tie(stage)
        elif tool:
            componente = f"tool:{tool}"
        elif model_key:
            componente = f"model:{model_key}"
        else:
            componente = _pieza_del_tie(stage)

        out.append({
            "kind": kind,
            "blame": culpa,
            "component": componente,
            "model_key": model_key,
            # `tool` se conserva aunque el componente no sea la tool: sigue
            # siendo el CONTEXTO donde ocurrió (útil para el panel), pero ya no
            # decide de quién es la culpa.
            "tool": tool,
            # La clave EXACTA del agregado de tools del timeline ("tool.action"),
            # que es también la clave de `ToolStat.tool`. Sin ella, contar los
            # fallos externos por tool y no por acción hacía que dos acciones de
            # la misma tool se sumaran el total la una a la otra.
            "event_key": nombre if stage == "tool_call" else None,
            "detail": mensaje,
        })
    return out


def record_failures(mission_id: str, fallos: list[dict]) -> int:
    """Suma los fallos de una misión a `failure_stats`. Una fila por
    (kind, component): el mismo fallo repetido en la misma misión cuenta las
    veces que ocurrió (es señal de insistencia), pero el `mission_id` solo se
    guarda UNA vez en el ring de ejemplos."""
    if not fallos:
        return 0
    ahora = datetime.utcnow()

    # (1) Se agrupa ANTES de tocar la BD: una fila por (kind, componente) con
    # cuántas veces pasó en esta misión. Así el UPDATE es uno solo por clave —
    # ni una fila duplicada por repetición (el `autoflush=False` de
    # `SessionLocal` hace invisible lo recién añadido para el query siguiente),
    # ni un contador incrementado a trompicones.
    agrupados: Dict[tuple, dict] = {}
    for f in fallos:
        clave = (f["kind"], f["component"])
        acc = agrupados.setdefault(clave, {"n": 0, "blame": f["blame"],
                                           "model_key": None, "tool": None,
                                           "detail": ""})
        acc["n"] += 1
        acc["blame"] = f["blame"]
        acc["model_key"] = f.get("model_key") or acc["model_key"]
        acc["tool"] = f.get("tool") or acc["tool"]
        acc["detail"] = f.get("detail") or acc["detail"]

    with SessionLocal() as s:
        for (kind, componente), acc in agrupados.items():
            fila = (s.query(FailureStat)
                    .filter(FailureStat.kind == kind,
                            FailureStat.component == componente).first())
            if fila is None:
                fila = FailureStat(kind=kind, blame=acc["blame"],
                                   component=componente, count=acc["n"],
                                   sample_mission_ids=[])
                s.add(fila)
            else:
                # (2) Incremento ATÓMICO: lo calcula la BD, no Python. Dos
                # misiones que fallan por lo mismo casi a la vez —normal con el
                # Orquestador corriendo varias en paralelo— leerían las dos el
                # mismo valor y escribirían las dos el mismo +1, perdiendo una
                # cuenta. Un contador que se queda corto no es solo impreciso:
                # es el que decide si el usuario llega a ver la propuesta de
                # arreglo, así que perder cuentas es perder avisos.
                fila.count = FailureStat.count + acc["n"]
            fila.blame = acc["blame"]        # por si el mapeo se afina luego
            fila.model_key = acc["model_key"] or fila.model_key
            fila.tool = acc["tool"] or fila.tool
            fila.last_seen = ahora
            fila.updated_at = ahora
            if acc["detail"]:
                fila.last_detail = acc["detail"]
            muestras = list(fila.sample_mission_ids or [])
            if mission_id and mission_id not in muestras:
                muestras.append(mission_id)
                fila.sample_mission_ids = muestras[-_MAX_SAMPLES:]
        s.commit()
    return len(fallos)


def aggregate_from_timeline(timeline: dict, *, mission_ok: bool,
                            capability_hint: str = "mission",
                            excused: bool = False,
                            fallos: Optional[list[dict]] = None) -> dict:
    """Suma UN timeline a las tablas. Devuelve un resumen de lo escrito.

    `mission_ok` es la señal que da valor a todo esto: no "¿respondió el
    modelo?" sino "¿sirvió la misión?". Se propaga a TODOS los modelos que
    participaron — atribuir el mérito por nodo exigiría saber qué nodo fue
    decisivo, y eso es adivinar; contar participación es honesto y, con
    volumen, igual de informativo.

    `capability_hint`: el timeline de la telemetría no guarda la capability de
    cada llamada (solo provider/model), así que se agrega bajo una etiqueta
    común. Cuando la telemetría la registre, este parámetro deja de hacer falta
    y las filas se separan solas — por eso es un campo de la tabla desde ya.

    [L2b] `excused`: la misión falló, pero por algo AJENO al modelo. Entonces
    suma a `missions_excused` en vez de contar como derrota — la petición
    literal del usuario ("que los fallos de conexión no cuenten como errores
    del sistema"), aplicada donde de verdad importa: en el denominador.

    `fallos`: los de `failures_in(timeline)`, si el llamador ya los calculó.
    Se acepta para que la atribución se extraiga UNA vez por misión y no haya
    dos lecturas del mismo timeline que puedan divergir."""
    resumen = (timeline or {}).get("summary") or {}
    if fallos is None:
        fallos = failures_in(timeline)
    por_modelo: Dict[str, Any] = resumen.get("llm_by_model") or {}
    por_tool: Dict[str, Any] = resumen.get("tools") or {}
    ahora = datetime.utcnow()
    escritos = {"models": 0, "tools": 0}

    with SessionLocal() as s:
        for key, agg in por_modelo.items():
            provider, model = split_model_key(str(key))
            if model in ("?", ""):
                continue                       # sin modelo identificable: no se aprende nada
            fila = (s.query(ModelStat)
                    .filter(ModelStat.capability == capability_hint,
                            ModelStat.provider == provider,
                            ModelStat.model == model).first())
            if fila is None:
                fila = ModelStat(capability=capability_hint, provider=provider,
                                 model=model)
                s.add(fila)
            fila.missions = int(fila.missions or 0) + 1
            fila.missions_ok = int(fila.missions_ok or 0) + (1 if mission_ok else 0)
            if excused and not mission_ok:
                fila.missions_excused = int(fila.missions_excused or 0) + 1
            fila.calls = int(fila.calls or 0) + int(agg.get("calls") or 0)
            fila.call_fails = int(fila.call_fails or 0) + int(agg.get("fails") or 0)
            fila.total_ms = int(fila.total_ms or 0) + int(agg.get("ms") or 0)
            lento = int(resumen.get("slowest_llm_ms") or 0)
            fila.slowest_ms = max(int(fila.slowest_ms or 0), lento)
            fila.last_used = ahora
            fila.updated_at = ahora
            escritos["models"] += 1

        # [L2b] Cuántos de los fallos de CADA fila de tool fueron ajenos a ella
        # (red, cuota, config). El agregado del timeline no lo trae — hay que
        # mirar los eventos, que sí llevan la atribución que puso el hook.
        # Se cuenta por `event_key` ("tool.action"), la MISMA clave que usa
        # `ToolStat`: agrupar por tool a secas hacía que `search.search_web` y
        # `search.search_news` se sumaran mutuamente sus fallos externos, y
        # `fails_external` podía acabar siendo mayor que `fails`.
        externos: Dict[str, int] = {}
        for f in fallos:
            if f.get("event_key") and f.get("blame") in ("external", "config"):
                externos[f["event_key"]] = externos.get(f["event_key"], 0) + 1

        for nombre, agg in por_tool.items():
            if not nombre or nombre == "?":
                continue
            fila = s.query(ToolStat).filter(ToolStat.tool == nombre).first()
            if fila is None:
                fila = ToolStat(tool=nombre)
                s.add(fila)
            fila.missions = int(fila.missions or 0) + 1
            fila.calls = int(fila.calls or 0) + int(agg.get("calls") or 0)
            fila.fails = int(fila.fails or 0) + int(agg.get("fails") or 0)
            # Acotado a los fallos REALES de esta pasada: un `detail` mal
            # formado no puede hacer que `fails_external` supere a `fails`.
            fila.fails_external = int(fila.fails_external or 0) + min(
                externos.get(nombre, 0), int(agg.get("fails") or 0))
            fila.total_ms = int(fila.total_ms or 0) + int(agg.get("ms") or 0)
            fila.last_used = ahora
            fila.updated_at = ahora
            escritos["tools"] += 1

        s.commit()
    return escritos


async def record_mission(mission_id: str, *, ok: bool) -> dict:
    """Agrega la misión `mission_id` (async: la BD va por to_thread).

    [L2b] Además de los contadores, atribuye: extrae los fallos ya etiquetados
    por los hooks, elige el DOMINANTE (el que explica por qué acabó así) y
    decide si la misión queda excusada. Devuelve también esa atribución para
    que `mission_learning` la mencione en la reflexión sin re-calcularla."""
    def _work() -> dict:
        from app.telemetry import mission_timeline

        timeline = mission_timeline(mission_id)
        fallos = failures_in(timeline)
        dom = dominant([f["kind"] for f in fallos]) if fallos else None
        # Solo se excusa una misión FALLIDA: una que salió bien no necesita
        # perdón, y contarla como excusada la sacaría del denominador
        # inflando artificialmente la tasa del modelo.
        excusada = bool(dom) and not ok and is_excused(dom)
        out = aggregate_from_timeline(timeline, mission_ok=ok, excused=excusada,
                                      fallos=fallos)
        out["failures"] = record_failures(mission_id, fallos)
        out["dominant_kind"] = dom.value if dom else None
        out["blame"] = blame_of(dom) if dom else None
        out["excused"] = excusada
        return out

    try:
        return await asyncio.to_thread(_work)
    except Exception as e:
        logger.info(f"[stats] agregación de {mission_id} falló (no crítico): {e!r}")
        return {"models": 0, "tools": 0, "failures": 0,
                "dominant_kind": None, "blame": None, "excused": False}


# ---------------------------------------------------------------------------
# Lectura (la usarán el Model Router en V1.2 y el panel en L4)
# ---------------------------------------------------------------------------
def model_ranking(capability: Optional[str] = None, min_missions: int = 1) -> list[dict]:
    """Modelos ordenados por TASA DE ÉXITO DE MISIÓN, no por latencia ni por
    tasa de respuesta técnica. `min_missions` evita que un modelo con una sola
    misión afortunada encabece la lista (misma disciplina que la escalera: una
    racha no es evidencia)."""
    with SessionLocal() as s:
        q = s.query(ModelStat).filter(ModelStat.missions >= min_missions)
        if capability:
            q = q.filter(ModelStat.capability == capability)
        filas = q.all()
    out = []
    for f in filas:
        misiones = int(f.missions or 0)
        excusadas = int(getattr(f, "missions_excused", 0) or 0)
        llamadas = int(f.calls or 0)
        # [L2b] LA FÓRMULA JUSTA: las misiones excusadas salen del denominador.
        # Un modelo que participó en 10 misiones, 7 buenas y 3 caídas por falta
        # de red, tiene un 100% — no un 70%. `contadas` nunca baja de 0 aunque
        # los contadores llegaran desalineados de una versión anterior.
        contadas = max(misiones - excusadas, 0)
        out.append({
            "capability": f.capability, "provider": f.provider, "model": f.model,
            "missions": misiones, "missions_ok": int(f.missions_ok or 0),
            "missions_excused": excusadas,
            "mission_success_rate": (f.missions_ok / contadas) if contadas else 0.0,
            "calls": llamadas, "call_fails": int(f.call_fails or 0),
            "call_fail_rate": (f.call_fails / llamadas) if llamadas else 0.0,
            "avg_ms": int(f.total_ms / llamadas) if llamadas else 0,
            "slowest_ms": int(f.slowest_ms or 0),
            "last_used": f.last_used.isoformat() if f.last_used else None,
        })
    out.sort(key=lambda x: (x["mission_success_rate"], x["missions"]), reverse=True)
    return out


def tool_ranking(min_calls: int = 1) -> list[dict]:
    """Herramientas ordenadas por TASA DE FALLO descendente: lo primero que se
    quiere ver es lo que está rompiéndose."""
    with SessionLocal() as s:
        filas = s.query(ToolStat).filter(ToolStat.calls >= min_calls).all()
    out = []
    for f in filas:
        llamadas = int(f.calls or 0)
        fallos = int(f.fails or 0)
        externos = int(getattr(f, "fails_external", 0) or 0)
        # [L2b] Misma justicia que con los modelos: la tasa de error de una
        # tool mide lo que ELLA hace mal. Un timeout de red dentro de `search`
        # es de la red — se cuenta aparte y se ve, pero no la condena.
        propios = max(fallos - externos, 0)
        out.append({
            "tool": f.tool, "missions": int(f.missions or 0), "calls": llamadas,
            "fails": fallos, "fails_external": externos,
            "error_rate": (propios / llamadas) if llamadas else 0.0,
            "avg_ms": int(f.total_ms / llamadas) if llamadas else 0,
            "last_used": f.last_used.isoformat() if f.last_used else None,
        })
    out.sort(key=lambda x: (x["error_rate"], x["calls"]), reverse=True)
    return out


CONFIG_FIX_THRESHOLD = 3   # repeticiones antes de molestar al usuario


def config_gaps(threshold: int = CONFIG_FIX_THRESHOLD) -> list[dict]:
    """[L2b] Configuraciones que llevan estorbando lo bastante como para
    proponer arreglarlas. LECTURA pura — no crea nada (quien crea propuestas es
    `proposal_service`, y este módulo no lo conoce).

    El umbral existe por respeto: un fallo de configuración aislado puede ser
    un experimento del usuario o algo que ya arregló. Tres veces la misma
    carencia ya no es ruido, es un estorbo real.

    Se filtra por CULPA (`blame == "config"`) y no por un kind concreto: así
    entra tanto un `config_missing` del preflight como un `provider_auth`
    repetido (una API key caducada es igual de arreglable por el usuario), y
    un kind nuevo con esa misma culpa quedará cubierto sin tocar esto."""
    with SessionLocal() as s:
        filas = (s.query(FailureStat)
                 .filter(FailureStat.blame == "config",
                         FailureStat.count >= threshold).all())
    return [{
        "kind": f.kind,
        "component": f.component,
        "count": int(f.count or 0),
        "detail": f.last_detail or "",
        # La pista de a dónde ir se calcula sobre el mensaje REAL del preflight,
        # que es quien sabe qué falta ("añade una API key de SerpAPI o Brave en
        # Ajustes → Búsqueda web"). Ese texto es además el que ve el usuario.
        "settings_tab": _settings_hint(f.last_detail or f.component or ""),
        "dedup_key": f"config:{f.component}",
        "sample_mission_ids": list(f.sample_mission_ids or []),
    } for f in filas]


def failure_summary(min_count: int = 1) -> dict:
    """[L2b] Lo que pinta la pestaña "Salud" del panel (L4): el reparto de
    fallos por CULPA, y el detalle por tipo y componente. Lectura pura.

    El bucket `unknown` se devuelve como uno más, a propósito: lo que el
    sistema no sabe atribuir tiene que verse — esconderlo daría una foto más
    bonita y menos cierta."""
    with SessionLocal() as s:
        filas = s.query(FailureStat).filter(FailureStat.count >= min_count).all()

    por_culpa: Dict[str, int] = {}
    detalle = []
    for f in filas:
        n = int(f.count or 0)
        por_culpa[f.blame] = por_culpa.get(f.blame, 0) + n
        detalle.append({
            "kind": f.kind, "blame": f.blame, "component": f.component,
            "model_key": f.model_key, "tool": f.tool, "count": n,
            "last_seen": f.last_seen.isoformat() if f.last_seen else None,
            "sample_mission_ids": list(f.sample_mission_ids or []),
            "last_detail": f.last_detail,
        })
    detalle.sort(key=lambda x: x["count"], reverse=True)
    return {"total": sum(por_culpa.values()), "by_blame": por_culpa, "items": detalle}
