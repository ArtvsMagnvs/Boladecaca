# backend/app/learner/signals.py — EL PAQUETE DE SEÑALES DURAS (V1.1 LC1)
#
# doc 41 §3.2. Lo que el juez ve antes de dictaminar. Es la mitad MECÁNICA del
# Learner Cognitivo (doc 41 §1): aquí no se juzga nada — se EXTRAE lo que ya
# quedó registrado en otras capas y se pone junto, en un formato que un modelo
# pueda leer.
#
# Por qué importa que sea mecánico: la evidencia tiene que ser INDEPENDIENTE de
# quien la interpreta. Si el mismo LLM que decide "sirvió" fuera también quien
# decide "qué evidencia hay", volveríamos al bucle de autoevaluación que causó
# el desastre (doc 41 §0: `execution_ok` era evidencia autogenerada).
#
# TODAS las señales vienen de sesiones anteriores que ya las registran:
#   1. Entregables verificados ....... Sesión B (`toolloop` anota `target`)
#   2. Rendición ..................... NEW-4 (`grounding.is_surrender`)
#   3. PlanRejection ................. S2/B-1 (el planner declara que no puede)
#   4. Atasco y fallos repetidos ..... Sesión A (`stalled`) y S9c
#   5. Atribución de fallos .......... L2b (`core/failures`, timeline)
#   6. Limitaciones declaradas ....... S11 (`limitations`)
#   7. EL DESPUÉS .................... LC1 (session_id de R6.5b) ← la nueva
#   8. Origen ........................ LC1 (`core/corpus`)
#
# La 7 es la que nadie miraba y la que explica el caso Melendi: ocho peticiones
# casi idénticas seguidas no son una costumbre, son ocho intentos porque ninguno
# funcionó. Ojo con el matiz: eso es un INSUMO para el juez, NO una regla. Aquí
# se mide y se cuenta; interpretarlo es su trabajo.
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Recortes: el paquete viaja dentro de un prompt. Generosos con lo que decide
# (el goal, la respuesta final) y cortos con lo repetitivo.
_MAX_GOAL = 600
_MAX_OUTCOME = 2000
_MAX_AFTER_MSGS = 3
_MAX_AFTER_CHARS = 400
_AFTER_WINDOW_MIN = 90          # cuánto se mira hacia adelante en la conversación
_SAME_WORK_WINDOW_H = 24        # ventana para "¿me lo volvieron a pedir?"


# ---------------------------------------------------------------------------
# 1 · Entregables
# ---------------------------------------------------------------------------
def _deliverables(snap: dict) -> dict:
    """Qué archivos AFIRMA la respuesta haber creado, cuáles se escribieron de
    verdad y cuáles existen ahora en disco.

    Reusa exactamente la maquinaria de la Sesión B: `claimed_written_files` para
    lo afirmado y el `target` que el toolloop anota SOLO en escrituras con
    éxito. Aquí no se decide si eso está bien o mal — se cuenta."""
    from app.core.grounding import claimed_written_files

    afirmados = claimed_written_files(snap.get("outcome") or "")
    escritos: list[str] = []
    for n in snap.get("nodes") or []:
        for c in (n.get("tool_calls") or []):
            if not isinstance(c, dict):
                continue
            objetivo = c.get("target")
            if objetivo and c.get("ok"):
                escritos.append(str(objetivo))

    existen: list[str] = []
    faltan: list[str] = []
    for ruta in escritos:
        try:
            (existen if os.path.isfile(ruta) else faltan).append(ruta)
        except Exception:
            pass                     # un error de disco no acusa a nadie
    return {
        "claimed": afirmados,
        "written": escritos,
        "on_disk": existen,
        "missing_on_disk": faltan,
        # Lo AFIRMADO sin ninguna escritura detrás. La comprobación fina la hace
        # el responder (Sesión B); aquí solo se le pone delante al juez.
        "claimed_without_write": [
            f for f in afirmados
            if not any(f.lower() in w.lower().replace("\\", "/") for w in escritos)
        ],
    }


# ---------------------------------------------------------------------------
# 2-3 · Rendición y rechazo del plan
# ---------------------------------------------------------------------------
_RECHAZO = re.compile(
    r"\bno (puedo|es posible) (hacer|completar|realizar)|"
    r"\bplan_?rejection\b|\bcannot\b.*\bcomplete\b", re.I)


def _honesty(snap: dict) -> dict:
    from app.core.grounding import is_surrender

    salida = snap.get("outcome") or ""
    nodos_rendidos = [
        n.get("id") for n in (snap.get("nodes") or [])
        if is_surrender(str(n.get("output") or ""))
    ]
    return {
        "final_is_surrender": bool(is_surrender(salida)),
        "surrendered_nodes": [x for x in nodos_rendidos if x],
        # Una misión sin ningún nodo es, casi siempre, un plan rechazado: el
        # planner declaró que no podía y no llegó a construirse grafo.
        "plan_rejected": (not (snap.get("nodes") or []))
                         and bool(_RECHAZO.search(salida)),
    }


