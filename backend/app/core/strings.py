# app/core/strings.py — catálogo de textos backend NO generados por LLM (I18N-10)
#
# QUÉ RESUELVE: I18N-9 (`app/core/language.py`) fuerza el idioma en los prompts
# que van a un LLM (chat, resumen de misión, plan). Pero hay texto que el
# usuario lee que NO pasa por ningún LLM — son las plantillas DETERMINISTAS de
# respaldo (cuando el modelo está caído o devuelve vacío) y los mensajes de
# estado/error de puro código: `responder._template_success/_template_failure`,
# `tie/pipeline.py` (aclaraciones de modelo, gate del plan, cancelaciones) y
# `orchestrator/consolidator._plantilla` (el equivalente multi-objetivo). Sin
# esto, aunque el usuario elija inglés, un fallo de red en el LLM justo esa vez
# le devolvería una respuesta en español — inconsistente y confuso.
#
# MISMO PATRÓN que el `useI18n`/`translate()` del frontend (store/useI18n.ts):
# diccionario plano {idioma: {clave: texto}} con interpolación `{var}`, fallback
# a español si falta la clave o el idioma. Aquí en Python porque este texto lo
# genera el backend, nunca lo ve el bundle de React.
from __future__ import annotations

from typing import Optional

from app.core.language import ui_language

