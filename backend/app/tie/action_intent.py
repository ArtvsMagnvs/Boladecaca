# app/tie/action_intent.py — detector DETERMINISTA de "esto es una acción sobre
# Aithera" (2026-07-25, tras el fallo real: crear milestone+agente acabó en el
# camino conversacional y el modelo FINGIÓ haberlo hecho).
#
# EL FALLO QUE CIERRA (log real del usuario):
#     17:35:20 classify LLM: 5781ms modelo='llama3'
#     17:35:20 [intents] sin JSON parseable, fallback conversational
# Una petición de ACCIÓN ("crea una milestone MVP y un agente Investigador")
# dependía de que un LLM local produjera JSON válido. Al fallar, el fail-safe
# "conversational" (correcto para charla) tiraba la intención de acción a la
# basura: el turno acababa en chat SIN herramientas y el modelo respondía como
# si lo hubiera hecho. Dos mentiras seguidas.
#
# EL ARREGLO, Y POR QUÉ ES GLOBAL (no un parche):
#   1. Los VERBOS de acción y los SUSTANTIVOS de dominio se listan una vez y
#      cubren TODAS las acciones del catálogo de `aithera_tool` (proyectos,
#      hitos, tareas, agentes, reglas, recordatorios, idioma, modelo) — y las
#      futuras que usen los mismos sustantivos. `assert_covers_catalog()` lo
#      verifica CONTRA el catálogo real, así que una acción nueva sin cobertura
#      rompe un test en vez de fallar en silencio en producción.
#   2. No sustituye al clasificador ni al TIE: es una RED DE SEGURIDAD. Corrige
#      dos casos concretos y acotados (ver `intents.classify`):
#        · el LLM falló (sin JSON / error / excepción) → antes: charla. Ahora:
#          acción, con las herramientas puestas.
#        · el LLM dijo "conversational" pero el mensaje es claramente una orden
#          de actuar → se corrige el tipo (los modelos pequeños confunden
#          "créame X" con charla). El resto del intent del LLM se respeta.
#      Todo lo demás (planner, grafo, MEL, orquestador, multi-objetivo) sigue
#      exactamente igual: la versatilidad del chat no se toca.
from __future__ import annotations

import unicodedata
from typing import Optional

from app.tie.contracts import Intent, IntentType


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


# Verbos que expresan "hazlo" (es/en/fr/pt). Se comparan por PREFIJO para cubrir
# conjugaciones ("crea", "crear", "créame", "crealo", "creas"…).
_ACTION_VERB_STEMS = (
    # crear / añadir
    "crea", "crear", "cree", "creame", "genera", "generar", "anade", "anadir",
    "agrega", "agregar", "monta", "montar", "haz", "hazme", "pon", "ponme", "poner",
    "create", "add", "make", "generate", "set", "setup",
    "ajoute", "ajouter", "cree", "creer", "genere", "mets", "mettre",
    "cria", "criar", "adiciona", "adicionar", "gera", "poe", "por",
    # borrar / archivar
    "borra", "borrar", "elimina", "eliminar", "quita", "quitar", "archiva", "archivar",
    "delete", "remove", "archive", "supprime", "supprimer", "apaga", "apagar", "remove",
    # modificar / mover / renombrar
    "cambia", "cambiar", "modifica", "modificar", "edita", "editar", "actualiza",
    "actualizar", "renombra", "renombrar", "mueve", "mover", "asigna", "asignar",
    "change", "modify", "edit", "update", "rename", "move", "assign",
    "modifie", "modifier", "renomme", "deplace", "assigne",
    "muda", "mudar", "altera", "atualiza", "renomeia", "move", "atribui",
    # abrir / ejecutar / activar
    "abre", "abrir", "ejecuta", "ejecutar", "lanza", "lanzar", "activa", "activar",
    "desactiva", "desactivar", "cierra", "cerrar", "completa", "completar",
    "open", "run", "execute", "launch", "start", "enable", "disable", "close", "complete",
    "ouvre", "ouvrir", "execute", "lance", "active", "desactive", "ferme",
    "abre", "abrir", "executa", "lanca", "ativa", "desativa", "fecha",
)

