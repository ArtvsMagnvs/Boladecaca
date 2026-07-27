# app/orchestrator/consolidator.py — de N resultados a UNA respuesta (R2)
#
# El usuario mandó UN mensaje: merece UNA respuesta, no cinco informes sueltos.
# Aquí se funden los `outcome` de todas las misiones en un texto que además dice
# la verdad sobre lo que quedó a medias.
#
# HONESTIDAD (regla del bloque): la respuesta distingue explícitamente lo hecho,
# lo que espera aprobación y lo que falló. Un resumen que solo cuente lo bueno
# sería exactamente el "teatro" que este bloque existe para eliminar.
from __future__ import annotations

from app.core.logging_config import get_system_logger
from app.core.strings import t as _t
from app.orchestrator.contracts import OrchestrationRun

logger = get_system_logger("orchestrator.consolidator")

_SYSTEM_PROMPT = """Eres Aithera respondiendo al usuario. Te doy lo que ha pasado con cada
encargo de su mensaje y escribes UNA respuesta unificada, en primera persona.

Reglas:
- Cuenta lo que SÍ se hizo, con los datos concretos que aparecen en los resultados.
- Di claramente lo que quedó pendiente de su aprobación y lo que falló, sin adornarlo
  ni esconderlo al final de una frase larga.
- No inventes nada que no esté en los resultados. Si un resultado viene vacío, dilo.
- Texto plano, sin markdown, sin tablas, sin encabezados.
- Ve al grano: el usuario quiere saber en qué punto está todo, no leer un informe."""


async def consolidate(run: OrchestrationRun) -> str:
    """Redacta la respuesta final del run. Nunca lanza: si el modelo falla, cae a
    una plantilla determinista (mismo patrón que el responder del TIE en T4a y el
    summarizer del MOS en M3 — el usuario nunca se queda sin respuesta)."""
    if not run.objectives:
        return _t("orchestrator.no_objectives")

    # Un solo objetivo: su propio outcome YA es la respuesta redactada por el
    # responder del TIE. Resumir un resumen solo añadiría latencia y ruido.
    if len(run.objectives) == 1:
        unico = run.objectives[0]
        return unico.outcome or _plantilla(run)

    try:
        from app.mel import Capability, ExecutionRequest, complete as mel_complete

        # [I18N-10] Mismo patrón que responder._synthesize(): el idioma de
        # interfaz elegido (si lo hay) tiene prioridad; si no, se mantiene el
        # default histórico (español, el idioma del propio _SYSTEM_PROMPT).
        system = _SYSTEM_PROMPT
        try:
            from app.core.language import language_directive

            directive = language_directive()
            if directive:
                system = f"{_SYSTEM_PROMPT}\n\n{directive}"
        except Exception as e:
            logger.info(f"[consolidator] no se pudo resolver el idioma (uso el default): {e!r}")

        res = await mel_complete(ExecutionRequest(
            capability=Capability.SUMMARIZE,
            prompt=f"MENSAJE ORIGINAL:\n{run.user_message}\n\nRESULTADOS:\n{_detalle(run)}",
            system_prompt=system,
        ))
        if res.ok and res.text.strip():
            return res.text.strip()
        logger.info(f"[consolidator] el modelo no respondió, uso plantilla: {res.error}")
    except Exception as e:
        logger.error(f"[consolidator] excepción, uso plantilla: {type(e).__name__}: {e}")

    return _plantilla(run)


def _detalle(run: OrchestrationRun) -> str:
    """[I18N-10] Este texto se le PASA al LLM como parte del prompt (no es lo que
    lee el usuario), pero se traduce igual que el resultado final que sí ve —
    consistencia con lo que el modelo debe redactar en ese mismo idioma."""
    lineas = []
    for o in run.objectives:
        estado = {
            "done": _t("orchestrator.state_done"),
            "waiting": _t("orchestrator.state_waiting"),
            "failed": _t("orchestrator.state_failed"),
            "skipped": _t("orchestrator.state_skipped"),
            "cancelled": _t("orchestrator.state_cancelled"),
        }.get(o.state, o.state.upper())
        lineas.append(f"[{estado}] {o.goal}\n  Resultado: {o.outcome or o.error or '(sin resultado)'}")
    return "\n\n".join(lineas)


def _plantilla(run: OrchestrationRun) -> str:
    """Respuesta determinista, sin LLM. Fea pero cierta. [I18N-10] En el idioma
    de interfaz elegido — es texto de puro código, no pasa por ningún LLM."""
    hechos = [o for o in run.objectives if o.state == "done"]
    esperando = [o for o in run.objectives if o.state == "waiting"]
    mal = [o for o in run.objectives if o.state in ("failed", "skipped", "cancelled")]

    partes = []
    if hechos:
        partes.append(_t("orchestrator.template_completed_header") + "\n" + "\n".join(
            f"- {o.goal}" + (f"\n  {o.outcome[:400]}" if o.outcome else "") for o in hechos))
    if esperando:
        partes.append(_t("orchestrator.template_waiting_header") + "\n" + "\n".join(
            f"- {o.goal}" for o in esperando))
    if mal:
        partes.append(_t("orchestrator.template_failed_header") + "\n" + "\n".join(
            f"- {o.goal}" + (f" ({o.error})" if o.error else "") for o in mal))
    return "\n\n".join(partes) if partes else _t("orchestrator.template_nothing")