# ---------------------------------------------------------------------------
# Catálogo. Namespaced por módulo de origen (responder.*, pipeline.*,
# orchestrator.*) para que sea obvio de dónde viene cada clave al leerlo.
# ---------------------------------------------------------------------------
_ES: dict[str, str] = {
    # responder.py — plantillas deterministas (sin LLM)
    "responder.stopped_no_steps": "He parado la tarea antes de completar ningún paso, como pediste.",
    "responder.node_done_fallback": "hecho",
    "responder.completed_header": "He completado {n} paso(s) de «{goal}»:",
    "responder.could_not_complete": "No pude completar: {items}",
    "responder.left_untried": "Y quedaron sin intentar: {items}",
    "responder.you_cancelled": "Cancelaste: {items}",
    "responder.no_progress": "No he podido avanzar con «{goal}».",
    "responder.failed_with_reasons": "No he podido completar «{goal}». Falló: {reasons}",
    "responder.plan_step_permission_mark": " (pide permiso)",
    # [S11, doc 34 §S11] Un paso pidió una herramienta que no se le concedió;
    # el resultado puede estar incompleto por eso.
    "responder.limitations_note": "Ojo: no pude usar {tools} — el resultado puede estar incompleto en lo que dependía de eso.",
    # tie/pipeline.py — aclaraciones de modelo, estados, gate del plan
    "pipeline.model_unknown": (
        "No tengo configurado ningún modelo que se llame «{name}». "
        "Modelos disponibles ahora mismo: {available}. "
        "Puedes conectar más en Ajustes → Proveedores de IA."
    ),
    "pipeline.model_pinned_project": (
        "Hecho. A partir de ahora usaré {provider} ({model}) para todo este "
        "proyecto. Puedes quitarlo cuando quieras en Ajustes → Inteligencia."
    ),
    "pipeline.model_no_project_bind": (
        "Puedo usar {provider} para este mensaje, pero esta conversación no está "
        "ligada a ningún proyecto, así que no puedo fijarlo «para todo el proyecto» "
        "desde aquí. Si quieres fijarlo a un proyecto, dímelo desde ese proyecto o "
        "en Ajustes → Inteligencia. ¿Lo uso solo para este mensaje?"
    ),
    "pipeline.model_scope_unspecified": (
        "¿Quieres que use {provider} ({model}) solo para esta petición, o a partir "
        "de ahora para todo? Dímelo y sigo."
    ),
    # [PU3, doc 35] Bajo perfil Autónomo esto ya NO se pregunta (Autónomo =
    # nunca preguntar nada, decisión del usuario) — se asume "solo esta
    # petición" (el alcance más limitado, más fácil de deshacer) y se avisa
    # de qué se asumió, nunca en silencio.
    "pipeline.model_scope_auto_task": (
        "Uso {provider} ({model}) para esta petición (no dijiste si querías dejarlo "
        "fijo, y con Autónomo activo no te lo pregunto — si quieres fijarlo para "
        "todo el proyecto, dímelo explícitamente)."
    ),
    "pipeline.internal_error_retry": "He tenido un problema interno procesando eso. Inténtalo otra vez.",
    "pipeline.generic_done": "Hecho.",
    "pipeline.generic_could_not": "No pude completarlo.",
    "pipeline.generic_problem": "He tenido un problema procesando eso.",
    "pipeline.cannot_capability": (
        "No puedo hacer esto de forma completa con mis capacidades actuales: {reason}"
    ),
    "pipeline.plan_needs_approval": (
        "He preparado un plan de {n} paso(s) para «{goal}». Como toca algo sensible, "
        "necesito tu visto bueno antes de ejecutarlo:\n\n{plan_summary}"
    ),
    "pipeline.waiting_confirmation": "He empezado y estoy esperando tu confirmación para un paso.",
    "pipeline.plan_discarded": "He descartado el plan, como pediste. No he ejecutado nada.",
    "pipeline.stream_stopped": "Lo paraste antes de que terminara.",
    "pipeline.no_response": "(sin respuesta)",
    "pipeline.plan_gate_title": "Plan de {n} paso(s): {goal}",
    # orchestrator/consolidator.py — respuesta multi-objetivo
    "orchestrator.no_objectives": "No he identificado ningún encargo en tu mensaje.",
    "orchestrator.template_completed_header": "He completado:",
    "orchestrator.template_waiting_header": "Esperando tu aprobación:",
    "orchestrator.template_failed_header": "No he podido completar:",
    "orchestrator.template_nothing": "No he podido completar ninguno de los encargos.",
    # estados en vivo del streaming (Chat.tsx los muestra en crudo + "…")
    # ---- Rastro de actividad EN VIVO (progress.py) -------------------------
    # Frases CORTAS "acción + objeto" que el chat va mostrando mientras trabaja
    # (petición del usuario 2026-08-02). Nunca llevan punto final: son una
    # etiqueta de estado, no una frase.
    "act.reading": "Leyendo {obj}",
    "act.writing": "Escribiendo {obj}",
    "act.listing": "Explorando {obj}",
    "act.deleting": "Borrando {obj}",
    "act.searching_web": "Buscando en la web: {obj}",
    "act.browsing": "Abriendo {obj}",
    "act.browser_acting": "Navegando: {obj}",
    "act.running": "Ejecutando {obj}",
    "act.git": "Git: {obj}",
    "act.email_reading": "Revisando el correo",
    "act.email_writing": "Redactando un correo a {obj}",
    "act.calendar": "Consultando el calendario",
    "act.memory_read": "Buscando en la memoria: {obj}",
    "act.memory_write": "Guardando en la memoria",
    "act.self_projects": "Consultando tus proyectos",
    "act.self_agents": "Consultando tus agentes",
    "act.self_rules": "Consultando tus automatizaciones",
    "act.self_read": "Consultando {obj}",
    "act.self_write": "Trabajando en Aithera: {obj}",
    "act.desktop": "Usando el escritorio: {obj}",
    "act.downloading": "Descargando {obj}",
    "act.generic": "{tool}: {obj}",
    "act.generic_noobj": "Usando {tool}",
    "act.thinking": "Pensando el siguiente paso",
    "act.planning": "Preparando un plan",
    "act.plan_ready": "Plan listo: {n} paso(s)",
    "act.plan_none": "Sin plan válido: lo resuelvo directamente",
    "act.step": "Paso {i} de {n}: {obj}",
    "act.step_done": "Paso {i} terminado",
    "act.step_failed": "Paso {i} no salió: {obj}",
    "act.asking_permission": "Te pido permiso para {obj}",
    "act.asking_user": "Te he hecho una pregunta",
    "act.permission_granted": "Permiso concedido",
    "act.permission_denied": "Sin permiso: sigo sin {obj}",
    "act.failed": "Falló {obj}, pruebo otra vía",
    "act.writing_answer": "Redactando la respuesta",
    "status.analyzing": "analizando",
    "status.planning": "planificando",
    "status.executing": "ejecutando",
    # [S4] latido: se emite cada TIE_HEARTBEAT_S mientras se espera al
    # clasificador/planner/acción, para que ningún turno se quede mudo.
    "status.still_working": "sigo trabajando",
    "orchestrator.status_multi": "son {n} encargos: los hago a la vez",
    "orchestrator.status_progress": "{done} de {n} terminados",
    # respuestas deterministas sobre los datos propios (quick_answers, 0 LLM)
    "quick.projects_header": "Tienes {n} proyecto(s):",
    "quick.no_projects": "No tienes ningún proyecto todavía. Dime un nombre y te lo creo.",
    "quick.agents_header": "Tienes {n} agente(s):",
    "quick.no_agents": "No tienes ningún agente todavía. Puedo crearte uno.",
    "quick.rules_header": "Tienes {n} regla(s) de automatización:",
    "quick.no_rules": "No tienes ninguna regla de automatización todavía.",
    "quick.tasks_header": "Tienes {n} tarea(s) abiertas:",
    "quick.no_tasks": "No tienes tareas abiertas ahora mismo.",
    # grounding.py — la coletilla honesta del camino corto (S2·S6, doc 34)
    "grounding.no_tools_note": (
        "(Nota: en este turno no he ejecutado ninguna herramienta, así que lo "
        "anterior sale de mi conocimiento general y no lo he verificado en tu "
        "sistema. Si quieres que lo compruebe de verdad, dímelo.)"
    ),
    # Aviso FUERTE: la respuesta presenta datos concretos (listados, contenido
    # de archivos, recuentos, fuentes) que en este camino NO puede haber leído.
    "grounding.fabricated_note": (
        "⚠️ AVISO IMPORTANTE: en este turno no he ejecutado ninguna herramienta, "
        "así que NO he leído tus archivos ni visitado ninguna web. Los datos "
        "concretos que aparecen arriba (listados, contenidos, cifras o fuentes) "
        "son una suposición mía y lo más probable es que NO coincidan con la "
        "realidad. Pídemelo otra vez y lo compruebo de verdad."
    ),
    "quick.enabled": "activa",
    "quick.disabled": "inactiva",
    # [PU10, doc 35] mini-chat de memoria (guarda/busca/olvida, 0 LLM)
    "quick.memory.hint": (
        "No he reconocido eso como un comando de memoria. Prueba con "
        "«guarda que…», «¿qué sabes de…?» u «olvida lo de…»."
    ),
    "quick.memory.unavailable": "La memoria no está disponible ahora mismo.",
    "quick.memory.save_empty": "Dime qué quieres que guarde.",
    "quick.memory.save_failed": "No he podido guardarlo.",
    "quick.memory.saved": "Guardado: «{content}». Lo tendré en cuenta a partir de ahora.",
    "quick.memory.search_empty": "Dime qué quieres que busque.",
    "quick.memory.search_empty_result": "No tengo nada guardado sobre «{query}».",
    "quick.memory.search_prefs_header": "Preferencias guardadas:",
    "quick.memory.search_facts_header": "Otros datos que recuerdo:",
    "quick.memory.forget_empty": "Dime qué quieres que olvide.",
    "quick.memory.forget_none": "No he encontrado nada guardado sobre «{query}».",
    "quick.memory.forget_ambiguous": (
        "Hay {n} cosas guardadas que coinciden — dime cuál con más detalle:"
    ),
    "quick.memory.forget_failed": "No he podido olvidarlo.",
    "quick.memory.forgotten": "Olvidado: «{content}».",
    "pipeline.ack_mission": "Entendido, me pongo con ello: {goal}. Te cuento en cuanto lo tenga.",
    # [A·VOZ-4] Misiones en segundo plano (modo conversación): acuse + reporte async
    "conversation.acuse": "Vale, me pongo a ello. Te aviso cuando esté; sigue hablando si quieres.",
    "conversation.report_done": "Ya está: {outcome}",
    "conversation.report_failed": "No he podido con lo que me pediste: {outcome}",
    "conversation.report_error": "He tenido un problema con esa tarea y no he podido terminarla.",
    "conversation.gate_pending": (
        "Para seguir con «{goal}» necesito tu permiso para un paso sensible. "
        "Lo tienes esperando en Misiones."
    ),
}

