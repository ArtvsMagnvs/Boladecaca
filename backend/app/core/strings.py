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
