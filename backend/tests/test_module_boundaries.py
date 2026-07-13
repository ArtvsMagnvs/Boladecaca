# tests/test_module_boundaries.py — [Δ doc 16 §4.4] fronteras modulares
#
# Disciplina modular sin frameworkitis (doc 16): cada modulo expone su API en su
# __init__.py y el resto de la app la consume SOLO por ahi. Este test vigila las
# fronteras de los modulos con API publica congelada:
#   1. app.memory (MOS) y app.workspace (WPMS) exportan su API publica esperada.
#   2. Ningun modulo FUERA de un modulo importa sus internos
#      (app.memory.stores/.router/.interfaces/.vault; app.workspace.models/
#      .service/.progress).
#
# Se permite el import legacy `app.memory.memory_manager` (grandfathered).
import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
MEMORY_DIR = APP_DIR / "memory"
WORKSPACE_DIR = APP_DIR / "workspace"

# Internos que NADIE de fuera del propio modulo debe importar directamente.
# Cada entrada: (prefijo de import prohibido, directorio propietario que SI puede).
FORBIDDEN_MODULES = (
    ("app.memory.stores", MEMORY_DIR),
    ("app.memory.router", MEMORY_DIR),
    ("app.memory.interfaces", MEMORY_DIR),
    ("app.memory.vault", MEMORY_DIR),
    ("app.workspace.models", WORKSPACE_DIR),
    ("app.workspace.service", WORKSPACE_DIR),
    ("app.workspace.progress", WORKSPACE_DIR),
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
        # vault
        "vault_write_daily_summary", "vault_write_decision",
    }
    faltan = esperado - set(dir(mem))
    assert not faltan, f"app.memory no exporta: {sorted(faltan)}"
    # __all__ debe declararlos (contrato explicito, no accidental).
    assert esperado.issubset(set(mem.__all__)), (
        f"faltan en __all__: {sorted(esperado - set(mem.__all__))}"
    )


def test_workspace_public_api_completa():
    """El barrel app.workspace expone la API publica del WPMS (doc 18 §11)."""
    import app.workspace as ws

    esperado = {"Milestone", "workspace_service", "compute_progress", "is_done", "DONE_STATUSES"}
    faltan = esperado - set(dir(ws))
    assert not faltan, f"app.workspace no exporta: {sorted(faltan)}"
    assert esperado.issubset(set(ws.__all__)), (
        f"faltan en __all__: {sorted(esperado - set(ws.__all__))}"
    )


def test_nadie_de_fuera_importa_internos_de_un_modulo():
    """Ningun .py fuera de un modulo importa sus internos (MOS y WPMS)."""
    offenders: list[str] = []
    for py in APP_DIR.rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="ignore")
        for internal, owner_dir in FORBIDDEN_MODULES:
            # El propio modulo duenno SI puede usar sus internos.
            if owner_dir in py.parents or py.parent == owner_dir:
                continue
            # coincide con `import app.x.y...` y `from app.x.y import`
            pattern = rf"\b(from|import)\s+{re.escape(internal)}\b"
            if re.search(pattern, text):
                offenders.append(f"{py.relative_to(APP_DIR.parent)} -> {internal}")
    assert not offenders, (
        "Modulos que saltan una frontera (usa `from app.<modulo> import ...`):\n"
        + "\n".join(offenders)
    )
