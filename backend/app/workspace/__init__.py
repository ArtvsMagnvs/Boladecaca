# backend/app/workspace/__init__.py — API PUBLICA del WPMS (V0.87, doc 18)
#
# [Δ doc 16 §4.1] Disciplina modular: este __init__ ES la API publica del modulo.
# El resto de la app importa SOLO desde `app.workspace` — nunca de
# app.workspace.models, .service ni .progress (internos). La frontera la vigila
# tests/test_module_boundaries.py.
#
# El WPMS es ESTADO operativo (SQL); el CONOCIMIENTO permanente vive en el MOS
# (`mem_project`). El WPMS escribe destilados al MOS por evento (W3), nunca el
# estado vivo. Extiende Project/Task (en app.db) + entidad nueva Milestone.

# --- Modelo propio ---
from .models import Milestone

# --- Servicio (namespace-modulo, patron decision_service del MOS) ---
from . import service as workspace_service

# --- Funciones puras de progreso (utiles directamente + testeables) ---
from .progress import DONE_STATUSES, compute_progress, is_done

__all__ = [
    "Milestone",
    "workspace_service",
    "compute_progress",
    "is_done",
    "DONE_STATUSES",
]