# ---------------------------------------------------------------------------
# 4-5-6 · Lo que dice la telemetría: atascos, fallos atribuidos, limitaciones
# ---------------------------------------------------------------------------
_EVENTOS_PROBLEMA = ("stalled", "repeated_failure", "repeated_denial",
                     "preflight_not_ready", "tool_denied", "user_question")


def _from_timeline(mission_id: str) -> dict:
    """Lee la telemetría YA registrada de la misión. Nunca lanza: sin
    telemetría el juez trabaja con menos señales, que es peor que tenerlas pero
    infinitamente mejor que no juzgar."""
    vacio = {"llm_calls": 0, "path": "desconocido", "within_budget": True,
             "tools": {}, "problems": [], "failures": [], "duration_ms": 0}
    try:
        import app.telemetry as telemetry

        tl = telemetry.mission_timeline(mission_id)
    except Exception as e:
        logger.info(f"[learner/signals] sin telemetría de {mission_id}: {e!r}")
        return vacio

    resumen = tl.get("summary") or {}
    problemas: list[dict] = []
    for ev in (tl.get("events") or []):
        nombre = str(ev.get("name") or "")
        if nombre in _EVENTOS_PROBLEMA or ev.get("ok") is False:
            detalle = ev.get("detail") if isinstance(ev.get("detail"), dict) else {}
            problemas.append({
                "stage": ev.get("stage"), "name": nombre,
                "reason": (detalle.get("error") or detalle.get("reason")
                           or detalle.get("notes") or "")[:200],
                "failure_kind": detalle.get("failure_kind"),
                "blame": detalle.get("blame"),
            })

    # Atribución L2b agregada: de quién fue la culpa de lo que falló.
    culpas: list[dict] = []
    try:
        from app.learner.stats import failures_in

        culpas = failures_in(tl)
    except Exception:
        culpas = []

    return {
        "llm_calls": resumen.get("llm_calls", 0),
        "path": resumen.get("path", "desconocido"),
        "within_budget": resumen.get("within_budget", True),
        "tools": resumen.get("tools", {}),
        "problems": problemas[:12],
        "failures": culpas[:8],
        "duration_ms": resumen.get("total_ms", 0),
    }


def _limitations(snap: dict) -> list[str]:
    """Lo que Aithera declaró que NO pudo hacer (S11). Una misión que avisa de
    su propia incompletitud rara vez es un `served` limpio — pero eso lo decide
    el juez, no esta función."""
    out: list[str] = []
    for n in snap.get("nodes") or []:
        for lim in (n.get("limitations") or []):
            if isinstance(lim, str) and lim.strip():
                out.append(lim.strip()[:200])
    return out[:8]


# ---------------------------------------------------------------------------
# 7 · EL DESPUÉS — la señal que nadie miraba
# ---------------------------------------------------------------------------
def aftermath(session_id: Optional[str], since: Optional[datetime],
              *, goal: str = "") -> dict:
    """Qué pasó DESPUÉS de que Aithera respondiera.

    Dos cosas, las dos puramente descriptivas:
      - `next_messages`: los siguientes mensajes del usuario en la MISMA
        conversación (por eso hacía falta el `session_id` en la traza).
      - `repeats`: cuántas veces se volvió a pedir un trabajo parecido en las
        horas siguientes, y a los cuántos minutos la primera vez.

    NO hay ningún umbral aquí que decida nada. "Se repitió a los 3 minutos" es
    un dato que el juez lee igual que lo leería una persona: junto al texto de
    lo que el usuario dijo, que es lo que le da sentido ("otra vez, pero sin
    buscar en internet" significa una cosa; "gracias, ahora el resumen"
    significa la contraria)."""
    fuera = {"available": False, "next_messages": [], "repeats": 0,
             "minutes_to_repeat": None}
    if not session_id or since is None:
        return fuera

    try:
        from app.db.database import ChatMessage, SessionLocal
    except Exception:
        return fuera

    hasta = since + timedelta(minutes=_AFTER_WINDOW_MIN)
    db = SessionLocal()
    try:
        filas = (db.query(ChatMessage)
                 .filter(ChatMessage.session_id == session_id,
                         ChatMessage.role == "user",
                         ChatMessage.created_at > since,
                         ChatMessage.created_at <= hasta)
                 .order_by(ChatMessage.id).limit(20).all())
        siguientes = [{
            "text": (f.content or "")[:_MAX_AFTER_CHARS],
            "minutes_after": _minutos(since, f.created_at),
        } for f in filas[:_MAX_AFTER_MSGS]]

        # ¿Se volvió a pedir LO MISMO? Reusa la comparación de L2 (Jaccard
        # sobre palabras de contenido, mismo umbral) para que "parecido"
        # signifique exactamente lo mismo en todo el Learner.
        #
        # Se usa `similarity` y no `same_work` a propósito: `same_work` exige
        # además que coincidan las HERRAMIENTAS, y un mensaje suelto del chat no
        # tiene ninguna — pasarle una lista vacía haría que solo casara con
        # misiones sin tools, que es justo lo contrario de lo que hace falta.
        repeticiones, primer_min = 0, None
        if goal:
            from app.learner.mission_learning import (
                SIMILARITY_THRESHOLD, content_words, similarity,
            )

            palabras_goal = content_words(goal)
            tope = since + timedelta(hours=_SAME_WORK_WINDOW_H)
            candidatas = (db.query(ChatMessage)
                          .filter(ChatMessage.session_id == session_id,
                                  ChatMessage.role == "user",
                                  ChatMessage.created_at > since,
                                  ChatMessage.created_at <= tope)
                          .order_by(ChatMessage.id).limit(60).all())
            for f in candidatas:
                parecido = similarity(palabras_goal, content_words(f.content or ""))
                if parecido >= SIMILARITY_THRESHOLD:
                    repeticiones += 1
                    if primer_min is None:
                        primer_min = _minutos(since, f.created_at)
    except Exception as e:
        logger.info(f"[learner/signals] aftermath falló: {e!r}")
        return fuera
    finally:
        try:
            db.close()
        except Exception:
            pass

    return {"available": True, "next_messages": siguientes,
            "repeats": repeticiones, "minutes_to_repeat": primer_min}


