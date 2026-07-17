# app/mel/capabilities.py — taxonomía + mapeo de call-sites (doc 19 §3)
#
# La taxonomía EN SÍ es el enum `Capability` (contracts.py). Este módulo aporta:
#   1. qué capacidades pide "modelo potente" (el resto → barato) — el reparto
#      mínimo de V1.0 (doc 19 §5.1); el aprendizaje real (v2) lo afina por uso.
#   2. el mapeo de los call-sites REALES de hoy a su capacidad — es DOCUMENTACIÓN
#      viva que la migración de E2 usa para saber qué pedir en cada sitio. En E1
#      no se migra nada; esta tabla es el contrato de esa migración.
from __future__ import annotations

from app.mel.contracts import Capability

# Capacidades que merecen "modelo potente" (doc 19 §5.1). El Rule Engine no lee
# esto directamente (las cadenas ya vienen compiladas por política), pero el
# compilador de políticas (policies.py) y el auto-catálogo (research.py, E1b) lo
# usan para saber dónde prima calidad sobre coste.
SMART_CAPABILITIES: frozenset[Capability] = frozenset({
    Capability.REASON,
    Capability.CODE,
    Capability.ANALYZE,
    Capability.RESEARCH,
})


def is_smart(capability: Capability) -> bool:
    return capability in SMART_CAPABILITIES


# Mapeo de los ~9 call-sites reales de Aithera a su capacidad (doc 19 §3, columna
# "call-sites reales hoy"). E2 migra cada uno de `ai_manager.chat(...)` a
# `mel.complete(ExecutionRequest(capability=...))`. NO se importa desde el hot
# path — es una tabla de referencia para la migración y para los tests de E2.
CALL_SITE_CAPABILITY: dict[str, Capability] = {
    "chat_service.answer": Capability.CHAT,             # chat Electron/Telegram + camino corto TIE
    "chat_service.stream": Capability.CHAT,
    "email.llm_triage": Capability.CLASSIFY,            # triaje etapa 2
    "email.extract_meeting_datetime": Capability.EXTRACT,
    "email.generate_ai_reply": Capability.DRAFT,
    "memory.summarizer": Capability.SUMMARIZE,          # resumen nocturno + briefing + digest
    "tie.intents.classify": Capability.CLASSIFY,        # Intent Classifier del TIE
    "tie.planner.plan": Capability.REASON,              # Planner del TIE
    "tie.responder.build": Capability.SUMMARIZE,        # Response Builder del TIE
}
