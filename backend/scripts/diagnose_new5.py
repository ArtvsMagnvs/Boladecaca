# scripts/diagnose_new5.py — NEW-5 (doc 34 §12.4): "las tools del agente no
# llegaron al nodo". El agente tenía `browser`+`search` habilitadas y el paso
# de "recolectar información" recibió solo `document`+`filesystem`.
#
# Doc 34 es explícito: "Hay que medirlo antes de tocar" — este script hace
# EXACTAMENTE esa medición, de forma read-only, contra la BD real. Compara,
# para cada misión reciente:
#   (1) `authority.allowed_tools` — lo que el agente TENÍA PERMITIDO (persistido
#       en el propio grafo, `orchestrator_traces.plan.authority`, R4)
#   (2) `node.tools` — lo que el PLANNER ASIGNÓ a cada paso
#   (3) `node.tool_calls` — lo que el paso REALMENTE LLAMÓ durante la ejecución
#
# Si (1) incluye browser/search pero (2) no los lista en el nodo relevante →
# el planner no se los dio (hipótesis "a": calidad de planificación, no bug de
# seguridad). Si (2) SÍ los lista pero (3) nunca los llama → el paso las tuvo
# disponibles y decidió no usarlas (hipótesis "c", no contemplada en el doc
# original). Si (1) los tiene pero (2) tampoco los tiene NUNCA en ninguna
# misión de ningún agente con esas tools → mirar si `Authority.check()`
# (app/tie/authority.py) está denegando algo en el log del backend real.
#
# Uso (no hace falta que el backend esté corriendo — lee la BD directamente,
# mismo patrón que mission_report.py):
#   cd backend
#   python scripts/diagnose_new5.py                 # últimas 15 misiones con plan
#   python scripts/diagnose_new5.py --limit 40       # más misiones hacia atrás
#   python scripts/diagnose_new5.py --agent "Nombre" # agentes con browser/search
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_WATCH_TOOLS = {"browser", "search"}


def _short(text: str, n: int = 70) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def list_agents_con_web(name_filter: str | None = None) -> None:
    """Agentes que tienen browser/search en su whitelist — para saber qué
    agente(s) buscar en las trazas de abajo."""
    from app.db.database import Agent, SessionLocal

    db = SessionLocal()
    try:
        q = db.query(Agent)
        if name_filter:
            q = q.filter(Agent.name.ilike(f"%{name_filter}%"))
        agentes = q.all()
    finally:
        db.close()

    print("\n═══ Agentes con 'browser' y/o 'search' habilitadas ═══")
    encontrado = False
    for a in agentes:
        try:
            tools = json.loads(a.allowed_tools or "[]")
        except (ValueError, TypeError):
            tools = []
        if _WATCH_TOOLS & set(tools):
            encontrado = True
            print(f"  · agente #{a.id} {a.name!r} (proyecto={a.project_id}) "
                  f"— allowed_tools={tools}")
    if not encontrado:
        print("  (ninguno — si el agente que probaste no aparece aquí, revisa su "
              "config en Ajustes → Agentes: puede que browser/search se hayan "
              "desmarcado después de la prueba)")


def list_trazas(limit: int) -> None:
    """Últimas `limit` misiones con plan persistido: por cada nodo, compara
    authority.allowed_tools vs node.tools vs node.tool_calls REALES."""
    from app.db.database import OrchestratorTrace, SessionLocal

    db = SessionLocal()
    try:
        rows = (
            db.query(OrchestratorTrace)
            .filter(OrchestratorTrace.plan.isnot(None))
            .order_by(OrchestratorTrace.created_at.desc())
            .limit(limit)
            .all()
        )
        # Cargar todo lo necesario ANTES de cerrar la sesión.
        data = [
            {
                "trace_id": r.id,
                "mission_id": r.mission_id,
                "created_at": r.created_at,
                "state": r.state,
                "plan": r.plan,
                "intent": r.intent,
            }
            for r in rows
        ]
    finally:
        db.close()

    if not data:
        print("\nNo hay ninguna misión con plan persistido en esta BD.")
        return

    print(f"\n═══ Últimas {len(data)} misiones con plan (más reciente primero) ═══")
    for d in data:
        plan = d["plan"] or {}
        authority = plan.get("authority") or {}
        allowed = authority.get("allowed_tools")
        nodes = plan.get("nodes") or {}
        goal = (d["intent"] or {}).get("goal") or (d["intent"] or {}).get("raw_text") or ""

        # ¿Esta misión tiene ALGÚN interés para NEW-5? Solo la mostramos entera
        # si el agente tenía browser/search permitidas (allowed es None =
        # "sin restricción", eso también interesa: catálogo completo).
        interesa = allowed is None or bool(_WATCH_TOOLS & set(allowed or []))
        if not interesa:
            continue

        print(f"\n  ── misión {d['mission_id']}  (traza {d['trace_id'][:8]}…)  "
              f"{d['created_at']}  estado={d['state']}")
        print(f"     objetivo: {_short(goal, 90)}")
        print(f"     authority.allowed_tools = {allowed!r}  "
              f"(None = sin restricción, todo el catálogo)")
        if not nodes:
            print("     (sin nodos — probablemente degradó al camino corto)")
            continue

        for nid, n in nodes.items():
            planned = n.get("tools") or []
            calls = n.get("tool_calls") or []
            called_tools = sorted({c.get("tool_id") or c.get("tool") for c in calls if isinstance(c, dict)})
            marca = " ⚠ SIN browser/search asignadas" if allowed and (_WATCH_TOOLS & set(allowed)) and not (_WATCH_TOOLS & set(planned)) else ""
            print(f"       [{nid}] {_short(n.get('goal', ''), 60)}")
            print(f"             asignadas (planner) = {planned}{marca}")
            print(f"             llamadas  (real)    = {called_tools or '(ninguna)'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=15, help="cuántas misiones mirar hacia atrás")
    ap.add_argument("--agent", type=str, default=None, help="filtra agentes por nombre (substring)")
    args = ap.parse_args()

    list_agents_con_web(args.agent)
    list_trazas(args.limit)

    print("\n═══ Cómo leer esto ═══")
    print("  Busca la misión que corresponde a tu prueba real (por fecha/objetivo).")
    print("  Si 'authority.allowed_tools' SÍ incluye browser/search pero el nodo de")
    print("  'recolectar información' NO las tiene en 'asignadas (planner)' → el")
    print("  planificador no se las dio (no es un bug de seguridad, es un problema")
    print("  de calidad del plan).")
    print("  Si SÍ las tiene asignadas pero 'llamadas (real)' está vacío de ellas →")
    print("  el paso las tuvo disponibles y decidió no usarlas.")
    print("  Copia el bloque de esa misión (o el JSON completo si hace falta) y")
    print("  compártelo para decidir el fix exacto.\n")


if __name__ == "__main__":
    main()
