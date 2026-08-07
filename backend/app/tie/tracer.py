# app/tie/tracer.py — Trace & Learn del TIE (doc 11-B §B.1/§6, T1 base)
#
# Escribe la traza de cada misión en `orchestrator_traces` (estado operativo del
# TIE en SQL — NO en el MOS). En T1: record_start / record_intent / record_end.
# En T2 se añade el espejo Decision API (record_plan); en T3 el checkpoint por
# transición (update_graph); en T4 los eventos mission.* + el outcome del
# responder. Es la fuente de la que el Learner (V1.1) aprende (doc 14 §4.4).
#
# BEST-EFFORT SIEMPRE: un fallo del tracer nunca rompe el pipeline (la respuesta
# al usuario es lo primero). Cada método traga sus excepciones y loguea.
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional

from app.core.logging_config import get_system_logger
from app.db.database import OrchestratorTrace, SessionLocal
from app.tie.contracts import Intent, Mission, TaskGraph

logger = get_system_logger("tie.tracer")


def record_start(mission: Mission, *, channel: Optional[str] = None) -> str:
    """Abre una traza para una misión. Devuelve el trace_id (uuid). El trace_id
    y el mission_id son distintos: una misión puede (V1.2) tener varias trazas."""
    trace_id = uuid.uuid4().hex
    # [V1.1 LC1, doc 41 §6] El origen se decide AQUÍ, en el único punto por el
    # que pasan todas las misiones, y se guarda con la traza: la marca de prueba
    # la pone el entorno que lanza el trabajo, y de madrugada —cuando el juez
    # mira— ese entorno ya no existe. Nunca rompe: sin marca, `user`.
    try:
        from app.core import corpus

        origen = corpus.current_origin(mission.source)
    except Exception:
        origen = "user"
    db = SessionLocal()
    try:
        db.add(OrchestratorTrace(
            id=trace_id,
            mission_id=mission.id,
            channel=channel or mission.channel,
            state="running",
            # [LC1] Enlace con la conversación (para "el después") y de dónde
            # viene la misión. Los dos son datos de OBSERVACIÓN: el TIE no los
            # lee para decidir nada.
            session_id=mission.session_id,
            origin=origen,
            # [R2] Jerarquía: a qué orquestación pertenece y de qué misión nació.
            # El TIE no los usa para nada — los guarda para que la UI y el
            # Learner puedan reconstruir el árbol de un mensaje multi-objetivo.
            run_id=mission.run_id,
            parent_trace_id=mission.parent_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))
        db.commit()
    except Exception as e:
        logger.error(f"[tracer] record_start falló (no crítico): {type(e).__name__}: {e}")
        db.rollback()
    finally:
        db.close()
    # [2026-07-21, doc 31] Telemetría punta a punta: el tracer es el punto ÚNICO
    # por el que pasan TODAS las rutas (handle, handle_stream, submit_mission,
    # acción directa) — aquí se fija el contexto de misión (contextvar) que
    # heredan los hooks del MEL y del toolloop, y se registra el arranque.
    try:
        import app.telemetry as _telemetry

        _telemetry.set_mission(mission.id, trace_id)
        _telemetry.record("mission_start", name=mission.source,
                          detail={"channel": channel or mission.channel})
    except Exception:
        pass
    return trace_id


def record_intent(trace_id: str, intent: Intent, *, model_used: Optional[str] = None) -> None:
    """Guarda la intención clasificada (qué quería el usuario + qué necesita)."""
    _update(trace_id, intent=intent.to_dict(), model_used=model_used)
    try:
        import app.telemetry as _telemetry

        _telemetry.record("intent", name=intent.type, trace_id=trace_id, ok=True,
                          detail={"short_path": intent.is_short_path,
                                  "direct_action": getattr(intent, "is_direct_action", False),
                                  "requires_tools": intent.requires_tools,
                                  "requires_planning": intent.requires_planning})
    except Exception:
        pass


def record_plan(trace_id: str, graph: TaskGraph, *, decision_id: Optional[str] = None,
                context_query_id: Optional[str] = None) -> None:
    """T2: guarda el TaskGraph y enlaza la decisión/contexto. En T3 el checkpoint
    por transición reescribe `plan` en cada cambio de estado de nodo."""
    _update(trace_id, plan=graph.to_dict(), decision_id=decision_id,
            context_query_id=context_query_id, state="running")
    try:
        import app.telemetry as _telemetry

        _telemetry.record("plan", trace_id=trace_id, ok=True,
                          detail={"nodes": len(graph.nodes),
                                  "sensitive": sum(1 for n in graph.nodes.values()
                                                   if getattr(n, "approval_required", False))})
    except Exception:
        pass