_EN: dict[str, str] = {
    "responder.stopped_no_steps": "I stopped the task before completing any step, as you asked.",
    "responder.node_done_fallback": "done",
    "responder.completed_header": "I completed {n} step(s) of «{goal}»:",
    "responder.could_not_complete": "I couldn't complete: {items}",
    "responder.left_untried": "And these were left untried: {items}",
    "responder.you_cancelled": "You cancelled: {items}",
    "responder.no_progress": "I couldn't make progress on «{goal}».",
    "responder.failed_with_reasons": "I couldn't complete «{goal}». It failed: {reasons}",
    "responder.plan_step_permission_mark": " (needs your approval)",
    "responder.limitations_note": "Note: I couldn't use {tools} — the result may be incomplete because of that.",
    "pipeline.model_unknown": (
        "I don't have any model configured called «{name}». "
        "Models available right now: {available}. "
        "You can connect more in Settings → AI Providers."
    ),
    "pipeline.model_pinned_project": (
        "Done. From now on I'll use {provider} ({model}) for this entire "
        "project. You can remove it whenever you want in Settings → Intelligence."
    ),
    "pipeline.model_no_project_bind": (
        "I can use {provider} for this message, but this conversation isn't "
        "linked to any project, so I can't pin it \"for the whole project\" from "
        "here. If you want to pin it to a project, tell me from that project or "
        "in Settings → Intelligence. Should I use it just for this message?"
    ),
    "pipeline.model_scope_unspecified": (
        "Do you want me to use {provider} ({model}) just for this request, or "
        "from now on for everything? Let me know and I'll continue."
    ),
    "pipeline.model_scope_auto_task": (
        "Using {provider} ({model}) for this request (you didn't say whether you "
        "wanted it pinned, and with Autonomous mode on I won't ask — if you want it "
        "pinned for the whole project, just say so explicitly)."
    ),
    "pipeline.internal_error_retry": "I ran into an internal problem processing that. Try again.",
    "pipeline.generic_done": "Done.",
    "pipeline.generic_could_not": "I couldn't complete it.",
    "pipeline.generic_problem": "I ran into a problem processing that.",
    "pipeline.cannot_capability": (
        "I can't fully do this with my current capabilities: {reason}"
    ),
    "pipeline.plan_needs_approval": (
        "I've prepared a {n}-step plan for «{goal}». Since it touches something "
        "sensitive, I need your go-ahead before running it:\n\n{plan_summary}"
    ),
    "pipeline.waiting_confirmation": "I've started and I'm waiting for your confirmation for one step.",
    "pipeline.plan_discarded": "I've discarded the plan, as you asked. I haven't executed anything.",
    "pipeline.stream_stopped": "You stopped it before it finished.",
    "pipeline.no_response": "(no response)",
    "pipeline.plan_gate_title": "Plan of {n} step(s): {goal}",
    "orchestrator.no_objectives": "I didn't identify any task in your message.",
    "orchestrator.template_completed_header": "I completed:",
    "orchestrator.template_waiting_header": "Waiting for your approval:",
    "orchestrator.template_failed_header": "I couldn't complete:",
    "orchestrator.template_nothing": "I couldn't complete any of the tasks.",
    # ---- Live activity trail (progress.py) ---------------------------------
    "act.reading": "Reading {obj}",
    "act.writing": "Writing {obj}",
    "act.listing": "Exploring {obj}",
    "act.deleting": "Deleting {obj}",
    "act.searching_web": "Searching the web: {obj}",
    "act.browsing": "Opening {obj}",
    "act.browser_acting": "Browsing: {obj}",
    "act.running": "Running {obj}",
    "act.git": "Git: {obj}",
    "act.email_reading": "Checking email",
    "act.email_writing": "Drafting an email to {obj}",
    "act.calendar": "Checking the calendar",
    "act.memory_read": "Searching memory: {obj}",
    "act.memory_write": "Saving to memory",
    "act.self_projects": "Checking your projects",
    "act.self_agents": "Checking your agents",
    "act.self_rules": "Checking your automations",
    "act.self_read": "Checking {obj}",
    "act.self_write": "Working on Aithera: {obj}",
    "act.desktop": "Using the desktop: {obj}",
    "act.downloading": "Downloading {obj}",
    "act.generic": "{tool}: {obj}",
    "act.generic_noobj": "Using {tool}",
    "act.thinking": "Thinking about the next step",
    "act.planning": "Drawing up a plan",
    "act.plan_ready": "Plan ready: {n} step(s)",
    "act.plan_none": "No valid plan: handling it directly",
    "act.step": "Step {i} of {n}: {obj}",
    "act.step_done": "Step {i} done",
    "act.step_failed": "Step {i} did not work: {obj}",
    "act.asking_permission": "Asking your permission to {obj}",
    "act.asking_user": "I have asked you a question",
    "act.permission_granted": "Permission granted",
    "act.permission_denied": "No permission: still without {obj}",
    "act.failed": "{obj} failed, trying another way",
    "act.writing_answer": "Writing the answer",
    "status.analyzing": "analyzing",
    "status.planning": "planning",
    "status.executing": "executing",
    "status.still_working": "still working",
    "orchestrator.status_multi": "that's {n} tasks: I'm doing them at the same time",
    "orchestrator.status_progress": "{done} of {n} done",
    "quick.projects_header": "You have {n} project(s):",
    "quick.no_projects": "You don't have any projects yet. Give me a name and I'll create one.",
    "quick.agents_header": "You have {n} agent(s):",
    "quick.no_agents": "You don't have any agents yet. I can create one for you.",
    "quick.rules_header": "You have {n} automation rule(s):",
    "quick.no_rules": "You don't have any automation rules yet.",
    "quick.tasks_header": "You have {n} open task(s):",
    "quick.no_tasks": "You have no open tasks right now.",
    "grounding.no_tools_note": (
        "(Note: I didn't run any tool in this turn, so the above comes from my "
        "general knowledge and I haven't verified it on your system. Tell me if "
        "you want me to actually check it.)"
    ),
    "grounding.fabricated_note": (
        "⚠️ IMPORTANT: I didn't run any tool in this turn, so I have NOT read "
        "your files or visited any website. The specific data above (listings, "
        "file contents, counts or sources) is a guess of mine and most likely "
        "does NOT match reality. Ask me again and I'll actually check it."
    ),
    "quick.enabled": "enabled",
    "quick.disabled": "disabled",
    # [PU10, doc 35] memory mini-chat (save/search/forget, 0 LLM)
    "quick.memory.hint": (
        "I didn't recognize that as a memory command. Try \"save that…\", "
        "\"what do you know about…?\" or \"forget that…\"."
    ),
    "quick.memory.unavailable": "Memory isn't available right now.",
    "quick.memory.save_empty": "Tell me what you want me to save.",
    "quick.memory.save_failed": "I couldn't save that.",
    "quick.memory.saved": "Saved: \"{content}\". I'll keep that in mind from now on.",
    "quick.memory.search_empty": "Tell me what you want me to look for.",
    "quick.memory.search_empty_result": "I don't have anything saved about \"{query}\".",
    "quick.memory.search_prefs_header": "Saved preferences:",
    "quick.memory.search_facts_header": "Other things I remember:",
    "quick.memory.forget_empty": "Tell me what you want me to forget.",
    "quick.memory.forget_none": "I couldn't find anything saved about \"{query}\".",
    "quick.memory.forget_ambiguous": (
        "There are {n} saved things that match — tell me which one more precisely:"
    ),
    "quick.memory.forget_failed": "I couldn't forget that.",
    "quick.memory.forgotten": "Forgotten: \"{content}\".",
    "pipeline.ack_mission": "Got it, I'm on it: {goal}. I'll tell you as soon as it's done.",
    # [A·VOZ-4] Background missions (conversation mode): ack + async report
    "conversation.acuse": "Alright, I'm on it. I'll let you know when it's done; keep talking if you like.",
    "conversation.report_done": "It's done: {outcome}",
    "conversation.report_failed": "I couldn't do what you asked: {outcome}",
    "conversation.report_error": "I hit a problem with that task and couldn't finish it.",
    "conversation.gate_pending": (
        "To continue with «{goal}» I need your permission for a sensitive step. "
        "It's waiting for you in Missions."
    ),
}