def _minutos(desde: datetime, hasta: Optional[datetime]) -> Optional[int]:
    if hasta is None:
        return None
    try:
        return max(0, int((hasta - desde).total_seconds() // 60))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# El paquete completo
# ---------------------------------------------------------------------------
def collect(mission_id: str, snap: Optional[dict] = None) -> Optional[dict]:
    """El paquete de señales de UNA misión, listo para el juez.

    Devuelve None si la misión no existe. Nunca lanza: si una señal concreta no
    se puede leer, se omite esa señal — el juez lo verá y podrá decir `unclear`,
    que es la respuesta honesta cuando falta información."""
    from app.tie import tracer

    if snap is None:
        snap = tracer.mission_snapshot(mission_id)
    if not snap:
        return None

    from app.core import corpus

    goal = (snap.get("goal") or "")[:_MAX_GOAL]
    creada = _fecha(snap.get("created_at"))
    origen = corpus.origin_of(snap.get("origin"), goal=goal)

    nodos = []
    for n in (snap.get("nodes") or [])[:12]:
        nodos.append({
            "id": n.get("id"),
            "goal": (n.get("goal") or "")[:200],
            "state": n.get("state"),
            "tools_used": sorted({str(c.get("tool")) for c in (n.get("tool_calls") or [])
                                  if isinstance(c, dict) and c.get("tool")}),
            "tool_failures": sum(1 for c in (n.get("tool_calls") or [])
                                 if isinstance(c, dict) and c.get("ok") is False),
            "error": (n.get("error") or "")[:200] or None,
        })

    return {
        "mission_id": snap.get("mission_id") or mission_id,
        "trace_id": snap.get("trace_id"),
        "origin": origen,
        "goal": goal,
        "state": snap.get("state"),
        "outcome": (snap.get("outcome") or "")[:_MAX_OUTCOME],
        "project_id": snap.get("project_id"),
        "nodes": nodos,
        "deliverables": _deliverables(snap),
        "honesty": _honesty(snap),
        "execution": _from_timeline(snap.get("mission_id") or mission_id),
        "limitations": _limitations(snap),
        "aftermath": aftermath(snap.get("session_id"), creada, goal=goal),
    }


def _fecha(iso: Optional[str]) -> Optional[datetime]:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(str(iso))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Índice de señales citables — lo usa el grounding del juez (§3.5)
# ---------------------------------------------------------------------------
def citable_ids(paquete: dict) -> set:
    """Los identificadores de señal que el juez PUEDE citar, derivados del
    paquete que se le dio. Es lo que permite comprobar, sin otro LLM, que un
    veredicto se apoya en algo que existe de verdad (doc 41 §3.5)."""
    ids: set = set()
    if not isinstance(paquete, dict):
        return ids
    d = paquete.get("deliverables") or {}
    if d.get("on_disk"):
        ids.add("deliverable_on_disk")
    if d.get("missing_on_disk"):
        ids.add("deliverable_missing")
    if d.get("claimed_without_write"):
        ids.add("claimed_without_write")
    h = paquete.get("honesty") or {}
    if h.get("final_is_surrender"):
        ids.add("surrender")
    if h.get("surrendered_nodes"):
        ids.add("surrendered_node")
    if h.get("plan_rejected"):
        ids.add("plan_rejected")
    e = paquete.get("execution") or {}
    for p in (e.get("problems") or []):
        ids.add(f"problem:{p.get('name')}")
        ids.add("problem")
    if e.get("failures"):
        ids.add("failure_attributed")
    if e.get("within_budget") is False:
        ids.add("over_budget")
    if paquete.get("limitations"):
        ids.add("limitation")
    a = paquete.get("aftermath") or {}
    if a.get("next_messages"):
        ids.add("user_followup")
    if a.get("repeats"):
        ids.add("repeated_request")
    for n in (paquete.get("nodes") or []):
        if n.get("state"):
            ids.add(f"node_state:{n.get('state')}")
        if n.get("error"):
            ids.add("node_error")
    if paquete.get("state"):
        ids.add(f"mission_state:{paquete.get('state')}")
    if (paquete.get("outcome") or "").strip():
        ids.add("outcome_text")
    return ids
