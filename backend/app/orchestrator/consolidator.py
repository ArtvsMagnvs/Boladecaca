# app/orchestrator/consolidator.py — de N resultados a UNA respuesta (R2)
#
# El usuario mandó UN mensaje: merece UNA respuesta, no cinco informes sueltos.
# Aquí se juntan los `outcome` de todas las misiones en un texto que además dice
# la verdad sobre lo que quedó a medias.
#
# HONESTIDAD (regla del bloque): la respuesta distingue explícitamente lo hecho,
# lo que espera aprobación y lo que falló. Un resumen que solo cuente lo bueno
# sería exactamente el "teatro" que este bloque existe para eliminar.
#
# [S2·S6, doc 34] AQUÍ YA NO HAY LLM. Antes, con N≥2 objetivos, esta capa
# reescribía con un modelo los `outcome` que el responder del TIE YA había
# redactado. Esa segunda pasada causó el peor fallo de honestidad registrado
# (25-jul): el email SE ENVIÓ —`tool_call` con `message_id`— y el texto que
# leyó el usuario decía "está preparado pero NO se ha enviado, necesito tu
# confirmación". El modelo vio la etiqueta "pide permiso" del plan en el
# detalle que se le pasaba y la interpretó como estado pendiente. El prompt ya
# decía "No inventes nada que no esté en los resultados": una instrucción no es
# una comprobación.
#
# La eliminación no inventa nada nuevo — el propio código YA reconocía que esta
# pasada no aporta con 1 objetivo (`return unico.outcome`). Se extiende a N lo
# que ya se hacía con 1. Menos código, menos latencia, cero oportunidades de
# reinterpretar un hecho.
from __future__ import annotations

from app.core.logging_config import get_system_logger
from app.core.strings import t as _t
from app.orchestrator.contracts import OrchestrationRun

logger = get_system_logger("orchestrator.consolidator")


async def consolidate(run: OrchestrationRun) -> str:
    """Redacta la respuesta final del run. Determinista: cero llamadas al
    modelo, en cualquier número de objetivos. Sigue siendo `async` porque es su
    contrato público con el conductor (y porque nada obliga a romperlo)."""
    if not run.objectives:
        return _t("orchestrator.no_objectives")

    # Un solo objetivo: su propio outcome YA es la respuesta redactada por el
    # responder del TIE. Nunca hubo LLM aquí; sigue igual.
    if len(run.objectives) == 1:
        unico = run.objectives[0]
        return unico.outcome or _plantilla(run)

    return _plantilla(run)


def _plantilla(run: OrchestrationRun) -> str:
    """La respuesta: los `outcome` que el responder ya redactó, agrupados por
    estado. [I18N-10] En el idioma de interfaz elegido — es texto de puro
    código, no pasa por ningún LLM."""
    hechos = [o for o in run.objectives if o.state == "done"]
    esperando = [o for o in run.objectives if o.state == "waiting"]
    mal = [o for o in run.objectives if o.state in ("failed", "skipped", "cancelled")]

    partes = []
    if hechos:
        partes.append(_t("orchestrator.template_completed_header") + "\n" + "\n".join(
            f"- {o.goal}" + (f"\n  {o.outcome[:1200]}" if o.outcome else "") for o in hechos))
    if esperando:
        partes.append(_t("orchestrator.template_waiting_header") + "\n" + "\n".join(
            f"- {o.goal}" + (f"\n  {o.outcome[:600]}" if o.outcome else "") for o in esperando))
    if mal:
        partes.append(_t("orchestrator.template_failed_header") + "\n" + "\n".join(
            f"- {o.goal}" + (f" ({o.error})" if o.error else "") for o in mal))
    return "\n\n".join(partes) if partes else _t("orchestrator.template_nothing")