_FR: dict[str, str] = {
    "responder.stopped_no_steps": "J'ai arrêté la tâche avant de terminer une seule étape, comme demandé.",
    "responder.node_done_fallback": "fait",
    "responder.completed_header": "J'ai terminé {n} étape(s) de « {goal} » :",
    "responder.could_not_complete": "Je n'ai pas pu terminer : {items}",
    "responder.left_untried": "Et voici ce qui n'a pas été tenté : {items}",
    "responder.you_cancelled": "Vous avez annulé : {items}",
    "responder.no_progress": "Je n'ai pas pu avancer sur « {goal} ».",
    "responder.failed_with_reasons": "Je n'ai pas pu terminer « {goal} ». Échec : {reasons}",
    "responder.plan_step_permission_mark": " (nécessite votre accord)",
    "responder.limitations_note": "Attention : je n'ai pas pu utiliser {tools} — le résultat peut être incomplet à cause de ça.",
    "pipeline.model_unknown": (
        "Je n'ai aucun modèle configuré appelé « {name} ». "
        "Modèles disponibles en ce moment : {available}. "
        "Vous pouvez en connecter d'autres dans Paramètres → Fournisseurs IA."
    ),
    "pipeline.model_pinned_project": (
        "Fait. À partir de maintenant j'utiliserai {provider} ({model}) pour tout ce "
        "projet. Vous pouvez le retirer quand vous voulez dans Paramètres → Intelligence."
    ),
    "pipeline.model_no_project_bind": (
        "Je peux utiliser {provider} pour ce message, mais cette conversation n'est "
        "liée à aucun projet, donc je ne peux pas le fixer « pour tout le projet » "
        "depuis ici. Si vous voulez le fixer à un projet, dites-le-moi depuis ce "
        "projet ou dans Paramètres → Intelligence. Je l'utilise juste pour ce message ?"
    ),
    "pipeline.model_scope_unspecified": (
        "Voulez-vous que j'utilise {provider} ({model}) seulement pour cette demande, "
        "ou à partir de maintenant pour tout ? Dites-le-moi et je continue."
    ),
    "pipeline.model_scope_auto_task": (
        "J'utilise {provider} ({model}) pour cette demande (vous n'avez pas précisé si "
        "vous vouliez le fixer, et avec le mode Autonome activé je ne pose pas la "
        "question — si vous voulez le fixer pour tout le projet, dites-le explicitement)."
    ),
    "pipeline.internal_error_retry": "J'ai eu un problème interne en traitant cela. Réessayez.",
    "pipeline.generic_done": "Fait.",
    "pipeline.generic_could_not": "Je n'ai pas pu le terminer.",
    "pipeline.generic_problem": "J'ai eu un problème en traitant cela.",
    "pipeline.cannot_capability": (
        "Je ne peux pas faire cela complètement avec mes capacités actuelles : {reason}"
    ),
    "pipeline.plan_needs_approval": (
        "J'ai préparé un plan de {n} étape(s) pour « {goal} ». Comme cela touche "
        "quelque chose de sensible, j'ai besoin de votre accord avant de l'exécuter :"
        "\n\n{plan_summary}"
    ),
    "pipeline.waiting_confirmation": "J'ai commencé et j'attends votre confirmation pour une étape.",
    "pipeline.plan_discarded": "J'ai abandonné le plan, comme demandé. Je n'ai rien exécuté.",
    "pipeline.stream_stopped": "Vous l'avez arrêté avant qu'il ne se termine.",
    "pipeline.no_response": "(pas de réponse)",
    "pipeline.plan_gate_title": "Plan de {n} étape(s) : {goal}",
    "orchestrator.no_objectives": "Je n'ai identifié aucune tâche dans votre message.",
    "orchestrator.template_completed_header": "J'ai terminé :",
    "orchestrator.template_waiting_header": "En attente de votre approbation :",
    "orchestrator.template_failed_header": "Je n'ai pas pu terminer :",
    "orchestrator.template_nothing": "Je n'ai pu terminer aucune des tâches.",
    # ---- Fil d'activité en direct (progress.py) ----------------------------
    "act.reading": "Lecture de {obj}",
    "act.writing": "Écriture de {obj}",
    "act.listing": "Exploration de {obj}",
    "act.deleting": "Suppression de {obj}",
    "act.searching_web": "Recherche sur le web : {obj}",
    "act.browsing": "Ouverture de {obj}",
    "act.browser_acting": "Navigation : {obj}",
    "act.running": "Exécution de {obj}",
    "act.git": "Git : {obj}",
    "act.email_reading": "Consultation du courrier",
    "act.email_writing": "Rédaction d'un courriel à {obj}",
    "act.calendar": "Consultation de l'agenda",
    "act.memory_read": "Recherche en mémoire : {obj}",
    "act.memory_write": "Enregistrement en mémoire",
    "act.self_projects": "Consultation de tes projets",
    "act.self_agents": "Consultation de tes agents",
    "act.self_rules": "Consultation de tes automatisations",
    "act.self_read": "Consultation de {obj}",
    "act.self_write": "Travail sur Aithera : {obj}",
    "act.desktop": "Utilisation du bureau : {obj}",
    "act.downloading": "Téléchargement de {obj}",
    "act.generic": "{tool} : {obj}",
    "act.generic_noobj": "Utilisation de {tool}",
    "act.thinking": "Réflexion sur l'étape suivante",
    "act.planning": "Préparation d'un plan",
    "act.plan_ready": "Plan prêt : {n} étape(s)",
    "act.plan_none": "Pas de plan valide : je fais directement",
    "act.step": "Étape {i} sur {n} : {obj}",
    "act.step_done": "Étape {i} terminée",
    "act.step_failed": "Étape {i} en échec : {obj}",
    "act.asking_permission": "Je demande ta permission pour {obj}",
    "act.asking_user": "Je t'ai posé une question",
    "act.permission_granted": "Permission accordée",
    "act.permission_denied": "Sans permission : toujours sans {obj}",
    "act.failed": "Échec de {obj}, j'essaie autrement",
    "act.writing_answer": "Rédaction de la réponse",
    "status.analyzing": "analyse en cours",
    "status.planning": "planification en cours",
    "status.executing": "exécution en cours",
    "status.still_working": "toujours en cours",
    "orchestrator.status_multi": "ce sont {n} tâches : je les fais en même temps",
    "orchestrator.status_progress": "{done} sur {n} terminées",
    "quick.projects_header": "Tu as {n} projet(s) :",
    "quick.no_projects": "Tu n'as encore aucun projet. Donne-moi un nom et je le crée.",
    "quick.agents_header": "Tu as {n} agent(s) :",
    "quick.no_agents": "Tu n'as encore aucun agent. Je peux en créer un.",
    "quick.rules_header": "Tu as {n} règle(s) d'automatisation :",
    "quick.no_rules": "Tu n'as encore aucune règle d'automatisation.",
    "quick.tasks_header": "Tu as {n} tâche(s) ouvertes :",
    "quick.no_tasks": "Tu n'as aucune tâche ouverte pour le moment.",
    "grounding.no_tools_note": (
        "(Note : je n'ai exécuté aucun outil dans ce tour, donc ce qui précède "
        "vient de mes connaissances générales et je ne l'ai pas vérifié sur ton "
        "système. Dis-le-moi si tu veux que je le vérifie vraiment.)"
    ),
    "grounding.fabricated_note": (
        "⚠️ AVERTISSEMENT : je n'ai exécuté aucun outil dans ce tour, donc je "
        "n'ai PAS lu tes fichiers ni visité aucun site. Les données concrètes "
        "ci-dessus (listes, contenus, chiffres ou sources) sont une supposition "
        "de ma part et ne correspondent probablement PAS à la réalité. "
        "Redemande-le-moi et je vérifierai pour de vrai."
    ),
    "quick.enabled": "active",
    "quick.disabled": "inactive",
    # [PU10, doc 35] mini-chat de mémoire (sauvegarder/chercher/oublier, 0 LLM)
    "quick.memory.hint": (
        "Je n'ai pas reconnu ça comme une commande de mémoire. Essaie « garde "
        "que… », « que sais-tu de… ? » ou « oublie que… »."
    ),
    "quick.memory.unavailable": "La mémoire n'est pas disponible pour le moment.",
    "quick.memory.save_empty": "Dis-moi ce que tu veux que je garde.",
    "quick.memory.save_failed": "Je n'ai pas pu le garder.",
    "quick.memory.saved": "Gardé : « {content} ». J'en tiendrai compte désormais.",
    "quick.memory.search_empty": "Dis-moi ce que tu veux que je cherche.",
    "quick.memory.search_empty_result": "Je n'ai rien de gardé sur « {query} ».",
    "quick.memory.search_prefs_header": "Préférences enregistrées :",
    "quick.memory.search_facts_header": "Autres choses dont je me souviens :",
    "quick.memory.forget_empty": "Dis-moi ce que tu veux que j'oublie.",
    "quick.memory.forget_none": "Je n'ai rien trouvé de gardé sur « {query} ».",
    "quick.memory.forget_ambiguous": (
        "Il y a {n} choses gardées qui correspondent — précise laquelle :"
    ),
    "quick.memory.forget_failed": "Je n'ai pas pu l'oublier.",
    "quick.memory.forgotten": "Oublié : « {content} ».",
    "pipeline.ack_mission": "Compris, je m'en occupe : {goal}. Je te tiens au courant dès que c'est prêt.",
    # [A·VOZ-4] Missions en arrière-plan (mode conversation) : accusé + rapport async
    "conversation.acuse": "D'accord, je m'en occupe. Je te préviens quand c'est fait ; continue à parler si tu veux.",
    "conversation.report_done": "C'est fait : {outcome}",
    "conversation.report_failed": "Je n'ai pas pu faire ce que tu m'as demandé : {outcome}",
    "conversation.report_error": "J'ai rencontré un problème avec cette tâche et je n'ai pas pu la terminer.",
    "conversation.gate_pending": (
        "Pour continuer « {goal} », j'ai besoin de ta permission pour une étape sensible. "
        "Elle t'attend dans Missions."
    ),
}

