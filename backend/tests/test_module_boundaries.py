# tests/test_module_boundaries.py — [Δ doc 16 §4.4] fronteras modulares del MOS
#
# Disciplina modular sin frameworkitis (doc 16): cada modulo expone su API en su
# __init__.py y el resto de la app la consume SOLO por ahi. Este test vigila la
# frontera del MOS:
#   1. app.memory exporta la API publica esperada (barrel completo).
#   2. Ningun modulo FUERA de app/memory importa los internos del MOS
#      (app.memory.stores.*, app.memory.router, app.memory.interfaces).
#
# Se permite el import legacy `app.memory.memory_manager` (grandfathered hasta
# que chat/gateway/main migren a memory_router en M4).
import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
MEMORY_DIR = APP_DIR / "memory"

# Internos del MOS que NADIE de fuera debe importar directamente.
FORBIDDEN = (
    "app.memory.stores",
    "app.memory.router",
    "app.memory.interfaces",
)


def test_public_api_completa():
    """El barrel app.memory expone toda la API publica congelada de M1."""
    import app.memory as mem

    esperado = {
        # contratos
        "IMemoryStore", "ISkillStore", "MemoryType", "MemoryItem",
        "MemoryQuery", "LocalSkill", "SkillStatus",
        # acceso
        "MemoryRouter", "memory_router", "LocalSkillStore", "skill_store",
        # legacy
        "MemoryManager", "memory_manager", "CHROMA_PATH",
    }
    faltan = esperado - set(dir(mem))
    assert not faltan, f"app.memory no exporta: {sorted(faltan)}"
    # __all__ debe declararlos (contrato explicito, no accidental).
    assert esperado.issubset(set(mem.__all__)), (
        f"faltan en __all__: {sorted(esperado - set(mem.__all__))}"
    )


def test_nadie_de_fuera_importa_internos_del_mos():
    """Ningun .py fuera de app/memory/ importa los internos del MOS."""
    offenders: list[str] = []
    for py in APP_DIR.rglob("*.py"):
        # Los propios modulos del MOS SI pueden usar sus internos.
        if MEMORY_DIR in py.parents or py.parent == MEMORY_DIR:
            continue
        text = py.read_text(encoding="utf-8", errors="ignore")
        for internal in FORBIDDEN:
            # coincide con `import app.memory.stores...` y `from app.memory.router import`
            pattern = rf"\b(from|import)\s+{re.escape(internal)}\b"
            if re.search(pattern, text):
                offenders.append(f"{py.relative_to(APP_DIR.parent)} -> {internal}")
    assert not offenders, (
        "Modulos que saltan la frontera del MOS (usa `from app.memory import ...`):\n"
        + "\n".join(offenders)
    )
