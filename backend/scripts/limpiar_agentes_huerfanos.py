"""Agentes HUÉRFANOS (sin proyecto): listarlos y, si se pide, borrarlos.

[2026-08-02] Petición del usuario tras el caso "CordycepsDev": «elimina los
agentes huérfanos que existan, que solo queden los que están asignados a los
proyectos». Y con el orden que él mismo marcó: primero comprobar que ya NO se
crean nuevos, y solo después borrar los que quedaron.

Por eso el script NO borra por defecto. Dos pasadas:

    cd backend
    python scripts/limpiar_agentes_huerfanos.py            # solo mira
    python scripts/limpiar_agentes_huerfanos.py --borrar   # borra de verdad

Usa la MISMA base de datos que el backend (`DATABASE_URL` del entorno, con el
mismo fallback a SQLite): si el backend está apagado no pasa nada, esto habla
con la BD directamente. Borra a través de `agent_manager.delete_agent`, que ya
cancela las ejecuciones en curso del agente — nunca con un DELETE a pelo.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.agent_manager import agent_manager      # noqa: E402
from app.db.database import Agent, AgentExecution, SessionLocal   # noqa: E402


def _huerfanos() -> list[dict]:
    db = SessionLocal()
    try:
        filas = db.query(Agent).filter(Agent.project_id.is_(None)).order_by(Agent.id).all()
        out = []
        for a in filas:
            ejec = db.query(AgentExecution).filter(AgentExecution.agent_id == a.id).count()
            out.append({"id": a.id, "name": a.name, "role": a.role,
                        "is_active": a.is_active, "ejecuciones": ejec})
        return out
    finally:
        db.close()


def main() -> int:
    borrar = "--borrar" in sys.argv
    huerfanos = _huerfanos()

    if not huerfanos:
        print("No hay agentes huerfanos: todos pertenecen a un proyecto.")
        return 0

    print(f"{len(huerfanos)} agente(s) SIN proyecto:\n")
    for a in huerfanos:
        print(f"  id={a['id']:<5} {a['name'][:45]:<45} "
              f"role={a['role'] or '-':<13} activo={a['is_active']} "
              f"ejecuciones={a['ejecuciones']}")

    if not borrar:
        print("\n(No se ha borrado nada.) Para borrarlos:")
        print("    python scripts/limpiar_agentes_huerfanos.py --borrar")
        return 0

    print("\nBorrando...")
    borrados, fallos = 0, 0
    for a in huerfanos:
        try:
            if agent_manager.delete_agent(a["id"]):
                borrados += 1
                print(f"  borrado id={a['id']} ({a['name']})")
            else:
                fallos += 1
                print(f"  NO existia ya id={a['id']}")
        except Exception as e:      # noqa: BLE001 — informar, no reventar a medias
            fallos += 1
            print(f"  ERROR con id={a['id']}: {e!r}")

    restantes = _huerfanos()
    print(f"\nBorrados: {borrados}. Fallos: {fallos}. Huerfanos restantes: {len(restantes)}.")
    return 0 if not restantes else 1


if __name__ == "__main__":
    raise SystemExit(main())
