# backend/app/learner/__init__.py — API PÚBLICA del Learner (V1.1)
#
# [doc 16] Disciplina modular: este __init__ ES la API pública del paquete. El
# resto de la app importa SOLO desde `app.learner` — nunca de los internos
# (models/ladder/library/proposals/backfill/analysis). La frontera la vigila
# tests/test_module_boundaries.py.
#
# [doc 15, regla constitucional] El Learner observa, analiza y PROPONE. Nunca
# planifica (eso es del TIE), nunca ejecuta (AE/runtimes), nunca escribe fuera
# de sus tablas (`skills`, `skill_events`, `learner_proposals`) y de las APIs
# públicas del MOS. El contrato de producto que lo vigila:
# tests/test_product_learner.py.
#
# V1.1 L1: LSL completa (SkillLibrary sobre SQL + eventos + undo) + escalera de
#          confianza (ladder) + cuarentena (proposal_service) + backfill del
#          stub de V0.85 + firmas congeladas del análisis (L2/L3).
# V1.1 L2: Mission Learning — contadores (model_stats/tool_stats), reflexión
#          post-misión en la Decision API y candidatos a skill por acumulación
#          de evidencia. Suscrito a `mission.completed`/`failed`.
# V1.1 L2b: atribución de fallos — `failure_stats` (de quién fue cada fallo),
#          stats JUSTAS (lo ajeno al modelo sale del denominador) y propuestas
#          `config_fix` deterministas. La taxonomía en sí vive en
#          `app/core/failures.py`: la escriben MEL/toolloop/executor/planner, y
#          ninguno de ellos puede importar internos del Learner (doc 16).
from app.learner.models import (
    FailureStat,
    LearnerProposal,
    ModelStat,
    Skill,
    SkillEvent,
    ToolStat,
)
from app.learner import ladder
from app.learner.library import SkillLibrary, skill_library
from app.learner.proposals import (
    ProposalService,
    proposal_service,
    register_applier,
    registered_kinds,
)
from app.learner.backfill import backfill_from_mem_skill
from app.learner.stats import (
    config_gaps,
    failure_summary,
    model_ranking,
    tool_ranking,
)
from app.learner.mission_learning import (
    content_words,
    learn_from_mission,
    register_handlers,
    same_work,
    similarity,
)
from app.learner.authoring import learn_this
from app.learner.analysis import (
    analyze_cross_project,
    analyze_error_patterns,
    analyze_repeated_missions,
    error_findings,
    last_report,
    recompute_skill_quality,
    run_nightly_analysis,
    weekly_learning_report,
)

__all__ = [
    # modelos (solo para create_all/migraciones/tests — el CRUD va por servicios)
    "Skill", "SkillEvent", "LearnerProposal", "ModelStat", "ToolStat", "FailureStat",
    # la escalera (funciones puras: también son la doc ejecutable de la política)
    "ladder",
    # LSL
    "SkillLibrary", "skill_library",
    # cuarentena
    "ProposalService", "proposal_service", "register_applier", "registered_kinds",
    # arranque
    "backfill_from_mem_skill", "register_handlers",
    # Mission Learning (L2)
    "learn_from_mission", "same_work", "similarity", "content_words",
    "model_ranking", "tool_ranking",
    # atribución de fallos (L2b) — lo que consume la pestaña "Salud" de L4
    "failure_summary", "config_gaps",
    # el LLL en batch (L3)
    "analyze_repeated_missions", "analyze_error_patterns", "analyze_cross_project",
    "recompute_skill_quality", "weekly_learning_report", "run_nightly_analysis",
    "error_findings", "last_report",
    # "aprende esto" — la vía por la que enseña el usuario (L3)
    "learn_this",
]