# Sustantivos de DOMINIO de la app. Cada uno mapea a la familia de acciones del
# catálogo de `aithera_tool` que lo gobierna (ver `assert_covers_catalog`).
_DOMAIN_NOUNS: dict[str, tuple[str, ...]] = {
    "project": ("proyecto", "proyectos", "project", "projects", "projet", "projets", "projeto", "projetos"),
    "milestone": ("milestone", "milestones", "hito", "hitos", "jalon", "marco"),
    "task": ("tarea", "tareas", "task", "tasks", "tache", "taches", "tarefa", "tarefas"),
    "agent": ("agente", "agentes", "agent", "agents"),
    "rule": ("regla", "reglas", "rule", "rules", "automatizacion", "automatizaciones",
             "automation", "regle", "regles", "regra", "regras",
             "recordatorio", "recordatorios", "reminder", "reminders", "cron",
             "autorespuesta", "auto-respuesta", "respuesta automatica"),
    "language": ("idioma", "idiomas", "language", "langue", "lingua",
                 "espanol", "ingles", "frances", "portugues",
                 "english", "spanish", "french", "portuguese"),
    "model": ("modelo", "modelos", "model", "models", "modele", "modelo"),
}

# Qué acciones del catálogo cubre cada sustantivo (para el test de cobertura).
_NOUN_TO_ACTIONS: dict[str, tuple[str, ...]] = {
    "project": ("list_projects", "project_status", "create_project"),
    "milestone": ("create_milestone",),
    "task": ("create_task", "update_task"),
    "agent": ("create_agent", "assign_tools", "list_agents", "run_agent_task"),
    "rule": ("create_rule", "create_cron_job", "list_rules", "toggle_rule",
             "create_auto_reply_rule"),
    "language": ("set_language",),
    "model": ("set_chat_model",),
}

_MAX_WORDS = 60   # una orden puede ser larga ("crea X y además Y con Z…")


def _domains(norm: str) -> list[str]:
    return [dom for dom, words in _DOMAIN_NOUNS.items()
            if any(w in norm for w in words)]


def _has_action_verb(norm: str) -> bool:
    words = [w.strip(".,;:!?¡¿()[]{}\"'…") for w in norm.split()]
    for w in words:
        if w in _ACTION_VERB_STEMS:
            return True
        # Prefijo, para cubrir conjugaciones y pronombres enclíticos sin listar
        # cada forma: "creame", "crearlo", "ponle", "activalo", "asignale",
        # "creado"… Se admiten stems de 3+ letras ("pon", "haz") porque el
        # detector YA exige además un sustantivo de dominio, así que un "pon" en
        # otro contexto no dispara nada.
        if any(w.startswith(stem) and len(w) - len(stem) <= 4
               for stem in _ACTION_VERB_STEMS if len(stem) >= 3):
            return True
    return False


def looks_like_action(text: str) -> bool:
    """True si el mensaje pide ACTUAR sobre Aithera (verbo de acción + sustantivo
    de dominio). Determinista, sin LLM. Conservador: sin las DOS señales, False."""
    norm = _norm(text)
    if not norm or len(norm.split()) > _MAX_WORDS:
        return False
    return bool(_domains(norm)) and _has_action_verb(norm)


def action_intent(text: str) -> Optional[Intent]:
    """Intent de ACCIÓN listo para el camino de acción directa del TIE (toolloop
    con la tool `aithera`), o None si el mensaje no es una orden de actuar.

    `requires_planning=False` a propósito: crear/abrir/cambiar cosas de la app es
    una secuencia mecánica de llamadas a `aithera_tool`, no un plan que revisar
    (mismo criterio que `Intent.is_direct_action`). Si de verdad hiciera falta
    plan (varios entregables dependientes), el clasificador LLM lo marcará
    cuando funcione — este detector solo actúa cuando el LLM NO ha podido."""
    if not looks_like_action(text):
        return None
    return Intent(
        type=IntentType.EXECUTE,
        goal=text.strip()[:200],
        domain=_domains(_norm(text)),
        confidence=1.0,                 # el detector es determinista
        requires_planning=False,
        requires_tools=["aithera"],
        requires_memory=False,
        model_capability="agentic",
        raw_text=text.strip(),
    )


def assert_covers_catalog(catalog_action_ids: set) -> set:
    """Devuelve las acciones del catálogo de `aithera_tool` que NINGÚN sustantivo
    de dominio cubre. Vacío = cobertura total. Lo usa un test: si mañana se añade
    una acción nueva a la tool y nadie la mapea aquí, el test falla — así el
    detector no se queda obsoleto en silencio (que es como nacen los parches)."""
    cubiertas = {a for acts in _NOUN_TO_ACTIONS.values() for a in acts}
    return set(catalog_action_ids) - cubiertas
