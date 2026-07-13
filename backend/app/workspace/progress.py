# app/workspace/progress.py — Progreso automatico (V0.87, doc 18 §8)
#
# FUNCION PURA, sin BD — por eso es trivialmente testeable. service.py hace las
# consultas y llama aqui con las listas de estados.
#
# Metodo ELEGIDO (doc 18 §8): conteo de tareas cerradas, NO ponderado por
# estimate. Las estimaciones de un solo usuario son ruidosas; ponderar por ellas
# da falsa precision (Regla de Oro: simplicidad > sofisticacion sin valor). El
# conteo es transparente ("3 de 5") y el usuario lo entiende sin explicacion.
#
# ratio en 0.0-1.0 (el frontend lo pinta como progress*100 — NO cambiar la escala).
from __future__ import annotations

from typing import Iterable

# Estados que cuentan como "hecho". Coincide EXACTAMENTE con el filtro real ya
# usado en gateway/adapters/telegram_adapter.py (status != done && != completed):
# el frontend escribe "completed", pero ambos existen en el historico.
DONE_STATUSES = frozenset({"done", "completed"})


def is_done(status: str | None) -> bool:
    return (status or "").strip().lower() in DONE_STATUSES


def compute_progress(statuses: Iterable[str | None]) -> dict:
    """Progreso de un conjunto de tareas a partir de sus estados.

    Devuelve {done, total, ratio}. ratio = done/total (0.0 si no hay tareas —
    un milestone vacio esta al 0%, no al 100%). Las checklists NO entran aqui
    (son intra-tarea; contarlas inflaria el porcentaje, doc 18 §8)."""
    total = 0
    done = 0
    for s in statuses:
        total += 1
        if is_done(s):
            done += 1
    ratio = (done / total) if total else 0.0
    return {"done": done, "total": total, "ratio": round(ratio, 4)}
