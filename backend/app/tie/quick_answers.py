# app/tie/quick_answers.py — respuestas DETERMINISTAS sobre los datos del usuario
# (2026-07-24, arreglo definitivo tras el fallo reportado: "dime qué proyectos
# tengo" respondía "no tengo acceso a la lista de proyectos").
#
# EL PRINCIPIO (el que usan los asistentes de producción — Alexa/Siri/las
# "actions" de GPT): una pregunta sobre DATOS PROPIOS del sistema ("¿qué
# proyectos tengo?", "muestra mis agentes", "lista mis reglas") NO debe pasar
# por un LLM. El LLM puede ignorar el contexto, alucinar o degradar a una
# misión de minutos — todo observado en producción. La respuesta correcta es
# una CONSULTA SQL + una plantilla: determinista, instantánea (0 LLM) e
# imposible de alucinar.
#
# Conservador por diseño (mismo criterio que fast_precheck de A·VOZ-2): solo
# dispara con una pregunta de LISTADO clara y sin verbos de acción. "Crea un
# proyecto", "abre el proyecto X", "borra la regla Y" NO disparan — esas van al
# clasificador/toolloop (aithera_tool). Ante la duda, None (que decida el LLM).
from __future__ import annotations

import unicodedata
from typing import Optional

from app.core.strings import t as _t


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


# Verbos/segmentos de ACCIÓN: si aparecen, esto no es un listado — no disparar.
_ACTION_WORDS = (
    "crea", "crear", "nuevo", "nueva", "borra", "borrar", "elimina", "eliminar",
    "abre", "abrir", "cambia", "cambiar", "renombra", "archiva", "anade", "añade",
    "agrega", "modifica", "edita", "mueve", "cierra", "completa", "ejecuta",
    "activa", "desactiva", "pausa",
    "create", "new", "delete", "remove", "open", "change", "rename", "add",
    "edit", "move", "close", "run", "execute", "enable", "disable",
    "cree", "creer", "supprime", "ouvre", "ajoute", "modifie", "renomme",
    "cria", "criar", "apaga", "remove", "muda", "adiciona", "executa",
)

# Indicadores de PREGUNTA/LISTADO (al menos uno debe estar).
_QUERY_WORDS = (
    "que", "cuales", "cuantos", "cuantas", "tengo", "mis", "mi", "lista",
    "listame", "muestra", "muestrame", "dime", "ver", "ensename", "cuentame",
    "what", "which", "show", "list", "my", "have", "tell",
    "quels", "quelles", "mes", "montre", "affiche", "liste",
    "quais", "meus", "minhas", "tenho", "mostra", "lista",
)

_MAX_WORDS = 12   # una frase larga casi nunca es un listado puro → al LLM


def _matches(norm: str, nouns: tuple) -> bool:
    words = norm.replace("?", " ").replace("¿", " ").split()
    if not words or len(words) > _MAX_WORDS:
        return False
    if not any(n in norm for n in nouns):
        return False
    if any(w in _ACTION_WORDS for w in words):
        return False
    return any(w in _QUERY_WORDS for w in words) or norm.strip().endswith("?")


def try_answer(text: str) -> Optional[str]:
    """Si `text` es una pregunta de listado sobre los datos del propio sistema,
    devuelve la respuesta YA FORMATEADA (en el idioma de la app, vía el catálogo
    de strings). None = no es un listado claro → que siga el pipeline normal.
    Síncrono (SQL de milisegundos); los callers async lo envuelven en to_thread.
    Nunca lanza: cualquier error → None (el pipeline normal responde)."""
    try:
        norm = _norm(text)
        if _matches(norm, ("proyecto", "project", "projet", "projeto")):
            return _projects_answer()
        if _matches(norm, ("agente", "agent")):
            return _agents_answer()
        if _matches(norm, ("regla", "rule", "automatizacion", "automation", "regle")):
            return _rules_answer()
        if _matches(norm, ("tarea", "task", "tache", "tarefa", "pendiente")):
            return _tasks_answer()
        return None
    except Exception:
        return None


def _projects_answer() -> str:
    from app.db.database import Project, SessionLocal

    db = SessionLocal()
    try:
        projects = (
            db.query(Project).filter(Project.archived_at.is_(None))
            .order_by(Project.id.desc()).limit(50).all()
        )
        if not projects:
            return _t("quick.no_projects")
        lines = [_t("quick.projects_header", n=len(projects))]
        for p in projects:
            pct = int((p.progress or 0.0) * 100)
            ver = f" · v{p.current_version}" if p.current_version else ""
            lines.append(f"- {p.name} — {p.status or 'active'}, {pct}%{ver}")
        return "\n".join(lines)
    finally:
        db.close()


def _agents_answer() -> str:
    from app.db.database import Agent, SessionLocal

    db = SessionLocal()
    try:
        agents = db.query(Agent).order_by(Agent.id.desc()).limit(50).all()
        if not agents:
            return _t("quick.no_agents")
        lines = [_t("quick.agents_header", n=len(agents))]
        for a in agents:
            estado = _t("quick.enabled") if a.is_active else _t("quick.disabled")
            lines.append(f"- {a.name} ({a.agent_type or 'generic'}) — {estado}")
        return "\n".join(lines)
    finally:
        db.close()


def _rules_answer() -> str:
    from app.automation import AutomationRule
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        rules = db.query(AutomationRule).order_by(AutomationRule.id.desc()).limit(50).all()
        if not rules:
            return _t("quick.no_rules")
        lines = [_t("quick.rules_header", n=len(rules))]
        for r in rules:
            estado = _t("quick.enabled") if r.enabled else _t("quick.disabled")
            lines.append(f"- {r.name} ({r.trigger_type}) — {estado}")
        return "\n".join(lines)
    finally:
        db.close()


def _tasks_answer() -> str:
    from app.db.database import Project, SessionLocal, Task

    db = SessionLocal()
    try:
        tasks = (
            db.query(Task).filter(Task.status.notin_(("done", "completed")))
            .order_by(Task.id.desc()).limit(25).all()
        )
        if not tasks:
            return _t("quick.no_tasks")
        proj_names = {p.id: p.name for p in db.query(Project).all()}
        lines = [_t("quick.tasks_header", n=len(tasks))]
        for tk in tasks:
            proj = proj_names.get(tk.project_id)
            pref = f"[{proj}] " if proj else ""
            lines.append(f"- {pref}{tk.title} ({tk.status})")
        return "\n".join(lines)
    finally:
        db.close()
