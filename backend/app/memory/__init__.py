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

# --- Vault (V0.85, doc 07 §9): espejo Markdown, solo escritura ---
from .vault import write_daily_summary as vault_write_daily_summary
from .vault import write_decision as vault_write_decision

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
    # vault
    "vault_write_daily_summary",
    "vault_write_decision",
]
