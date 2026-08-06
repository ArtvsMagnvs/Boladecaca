# app/api/endpoints/learner.py — la cara visible del Learner (V1.1 L4, doc 27 §5)
#
# Este router NO añade ni una línea de lógica de aprendizaje: la EXPONE. Todo lo
# que sirve ya existe y está probado — la cuarentena (L1), los contadores y la
# atribución (L2/L2b), el análisis y el informe (L3). Aquí solo se traduce a lo
# que el panel necesita, y se traduce a LENGUAJE LLANO: el usuario no tiene por
# qué saber qué es un `blame` ni una `escalera de confianza`.
#
# La frontera de doc 16, respetada: se importa `app.learner` (el barrel), jamás
# sus internos.
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.logging_config import get_system_logger
from app.learner import (
    failure_summary,
    last_report,
    model_ranking,
    proposal_service,
    registered_kinds,
    run_nightly_analysis,
    skill_library,
    tool_ranking,
)

logger = get_system_logger("api.learner")
router = APIRouter(prefix="/learner", tags=["learner"])


class DecisionIn(BaseModel):
    note: str = ""


# Cómo se llama cada tipo de propuesta cuando se lo cuentas a una persona. El
# `kind` técnico no sale nunca a la UI: sale esto.
_TITULOS = {
    "skill_new": "Procedimiento nuevo",
    "skill_improve": "Mejora de un procedimiento",
    "config_fix": "Falta configurar algo",
    "rule": "Automatización sugerida",
    "preference": "Preferencia observada",
}

# El riesgo, dicho como se le dice a alguien: qué implica, no qué etiqueta lleva.
_RIESGOS = {
    "low": "riesgo bajo",
    "medium": "riesgo medio",
    "high": "riesgo alto — siempre te preguntaré",
}


def _propuesta_out(p: dict) -> dict:
    """Una propuesta, lista para pintarse sin que el frontend tenga que saber
    nada del Learner."""
    kind = p.get("kind", "")
    payload = p.get("payload") or {}
    evidencias = p.get("evidence") or []
    # Las misiones donde se vio: el usuario puede ir a mirarlas él mismo. Una
    # propuesta sin forma de comprobarla es una propuesta que hay que creerse.
    misiones = [e.get("context_key") for e in evidencias if (e or {}).get("context_key")]
    return {
        "id": p["id"],
        "kind": kind,
        "kind_label": _TITULOS.get(kind, "Algo aprendido"),
        "title": p.get("title", ""),
        "summary": p.get("summary", ""),
        "state": p.get("state"),
        "risk": p.get("risk"),
        "risk_label": _RIESGOS.get(p.get("risk", ""), ""),
        "evidence_count": len(evidencias),
        "mission_ids": misiones[:10],
        "created_at": p.get("created_at"),
        "project_id": p.get("project_id"),
        # Lo que el panel necesita para saber QUÉ botón ofrecer:
        #  - sin applier registrado no hay nada que aplicar (config_fix), así que
        #    en vez de "Aceptar" se muestra "Ir a Ajustes". La garantía es del
        #    backend (L1); esto solo la refleja.
        "applicable": kind in registered_kinds(),
        "settings_tab": payload.get("settings_tab"),
        "steps": (payload.get("definition") or {}).get("steps") or [],
        "tools": payload.get("tools") or [],
    }


@router.get("/proposals")
async def list_proposals(kind: Optional[str] = None) -> dict:
    """Lo que espera al usuario. Ordenado por lo que ya está listo para
    decidirse: lo demás sigue acumulando evidencia y no le pide nada."""
    props = [_propuesta_out(p) for p in await proposal_service.pending(kind=kind)]
    orden = {"proposed": 0, "validated": 1, "candidate": 2, "observed": 3}
    props.sort(key=lambda p: (orden.get(p["state"], 9), p["created_at"] or ""))
    return {"proposals": props,
            "waiting_for_you": sum(1 for p in props
                                   if p["state"] in ("candidate", "proposed", "validated"))}


@router.post("/proposals/{proposal_id}/approve")
async def approve(proposal_id: str, body: DecisionIn) -> dict:
    """El usuario dice que sí. Sube el peldaño y consolida en el mismo gesto —
    para él es UNA decisión, no dos; la escalera sigue siendo la de siempre por
    dentro (nada nace validado, nada se aplica sin applier)."""
    try:
        prop = await proposal_service.get(proposal_id)
        if prop is None:
            raise HTTPException(status_code=404, detail="Esa propuesta ya no existe")
        if prop["state"] == "candidate":
            await proposal_service.promote_to_proposed(proposal_id)
        await proposal_service.approve(proposal_id, note=body.note)
        aplicada = await proposal_service.apply(proposal_id)
        return {"ok": True, "state": aplicada["state"]}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/proposals/{proposal_id}/reject")