_PT: dict[str, str] = {
    "responder.stopped_no_steps": "Parei a tarefa antes de concluir qualquer etapa, como pediu.",
    "responder.node_done_fallback": "feito",
    "responder.completed_header": "Concluí {n} etapa(s) de «{goal}»:",
    "responder.could_not_complete": "Não consegui concluir: {items}",
    "responder.left_untried": "E ficaram por tentar: {items}",
    "responder.you_cancelled": "Cancelou: {items}",
    "responder.no_progress": "Não consegui avançar com «{goal}».",
    "responder.failed_with_reasons": "Não consegui concluir «{goal}». Falhou: {reasons}",
    "responder.plan_step_permission_mark": " (precisa da sua autorização)",
    "responder.limitations_note": "Atenção: não consegui usar {tools} — o resultado pode estar incompleto por causa disso.",
    "pipeline.model_unknown": (
        "Não tenho nenhum modelo configurado chamado «{name}». "
        "Modelos disponíveis neste momento: {available}. "
        "Pode ligar mais em Definições → Fornecedores de IA."
    ),
    "pipeline.model_pinned_project": (
        "Feito. A partir de agora vou usar {provider} ({model}) para todo este "
        "projeto. Pode retirá-lo quando quiser em Definições → Inteligência."
    ),
    "pipeline.model_no_project_bind": (
        "Posso usar {provider} para esta mensagem, mas esta conversa não está "
        "ligada a nenhum projeto, por isso não posso fixá-lo «para todo o projeto» "
        "a partir daqui. Se quiser fixá-lo a um projeto, diga-me a partir desse "
        "projeto ou em Definições → Inteligência. Uso-o só para esta mensagem?"
    ),
    "pipeline.model_scope_unspecified": (
        "Quer que use {provider} ({model}) só para este pedido, ou a partir de "
        "agora para tudo? Diga-me e continuo."
    ),
    "pipeline.model_scope_auto_task": (
        "A usar {provider} ({model}) para este pedido (não disse se queria fixá-lo, "
        "e com o modo Autónomo ativo não pergunto — se quiser fixá-lo para todo o "
        "projeto, diga-o explicitamente)."
    ),
    "pipeline.internal_error_retry": "Tive um problema interno ao processar isso. Tente novamente.",
    "pipeline.generic_done": "Feito.",
    "pipeline.generic_could_not": "Não consegui concluí-lo.",
    "pipeline.generic_problem": "Tive um problema ao processar isso.",
    "pipeline.cannot_capability": (
        "Não consigo fazer isto por completo com as minhas capacidades atuais: {reason}"
    ),
    "pipeline.plan_needs_approval": (
        "Preparei um plano de {n} etapa(s) para «{goal}». Como envolve algo "
        "sensível, preciso da sua autorização antes de o executar:\n\n{plan_summary}"
    ),
    "pipeline.waiting_confirmation": "Comecei e estou à espera da sua confirmação para uma etapa.",
    "pipeline.plan_discarded": "Descartei o plano, como pediu. Não executei nada.",
    "pipeline.stream_stopped": "Parou-o antes de terminar.",
    "pipeline.no_response": "(sem resposta)",
    "pipeline.plan_gate_title": "Plano de {n} etapa(s): {goal}",
    "orchestrator.no_objectives": "Não identifiquei nenhuma tarefa na sua mensagem.",
    "orchestrator.template_completed_header": "Concluí:",
    "orchestrator.template_waiting_header": "À espera da sua aprovação:",
    "orchestrator.template_failed_header": "Não consegui concluir:",
    "orchestrator.template_nothing": "Não consegui concluir nenhuma das tarefas.",
    # ---- Rasto de atividade em direto (progress.py) ------------------------
    "act.reading": "A ler {obj}",
    "act.writing": "A escrever {obj}",
    "act.listing": "A explorar {obj}",
    "act.deleting": "A apagar {obj}",
    "act.searching_web": "A pesquisar na web: {obj}",
    "act.browsing": "A abrir {obj}",
    "act.browser_acting": "A navegar: {obj}",
    "act.running": "A executar {obj}",
    "act.git": "Git: {obj}",
    "act.email_reading": "A ver o correio",
    "act.email_writing": "A redigir um email para {obj}",
    "act.calendar": "A consultar o calendário",
    "act.memory_read": "A procurar na memória: {obj}",
    "act.memory_write": "A guardar na memória",
    "act.self_projects": "A consultar os teus projetos",
    "act.self_agents": "A consultar os teus agentes",
    "act.self_rules": "A consultar as tuas automatizações",
    "act.self_read": "A consultar {obj}",
    "act.self_write": "A trabalhar na Aithera: {obj}",
    "act.desktop": "A usar o ambiente de trabalho: {obj}",
    "act.downloading": "A descarregar {obj}",
    "act.generic": "{tool}: {obj}",
    "act.generic_noobj": "A usar {tool}",
    "act.thinking": "A pensar no passo seguinte",
    "act.planning": "A preparar um plano",
    "act.plan_ready": "Plano pronto: {n} passo(s)",
    "act.plan_none": "Sem plano válido: resolvo diretamente",
    "act.step": "Passo {i} de {n}: {obj}",
    "act.step_done": "Passo {i} concluído",
    "act.step_failed": "Passo {i} falhou: {obj}",
    "act.asking_permission": "A pedir-te permissão para {obj}",
    "act.asking_user": "Fiz-te uma pergunta",
    "act.permission_granted": "Permissão concedida",
    "act.permission_denied": "Sem permissão: continuo sem {obj}",
    "act.failed": "{obj} falhou, tento outra via",
    "act.writing_answer": "A escrever a resposta",
    "status.analyzing": "a analisar",
    "status.planning": "a planear",
    "status.executing": "a executar",
    "status.still_working": "ainda a trabalhar",
    "orchestrator.status_multi": "são {n} tarefas: vou fazê-las ao mesmo tempo",
    "orchestrator.status_progress": "{done} de {n} concluídas",
    "quick.projects_header": "Tens {n} projeto(s):",
    "quick.no_projects": "Ainda não tens nenhum projeto. Diz-me um nome e eu crio-o.",
    "quick.agents_header": "Tens {n} agente(s):",
    "quick.no_agents": "Ainda não tens nenhum agente. Posso criar um.",
    "quick.rules_header": "Tens {n} regra(s) de automatização:",
    "quick.no_rules": "Ainda não tens nenhuma regra de automatização.",
    "quick.tasks_header": "Tens {n} tarefa(s) abertas:",
    "quick.no_tasks": "Não tens tarefas abertas neste momento.",
    "grounding.no_tools_note": (
        "(Nota: neste turno não executei nenhuma ferramenta, por isso o acima "
        "vem do meu conhecimento geral e não o verifiquei no teu sistema. "
        "Diz-me se queres que o confirme a sério.)"
    ),
    "grounding.fabricated_note": (
        "⚠️ AVISO IMPORTANTE: neste turno não executei nenhuma ferramenta, por "
        "isso NÃO li os teus ficheiros nem visitei nenhum site. Os dados "
        "concretos acima (listagens, conteúdos, números ou fontes) são uma "
        "suposição minha e muito provavelmente NÃO correspondem à realidade. "
        "Pede-me outra vez e verifico a sério."
    ),
    "quick.enabled": "ativa",
    "quick.disabled": "inativa",
    # [PU10, doc 35] mini-chat de memória (guardar/procurar/esquecer, 0 LLM)
    "quick.memory.hint": (
        "Não reconheci isso como um comando de memória. Tenta «guarda que…», "
        "«que sabes sobre…?» ou «esquece que…»."
    ),
    "quick.memory.unavailable": "A memória não está disponível neste momento.",
    "quick.memory.save_empty": "Diz-me o que queres que eu guarde.",
    "quick.memory.save_failed": "Não consegui guardar isso.",
    "quick.memory.saved": "Guardado: «{content}». Vou ter isso em conta a partir de agora.",
    "quick.memory.search_empty": "Diz-me o que queres que eu procure.",
    "quick.memory.search_empty_result": "Não tenho nada guardado sobre «{query}».",
    "quick.memory.search_prefs_header": "Preferências guardadas:",
    "quick.memory.search_facts_header": "Outras coisas que me lembro:",
    "quick.memory.forget_empty": "Diz-me o que queres que eu esqueça.",
    "quick.memory.forget_none": "Não encontrei nada guardado sobre «{query}».",
    "quick.memory.forget_ambiguous": (
        "Há {n} coisas guardadas que correspondem — diz-me qual com mais detalhe:"
    ),
    "quick.memory.forget_failed": "Não consegui esquecer isso.",
    "quick.memory.forgotten": "Esquecido: «{content}».",
    "pipeline.ack_mission": "Entendido, vou tratar disso: {goal}. Digo-te assim que estiver pronto.",
    # conversation.* (A·VOZ-4) — faltaban en PT (hallado 2026-07-24 al validar paridad)
    "conversation.acuse": "Está bem, vou tratar disso. Aviso-te quando estiver; continua a falar se quiseres.",
    "conversation.report_done": "Já está: {outcome}",
    "conversation.report_failed": "Não consegui fazer o que pediste: {outcome}",
    "conversation.report_error": "Tive um problema com essa tarefa e não consegui terminá-la.",
    "conversation.gate_pending": (
        "Para continuar com «{goal}» preciso da tua autorização para um passo "
        "sensível. Está à espera em Missões."
    ),
}

_DICTS: dict[str, dict[str, str]] = {"es": _ES, "en": _EN, "fr": _FR, "pt": _PT}


def t(key: str, **vars_) -> str:
    """Traduce `key` al idioma de interfaz elegido (`Config.app_language`), con
    fallback a español si no hay idioma elegido, el idioma no tiene esa clave, o
    la clave no existe en absoluto (nunca lanza — un texto en español de más es
    preferible a romper la respuesta). Interpolación simple `{var}` con
    `str.format`, igual que el resto del catálogo (`_ES` son las plantillas)."""
    lang = ui_language() or "es"
    template = _DICTS.get(lang, {}).get(key) or _ES.get(key) or key
    try:
        return template.format(**vars_)
    except Exception:
        return template