def update_graph(trace_id: str, graph: TaskGraph) -> None:
    """T3: checkpoint — reescribe el grafo serializado. Un UPDATE por transición."""
    _update(trace_id, plan=graph.to_dict())


def record_end(trace_id: str, *, outcome: str, state: str = "done",
               result: Optional[str] = None) -> None:
    """Cierra la traza con el resultado. `state` ∈ done|failed|cancelled."""
    _update(trace_id, outcome=outcome, result=result, state=state)
    try:
        import app.telemetry as _telemetry

        # Duración total real: desde created_at de la traza hasta ahora.
        duration_ms = None
        try:
            meta = get_meta(trace_id)
            created = meta.get("created_at") if meta else None
            if created:
                from datetime import datetime as _dt
                start = _dt.fromisoformat(created) if isinstance(created, str) else created
                duration_ms = int((_dt.utcnow() - start).total_seconds() * 1000)
        except Exception:
            pass
        _telemetry.record("mission_end", name=state, trace_id=trace_id,
                          ok=(state == "done"), duration_ms=duration_ms)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Eventos mission.* (doc 17 §4, T4) — METADATOS, nunca contenido
# ---------------------------------------------------------------------------
# Consumidores: el Learner (V1.1, Mission Learning — doc 15 §4), la telemetría
# de V2.0+ (`subscribe("*")`) y el Hub. Best-effort: `emit` es no bloqueante y
# aísla a sus handlers (doc 17); un consumidor roto jamás afecta a la misión.
def emit_started(mission: Mission) -> None:
    _emit("mission.started", {"mission_id": mission.id, "source": mission.source,
                              "channel": mission.channel})


def emit_completed(mission: Mission, *, ok: bool, nodes: int) -> None:
    _emit("mission.completed", {"mission_id": mission.id, "ok": ok, "nodes": nodes,
                                "spent_tokens": mission.spent_tokens})


def emit_failed(mission: Mission) -> None:
    _emit("mission.failed", {"mission_id": mission.id, "partial": bool(mission.outcome)})


def emit_cancelled(mission: Mission) -> None:
    _emit("mission.cancelled", {"mission_id": mission.id})


def _emit(name: str, payload: dict) -> None:
    try:
        from app.core.events import emit

        emit(name, source="tie", payload=payload)
    except Exception as e:  # un bus roto no rompe una misión
        logger.error(f"[tracer] emit({name}) falló (no crítico): {type(e).__name__}: {e}")


def set_state(trace_id: str, state: str) -> None:
    """Cambia el estado de la traza (running|waiting|done|failed|cancelled). Lo
    usa el executor al pausar en un gate (waiting) o al cancelar."""
    _update(trace_id, state=state)


def load_graph(trace_id: str) -> Optional[TaskGraph]:
    """Recupera el TaskGraph persistido de una traza (T3: reanudación tras gate
    o tras reinicio). None si no hay traza o aún no tiene plan."""
    db = SessionLocal()
    try:
        row = db.get(OrchestratorTrace, trace_id)
        if row is None or not row.plan:
            return None
        return TaskGraph.from_dict(row.plan)
    except Exception as e:
        logger.error(f"[tracer] load_graph({trace_id}) falló: {type(e).__name__}: {e}")
        return None
    finally:
        db.close()


