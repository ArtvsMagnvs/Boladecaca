# backend/app/memory/__init__.py — API PUBLICA del MOS (Memory Operating System)
#
# [Δ doc 16 §4.1] Disciplina modular: este __init__ ES la API publica del
# paquete. El resto de la app importa SOLO desde `app.memory` — nunca de
# app.memory.stores.*, .router ni .interfaces (internos). La frontera la vigila
# tests/test_module_boundaries.py.
#
# V0.6 (legacy): `memory_manager` sigue expuesto para los consumidores actuales
# (chat/gateway/main). Se migran a `memory_router` en M4; hasta entonces conviven.
# V0.85 (M1): se anaden los contratos congelados + memory_router + skill_store.

# --- Legacy (V0.6): memoria semantica original ---
from .memory_manager import MemoryManager, memory_manager, CHROMA_PATH

# --- Contratos congelados (V0.85 M1) ---
from .interfaces import (
    IMemoryStore,
    ISkillStore,
    MemoryType,
    MemoryItem,
    MemoryQuery,
    LocalSkill,
    SkillStatus,
)

# --- Puntos de acceso publicos (singletons) ---
from .router import MemoryRouter, memory_router
from .stores.skill_store import LocalSkillStore, skill_store
from .stores.local_store import ACTIVE_TYPES

# --- Vault (V0.85, doc 07 §9): espejo Markdown, solo escritura ---
from .vault import write_daily_summary as vault_write_daily_summary
from .vault import write_decision as vault_write_decision


# --- Jobs de fondo (V0.85 M2/M3, V0.9 A2a, R6.5c) ---
#
# [R7] Se exponen aquí para que NADIE tenga que importar `app.memory.ingestion`,
# `.summarizer`, `.lifecycle` ni `.profile` directamente: eran 12 imports en
# `main.py`, `endpoints/memory.py`, `automation/actions.py` y `chat_service.py`
# atravesando la frontera del módulo (doc 16 §4.1).
#
# PEREZOSOS a propósito (PEP 562), y esto NO es un capricho: los 4 arrastran
# dependencias caras (ChromaDB, sentence-transformers, el WPMS) y sus callers ya
# los importaban DENTRO de la función justamente para no pagarlo en el arranque
# — hay un test con presupuesto de 2 s sobre `import app.main` que salta si esto
# se hace eager. Con `__getattr__`, `from app.memory import profile` dentro de
# una función sigue siendo tan diferido como antes, pero ya respeta la frontera.
_LAZY_SUBMODULES = ("ingestion", "summarizer", "lifecycle", "profile")


def __getattr__(name: str):
    if name in _LAZY_SUBMODULES:
        import importlib

        modulo = importlib.import_module(f"{__name__}.{name}")
        globals()[name] = modulo      # se cachea: el segundo acceso es gratis
        return modulo
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(list(globals()) + list(_LAZY_SUBMODULES))


__all__ = [
    # legacy
    "MemoryManager",
    "memory_manager",
    "CHROMA_PATH",
    # contratos
    "IMemoryStore",
    "ISkillStore",
    "MemoryType",
    "MemoryItem",
    "MemoryQuery",
    "LocalSkill",
    "SkillStatus",
    # acceso
    "MemoryRouter",
    "memory_router",
    "LocalSkillStore",
    "skill_store",
    "ACTIVE_TYPES",
    # vault
    "vault_write_daily_summary",
    "vault_write_decision",
    # jobs de fondo (perezosos)
    "ingestion",
    "summarizer",
    "lifecycle",
    "profile",
]