async def reject(proposal_id: str, body: DecisionIn) -> dict:
    """El usuario dice que no — y el no SE REGISTRA con su motivo: el Learner
    aprende de los noes tanto como de los síes (doc 15 §8)."""
    try:
        await proposal_service.reject(proposal_id, note=body.note)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/proposals/{proposal_id}/undo")
async def undo(proposal_id: str) -> dict:
    """Arrepentirse. La promesa que hace usable todo lo demás: si algo se
    aprendió mal, se deshace — y deshacer deja su propio rastro, nunca borra."""
    try:
        await proposal_service.undo(proposal_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


# Cómo se le explica a una persona de quién fue cada fallo. Sin jerga y sin
# echar culpas donde no las hay.
_CULPAS = {
    "external": ("Servicios externos", "Conexión o servicios de terceros — no es "
                                       "culpa de Aithera ni de los modelos."),
    "config": ("Configuración pendiente", "Falta configurar algo. Suele arreglarse "
                                          "en dos clics."),
    "model": ("Modelos de IA", "El modelo se atascó o respondió en un formato que "
                               "no se pudo usar."),
    "tool": ("Herramientas", "Una herramienta falló por su cuenta."),
    "aithera": ("El propio sistema", "Un fallo de Aithera. Lo apunto para "
                                     "revisarlo."),
    "none": ("Decisiones tuyas", "Cosas que paraste o no autorizaste. No son "
                                 "averías."),
    "unknown": ("Sin atribuir", "No he sabido de quién era. Aparece aquí a "
                                "propósito en vez de esconderse."),
}


@router.get("/health")
async def health(min_count: int = Query(1, ge=1)) -> dict:
    """La pestaña "Salud": por qué fallan las cosas, quién va bien y qué está
    rompiéndose. Todo lectura — no dispara ningún análisis."""
    resumen = failure_summary(min_count=min_count)
    culpas = []
    for clave, n in sorted(resumen.get("by_blame", {}).items(),
                           key=lambda kv: kv[1], reverse=True):
        etiqueta, explicacion = _CULPAS.get(clave, (clave, ""))
        culpas.append({"blame": clave, "label": etiqueta,
                       "explanation": explicacion, "count": n})
    return {
        "total_failures": resumen.get("total", 0),
        "by_blame": culpas,
        "items": resumen.get("items", [])[:20],
        # `min_missions=2` para que un modelo con una sola misión afortunada no
        # encabece un ranking: una racha no es evidencia (misma disciplina que
        # la escalera).
        "models": model_ranking(min_missions=2)[:6],
        "tools": [t for t in tool_ranking(min_calls=2) if t["error_rate"] > 0][:6],
        "report": last_report() or {},
    }


@router.get("/history")
async def history(limit: int = Query(50, ge=1, le=200)) -> dict:
    """Lo que ya se decidió: qué se aceptó, qué se rechazó y con qué motivo, y
    el historial de cada skill. La memoria de las decisiones del usuario."""
    skills = await skill_library.list()
    return {
        "skills": [{
            "id": s.id, "name": s.name, "status": s.status.value,
            "created_by": s.created_by,
            # "lo pediste tú" vs "lo aprendí mirando" es información, no adorno.
            "taught_by_user": s.created_by == "user_taught",
            "quality_score": round(s.quality_score, 2),
            "error_rate": round(s.error_rate, 2),
            "use_count": s.use_count,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        } for s in skills[:limit]],
        "decided": [_propuesta_out(p) | {"decision_note": p.get("decision_note"),
                                         "decided_at": p.get("decided_at")}
                    for p in await proposal_service.decided(limit=limit)],
    }


@router.post("/analyze")
async def analyze_now() -> dict:
    """"Analizar ahora": la misma pasada que corre de madrugada, a petición.
    Existe porque esperar a mañana para ver si el Learner funciona es mala
    experiencia — y porque el usuario tiene derecho a mirar cuando quiera."""
    resumen = await run_nightly_analysis()
    return {
        "ok": True,
        "new_proposals": len(resumen.get("repeated", []) or []) +
                         len(resumen.get("config", []) or []),
        "skills_rescored": resumen.get("quality", 0),
        "report": resumen.get("report") or {},
    }