def mission_snapshot(any_id: str) -> Optional[dict]:
    """[V1.1 L2] Lo que el LEARNER necesita saber de una misión terminada, en
    una sola lectura y SIN que tenga que conocer el esquema de esta tabla.

    Por qué existe este accesor en vez de que el Learner consulte
    `orchestrator_traces` por su cuenta: el Learner es un OBSERVADOR (doc 15).
    Que lea directamente el SQL del TIE lo acoplaría a un esquema ajeno —
    cualquier columna que cambiara aquí rompería el aprendizaje en silencio.
    Con este accesor, el TIE controla su superficie de lectura y el contrato es
    explícito. Es SOLO lectura: no muta nada, no planifica, no ejecuta.

    Devuelve datos ya destilados (nada de objetos vivos): el goal real que pidió
    el usuario, el camino que tomó, y por nodo lo que de verdad importa para
    aprender — si salió bien, qué tools llamó y con qué error falló."""
    trace_id = resolve_trace_id(any_id)
    if not trace_id:
        return None
    db = SessionLocal()
    try:
        row = db.get(OrchestratorTrace, trace_id)
        if row is None:
            return None
        intent = dict(row.intent or {})
        nodos: list[dict] = []
        if row.plan:
            try:
                # `TaskGraph.nodes` es un DICT {id: TaskNode}: iterarlo a secas
                # recorre las CLAVES (strings). Sin `.values()` esto lanzaba
                # `AttributeError` en el primer `n.id`, lo tragaba el `except` de
                # abajo y el snapshot salía SIEMPRE con `nodes: []` — dejando sin
                # herramientas al aprendizaje de L2, que por eso no proponía
                # jamás una skill a partir de una misión real. Lo encontró el
                # test de punta a punta; los unitarios no podían, porque
                # construían el snapshot a mano en vez de pasar por aquí.
                for n in TaskGraph.from_dict(row.plan).nodes.values():
                    nodos.append({
                        "id": n.id,
                        "goal": n.goal,
                        "state": n.state.value if hasattr(n.state, "value") else str(n.state),
                        "tools": list(n.tools or []),
                        "tool_calls": [
                            {"tool": c.get("tool"), "action": c.get("action"),
                             "ok": c.get("ok"),
                             # [LC1] La ruta del entregable, cuando la acción
                             # escribió algo (Sesión B). Es la prueba dura de
                             # "si dije que lo escribí, lo escribí": sin ella el
                             # juez solo tendría la palabra del propio modelo.
                             "target": c.get("target")}
                            for c in (n.tool_calls or []) if isinstance(c, dict)
                        ],
                        # [LC1] Lo que el nodo PRODUJO y lo que declaró no poder
                        # hacer (S11). Recortado: el juez necesita reconocer una
                        # rendición o un aviso de incompletitud, no releer el
                        # documento entero.
                        "output": (str(n.result.get("output") or "")[:1200]
                                   if isinstance(n.result, dict) else ""),
                        "limitations": (
                            [str(x)[:200] for x in (n.result.get("limitations") or [])]
                            if isinstance(n.result, dict) else []
                        ),
                        "error": n.error,
                    })
            except Exception as e:      # un plan corrupto no impide aprender del resto
                logger.info(f"[tracer] mission_snapshot: plan ilegible ({e!r})")
        return {
            "trace_id": row.id,
            "mission_id": row.mission_id,
            "channel": row.channel,
            "state": row.state,
            # `raw_text` es el texto ORIGINAL del usuario (C-1, doc 25): lo que
            # de verdad pidió, no el goal reescrito por el clasificador.
            "goal": (intent.get("raw_text") or intent.get("goal") or "").strip(),
            "intent_type": intent.get("type"),
            "requires_tools": list(intent.get("requires_tools") or []),
            "outcome": row.outcome or "",
            "nodes": nodos,
            # [L3] El proyecto de la misión, si venía acotada por autoridad (R4).
            # Lo consume el análisis inter-proyecto del Learner.
            "project_id": (row.plan.get("authority") or {}).get("project_id")
            if isinstance(row.plan, dict) and isinstance(row.plan.get("authority"), dict)
            else None,
            # [LC1] Lo que el juez necesita para situar la misión: de dónde vino
            # (¿trabajo real o corpus de pruebas?) y en qué conversación, para
            # poder leer lo que el usuario dijo después.
            "origin": getattr(row, "origin", None) or "user",
            "session_id": getattr(row, "session_id", None),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
    except Exception as e:
        logger.error(f"[tracer] mission_snapshot({any_id}) falló: {type(e).__name__}: {e}")
        return None
    finally:
        db.close()


def recent_missions(days: int = 30, limit: int = 200,
                    state: Optional[str] = "done") -> list[dict]:
    """[V1.1 L3] Las misiones recientes, destiladas — la materia prima del
    análisis en BATCH del Learner (LLL análisis 1 y 3, doc 09 §2.2).

    Hermana de `mission_snapshot`, y por el mismo motivo: el Learner no debe
    conocer el esquema de `orchestrator_traces`. La diferencia es el volumen —
    analizar 30 días misión a misión serían cientos de consultas; esto lo
    resuelve en UNA y destila en Python.

    Solo lo que el análisis necesita: el goal REAL, las tools que de verdad se
    ejecutaron con éxito (el procedimiento observado, no el planeado) y el
    proyecto al que pertenecía la misión. `state=None` trae todas."""
    desde = datetime.utcnow() - timedelta(days=max(days, 1))
    db = SessionLocal()
    try:
        q = db.query(OrchestratorTrace).filter(OrchestratorTrace.created_at >= desde)
        if state:
            q = q.filter(OrchestratorTrace.state == state)
        filas = q.order_by(OrchestratorTrace.created_at.desc()).limit(limit).all()
    except Exception as e:
        logger.error(f"[tracer] recent_missions falló: {type(e).__name__}: {e}")
        return []
    finally:
        db.close()

    out: list[dict] = []
    for row in filas:
        intent = dict(row.intent or {})
        plan = row.plan if isinstance(row.plan, dict) else {}
        tools: set = set()
        nodos = 0
        for n in (plan.get("nodes") or {}).values() if isinstance(plan.get("nodes"), dict) \
                else (plan.get("nodes") or []):
            if not isinstance(n, dict):
                continue
            nodos += 1
            for c in (n.get("tool_calls") or []):
                if isinstance(c, dict) and c.get("ok") and c.get("tool"):
                    tools.add(str(c["tool"]))
        out.append({
            "trace_id": row.id,
            "mission_id": row.mission_id,
            "state": row.state,
            "goal": (intent.get("raw_text") or intent.get("goal") or "").strip(),
            "tools": sorted(tools),
            "nodes": nodos,
            # La frontera de autoridad viaja dentro del plan persistido (R4). Si
            # la misión no venía de un agente/proyecto, es None — y entonces el
            # análisis inter-proyecto simplemente no tiene nada que decir de
            # ella, que es la respuesta honesta.
            "project_id": (plan.get("authority") or {}).get("project_id")
            if isinstance(plan.get("authority"), dict) else None,
            # [LC1] De dónde vino, para que el Learner pueda descartar el corpus
            # de pruebas sin conocer el esquema de esta tabla.
            "origin": getattr(row, "origin", None) or "user",
            "session_id": getattr(row, "session_id", None),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        })
    return out


def trace_id_for_mission(mission_id: str) -> Optional[str]:
    """La traza de una misión. [R4] Lo necesita `agent_manager` para recuperar el
    rastro de herramientas de la misión que acaba de delegar: `submit_mission`
    devuelve la Mission, no el trace_id. En V1.0 la relación es 1:1 (doc 14
    §3.6); si en V1.2 una misión llega a tener varias trazas, aquí habrá que
    decidir cuál — por eso se coge la más reciente y no `.first()` a ciegas."""
    db = SessionLocal()
    try:
        row = (db.query(OrchestratorTrace)
                 .filter(OrchestratorTrace.mission_id == mission_id)
                 .order_by(OrchestratorTrace.created_at.desc())
                 .first())
        return row.id if row else None
    except Exception as e:
        logger.error(f"[tracer] trace_id_for_mission({mission_id}) falló: {type(e).__name__}: {e}")
        return None
    finally:
        db.close()


def resolve_trace_id(any_id: str) -> Optional[str]:
    """[S7·S8] Resuelve un identificador de misión sea cual sea su FORMA: el
    `trace_id` real (PK de `orchestrator_traces`, lo que usan internamente los
    endpoints) o el `mission_id` (lo que anuncia el chat/lo que trae una misión
    nacida de `submit_mission`). Antes `GET /api/tie/missions/{id}` solo
    aceptaba el primero — el chat podía anunciar un id que el endpoint
    rechazaba con 404 (el mismatch real que motivó S8, distinto al de NEW-3).

    PK primero (ruta más barata); si no hay fila, cae a buscar por
    `mission_id` — la más reciente, mismo criterio que
    `trace_id_for_mission`. Devuelve el trace_id real, o None si ninguno de
    los dos encaja."""
    db = SessionLocal()
    try:
        row = db.get(OrchestratorTrace, any_id)
        if row is not None:
            return row.id
        row = (db.query(OrchestratorTrace)
                 .filter(OrchestratorTrace.mission_id == any_id)
                 .order_by(OrchestratorTrace.created_at.desc())
                 .first())
        return row.id if row else None
    except Exception as e:
        logger.error(f"[tracer] resolve_trace_id({any_id}) falló: {type(e).__name__}: {e}")
        return None
    finally:
        db.close()


def get_meta(trace_id: str) -> Optional[dict]:
    """Metadatos de la traza (mission_id, channel, state) — el executor los
    necesita al reanudar (la Mission de V1.0 es implícita: vive aquí)."""
    db = SessionLocal()
    try:
        row = db.get(OrchestratorTrace, trace_id)
        if row is None:
            return None
        return {"id": row.id, "mission_id": row.mission_id, "channel": row.channel,
                "state": row.state,
                # [2026-07-21] para que la telemetría calcule la duración total
                "created_at": row.created_at.isoformat() if row.created_at else None}
    finally:
        db.close()


def get_outcome(trace_id: str) -> Optional[str]:
    """El texto de resultado ya escrito por `record_end`. [A·VOZ-4] Lo necesita
    el reporte async de las misiones en segundo plano: el evento `mission.*` solo
    trae metadatos (nunca contenido, doc 17), así que el texto se lee de la traza."""
    db = SessionLocal()
    try:
        row = db.get(OrchestratorTrace, trace_id)
        return row.outcome if row else None
    except Exception as e:
        logger.error(f"[tracer] get_outcome({trace_id}) falló: {type(e).__name__}: {e}")
        return None
    finally:
        db.close()


def pending_trace_ids() -> list[str]:
    """Trazas sin terminar (running|waiting) — las que `resume_pending()` del
    executor recarga al arrancar el backend (doc 14 §3.4.3)."""
    db = SessionLocal()
    try:
        rows = (
            db.query(OrchestratorTrace)
            .filter(OrchestratorTrace.state.in_(["running", "waiting"]))
            .all()
        )
        return [r.id for r in rows]
    except Exception as e:
        logger.error(f"[tracer] pending_trace_ids falló: {type(e).__name__}: {e}")
        return []
    finally:
        db.close()


# Estados terminales — una misión aquí ya no cambia. Solo estos se pueden
# borrar (a mano o por la limpieza automática): una misión running/waiting
# NUNCA se borra por debajo de su ejecución, sin importar antigüedad.
_TERMINAL_STATES = ("done", "failed", "cancelled")


def delete_trace(trace_id: str) -> tuple[bool, str]:
    """Borra una misión terminada (botón "×" del usuario, doc: `DELETE
    /api/tie/missions/{id}`). `(ok, motivo)`: motivo ∈ "ok"|"not_found"|"live"
    |"error" — el endpoint traduce "live" a 409 (pide cancelar primero)."""
    db = SessionLocal()
    try:
        row = db.get(OrchestratorTrace, trace_id)
        if row is None:
            return False, "not_found"
        if row.state not in _TERMINAL_STATES:
            return False, "live"
        db.delete(row)
        db.commit()
        return True, "ok"
    except Exception as e:
        logger.error(f"[tracer] delete_trace({trace_id}) falló: {type(e).__name__}: {e}")
        db.rollback()
        return False, "error"
    finally:
        db.close()


def purge_old(retention_days: int) -> int:
    """Limpieza automática (job nocturno, mismo espíritu que `lifecycle.py`
    del MOS — RFC-007 — pero para el estado operativo del TIE, no la memoria):
    borra misiones TERMINADAS cuya última actualización es más vieja que
    `retention_days`. Una misión `running`/`waiting` NUNCA se toca, por vieja
    que sea — solo lo que ya terminó y perdió valor operativo. Devuelve
    cuántas se borraron. Best-effort: un fallo aquí no debe tumbar el job."""
    if retention_days <= 0:
        return 0
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    db = SessionLocal()
    try:
        n = (
            db.query(OrchestratorTrace)
            .filter(OrchestratorTrace.state.in_(_TERMINAL_STATES))
            .filter(OrchestratorTrace.updated_at < cutoff)
            .delete(synchronize_session=False)
        )
        db.commit()
        if n:
            logger.info(f"[tracer] purge_old: {n} misión(es) terminada(s) de más de {retention_days}d borradas")
        return n
    except Exception as e:
        logger.error(f"[tracer] purge_old falló (no crítico): {type(e).__name__}: {e}")
        db.rollback()
        return 0
    finally:
        db.close()


def _update(trace_id: str, **fields) -> None:
    db = SessionLocal()
    try:
        row = db.get(OrchestratorTrace, trace_id)
        if row is None:
            return
        for k, v in fields.items():
            if v is not None:
                setattr(row, k, v)
        row.updated_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        logger.error(f"[tracer] update({trace_id}) falló (no crítico): {type(e).__name__}: {e}")
        db.rollback()
    finally:
        db.close()
