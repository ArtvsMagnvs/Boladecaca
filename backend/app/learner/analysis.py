# app/learner/analysis.py — LLL: el análisis en BATCH (V1.1 L3, doc 09 §2.2)
#
# LA DIFERENCIA CON L2, que es lo que justifica que exista este archivo:
# `mission_learning` mira UNA misión en el momento en que termina y solo puede
# ver lo obvio. Esto mira SEMANAS de misiones a la vez, de madrugada y sin
# prisa, y ve lo que ninguna misión suelta puede enseñar: que un mismo encargo
# se repite, que un fallo lleva un mes ocurriendo, que un procedimiento sirve en
# dos proyectos distintos.
#
# LOS CINCO ANÁLISIS del doc 09 §2.2, y qué hace cada uno con los datos que de
# verdad hay hoy:
#   1. Tareas repetidas  → propuesta `skill_new` (complementa la acumulación de
#      L2: aquí se cazan las repeticiones que el momento no vio).
#   2. Patrones de error → sobre `failure_stats` YA ATRIBUIDA (L2b). Lo
#      accionable (configuración) se propone; lo demás va al informe.
#   3. Inter-proyecto    → el mismo trabajo en ≥2 proyectos: la skill candidata
#      deja de ser de un proyecto.
#   4. Calidad de skills → recálculo determinista de quality_score/error_rate.
#   5. Informe semanal   → lo aprendido, en una frase, más la AUTOPSIA: la única
#      llamada al LLM de todo este archivo, con el modelo más fiable, 1 vez por
#      semana.
#
# DISCIPLINA (doc 09 §2.3): micro-batch, prioridad idle, nada en el camino
# caliente. Ningún análisis lanza jamás: un fallo aquí se loguea y el resto
# sigue — perder una pasada nocturna de aprendizaje no puede costarle nada al
# usuario.
#
# LA FRONTERA CON V1.2, para que no se solape con lo que viene: proponer
# MEJORAS de skills (improve/merge/split) es ML2, y proponer mejoras del
# SISTEMA es ML3. L3 puede VER cosas que no puede proponer todavía; esas van al
# informe como hallazgo, nunca a la bandeja como propuesta.
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional

from app.core.logging_config import get_system_logger
from app.learner import ladder
from app.learner.mission_learning import same_work
from app.learner.proposals import proposal_service

logger = get_system_logger("learner.analysis")

# Micro-batch (doc 09 §2.3): un techo por pasada para que una noche con mucho
# acumulado no monopolice la CPU. Lo que no entre hoy entra mañana.
MAX_BATCH = 50
MAX_MISSIONS = 200          # techo de lectura de trazas por pasada


# ---------------------------------------------------------------------------
# Análisis 1 — RETIRADO como decisor (V1.1 LC2, doc 41 §7)
# ---------------------------------------------------------------------------
# Lo que hacía: agrupar las misiones con `state="done"` por parecido de texto y,
# a las 3 parecidas, dejar una propuesta de skill en la bandeja.
#
# POR QUÉ SE RETIRA: `state="done"` significa "la maquinaria terminó sin
# colgarse", no "al usuario le sirvió". Con ese criterio, ocho peticiones
# seguidas de lo mismo —ocho porque ninguna funcionaba— se leían como una
# costumbre y se proponían como procedimiento fijo (doc 41 §0). Contar
# repeticiones no es entender.
#
# QUIÉN LO HACE AHORA: `consolidation.py`, con los VEREDICTOS del juez delante y
# aprendiendo también de lo que falló. La agrupación por parecido (Jaccard) no
# se tira: sobrevive DEGRADADA a pre-agrupador dentro de la consolidación —
# sugiere qué mirar junto, ya no decide.
#
# `_agrupa_por_trabajo` se conserva aquí porque el análisis inter-proyecto
# (LLL 3) lo sigue usando para lo que sí es: agrupar.


async def analyze_repeated_missions(days: int = 30) -> list[str]:
    """[RETIRADA en LC2] Se conserva la firma porque el barrel la exporta y el
    panel podría llamarla; no crea nada. La decisión vive en
    `consolidation.consolidate()`."""
    logger.info("[lll-1] retirada en LC2: decide la consolidación con veredictos")
    return []


def _misiones_recientes(days: int) -> list[dict]:
    """Lectura por el accesor PÚBLICO del TIE — el Learner nunca toca su SQL."""
    from app.tie import tracer

    return tracer.recent_missions(days=days, limit=MAX_MISSIONS, state="done")


def _agrupa_por_trabajo(misiones: list[dict]) -> list[list[dict]]:
    """Agrupación voraz por `same_work` (mismo criterio exacto que L2: mismas
    herramientas + objetivo parecido). Sin embeddings a propósito — esto corre
    de madrugada, pero sobre cientos de misiones un clustering semántico costaría
    minutos de GPU para distinguir lo que la comparación de conjuntos ya
    distingue. Los grupos salen ordenados por tamaño: lo más repetido primero."""
    grupos: list[list[dict]] = []
    for m in misiones:
        if not (m.get("goal") or "").strip():
            continue
        for g in grupos:
            if same_work(m["goal"], m.get("tools") or [],
                         g[0]["goal"], g[0].get("tools") or []):
                g.append(m)
                break
        else:
            grupos.append([m])
    return sorted(grupos, key=len, reverse=True)


async def _nueva_candidata(ejemplo: dict, grupo: list[dict]) -> str:
    """Nace en `observed` y SIN pasos: la plantilla de verdad la redacta el
    usuario al aceptarla, o ML2 al mejorarla (V1.2). Inventar aquí unos pasos
    con un LLM sería poner en la cuarentena algo que nadie ha visto funcionar —
    exactamente la fábrica de skills-basura que doc 15 §10 teme."""
    proyectos = sorted({m["project_id"] for m in grupo if m.get("project_id")})
    return await proposal_service.create(
        kind="skill_new", risk="medium", state="observed",
        title=f"Trabajo repetido: {(ejemplo['goal'] or '')[:80]}",
        summary=(f"Esto se ha hecho {len(grupo)} veces con las mismas "
                 f"herramientas. Podría ser un procedimiento fijo."),
        payload={"name": (ejemplo["goal"] or "")[:60],
                 "description": (ejemplo["goal"] or "")[:280],
                 "definition": {"steps": []},
                 "tools": list(ejemplo.get("tools") or []),
                 "projects": proyectos,
                 "created_by": "local_learning_loop",
                 "source": "lll_analisis_1"},
        project_id=None)


# ---------------------------------------------------------------------------
# Análisis 2 — patrones de error (sobre la atribución de L2b)
# ---------------------------------------------------------------------------
async def analyze_error_patterns() -> list[str]:
    """LLL análisis 2: qué lleva fallando, de quién es, y qué se puede hacer.

    Corre sobre `failure_stats` (L2b) y NO sobre `mem_error` en crudo: agrupar
    texto de errores sin atribución mezcla "se cayó la red" con "el modelo se
    rindió", y son dos patrones con dos salidas distintas.

    Devuelve los ids de las propuestas CREADAS — que son solo las de
    configuración. Lo demás (un modelo que falla mucho, una tool que se rompe,
    un bug nuestro que se repite) NO se convierte en propuesta: no hay nada que
    el usuario pueda aceptar ahí, y proponer arreglos del sistema es ML3
    (V1.2). Eso viaja al informe semanal como hallazgo, con su evidencia."""
    from app.learner.mission_learning import _propose_config_fixes

    try:
        return [] if not await _propose_config_fixes() else await _ids_config_abiertas()
    except Exception as e:
        logger.error(f"[lll-2] fallo analizando patrones de error: {e!r}")
        return []


async def _ids_config_abiertas() -> list[str]:
    return [p["id"] for p in await proposal_service.pending(kind="config_fix")]


def error_findings(min_count: int = 3) -> list[dict]:
    """Los patrones que L3 VE pero no puede proponer todavía. Alimentan el
    informe semanal (y, en V1.2, el Informe de Salud de ML3)."""
    from app.learner.stats import failure_summary

    try:
        resumen = failure_summary(min_count=min_count)
    except Exception as e:
        logger.info(f"[lll-2] sin resumen de fallos ({e!r})")
        return []
    return [it for it in resumen.get("items", [])
            if it.get("blame") not in ("config", "none")][:MAX_BATCH]


# ---------------------------------------------------------------------------
# Análisis 3 — el mismo trabajo en varios proyectos
# ---------------------------------------------------------------------------
async def analyze_cross_project() -> list[str]:
    """LLL análisis 3: si un trabajo candidato se ha hecho en ≥2 proyectos
    distintos, deja de ser cosa de un proyecto.

    Efecto real y acotado: se anota en el payload de la propuesta (`projects`,
    `cross_project=True`) y se le quita el `project_id`. No toca nada fuera de
    la cuarentena del Learner — cambiar el alcance de una SKILL ya consolidada
    sería una operación de evolución, y eso es ML2 (V1.2).

    NOTA HONESTA sobre los datos: el proyecto de cada misión viaja en la
    frontera de autoridad del plan (R4), así que solo hay señal para misiones
    lanzadas desde un agente o un proyecto. Las del chat general no la tienen —
    y para ellas este análisis, correctamente, no dice nada."""
    creadas: list[str] = []
    try:
        for p in await proposal_service.pending(kind="skill_new"):
            payload = p.get("payload") or {}
            proyectos = {
                (e or {}).get("payload", {}).get("project_id")
                for e in (p.get("evidence") or [])
            }
            proyectos.discard(None)
            if len(proyectos) < 2 or payload.get("cross_project"):
                continue
            nuevo = dict(payload)
            nuevo["projects"] = sorted(proyectos)
            nuevo["cross_project"] = True
            await proposal_service.update_payload(
                p["id"], nuevo, project_id=None,
                note=f"visto en {len(proyectos)} proyectos distintos")
            creadas.append(p["id"])
            logger.info(f"[lll-3] «{payload.get('name', '?')}» sirve en "
                        f"{len(proyectos)} proyectos: deja de ser de uno solo")
    except Exception as e:
        logger.error(f"[lll-3] fallo en el análisis inter-proyecto: {e!r}")
    return creadas


# ---------------------------------------------------------------------------
# Análisis 4 — calidad de las skills
# ---------------------------------------------------------------------------
# Pesos de `quality_score` (doc 15 §6.2: "éxitos ponderados por RECENCIA,
# feedback, cobertura de contextos"). Deterministas y a la vista: una nota de
# calidad que saliera de un LLM sería una opinión disfrazada de métrica.
_PESO_EXITO = 0.6           # cuánto pesa "funciona"
_PESO_COBERTURA = 0.25      # cuánto pesa "funciona en sitios distintos"
_PESO_USO = 0.15            # cuánto pesa "se usa de verdad"
_VIDA_MEDIA_DIAS = 30.0     # un éxito de hace un mes vale la mitad que el de hoy
_USO_PLENO = 10             # a partir de aquí, "se usa mucho" no suma más


async def recompute_skill_quality() -> int:
    """LLL análisis 4: recalcula `quality_score` y `error_rate` de cada skill
    desde su historial real (`skill_events`). Devuelve cuántas cambiaron.

    RECENCIA: un éxito de hace tres meses no dice lo mismo que el de ayer — el
    mundo cambia y una skill puede haberse quedado obsoleta sin fallar nunca.
    Se pondera con vida media de 30 días.

    En V1.1 casi todas las skills darán 0: `execute` todavía no está abierto
    (L1 lo dejó cerrado a propósito), así que no hay ejecuciones que puntuar.
    Eso NO es un problema del cálculo — es que aún no hay experiencia. El día
    que la haya, la fórmula ya está puesta y es la misma."""
    def _work() -> int:
        from app.db.database import SessionLocal
        from app.learner.models import Skill, SkillEvent

        ahora = datetime.utcnow()
        cambiadas = 0
        with SessionLocal() as s:
            for sk in s.query(Skill).limit(MAX_BATCH * 4).all():
                eventos = (s.query(SkillEvent)
                           .filter(SkillEvent.skill_id == sk.id,
                                   SkillEvent.event.in_(("executed_ok", "executed_fail")))
                           .all())
                q, err = _puntua(eventos, ahora)
                if abs((sk.quality_score or 0.0) - q) > 1e-6 or \
                        abs((sk.error_rate or 0.0) - err) > 1e-6:
                    sk.quality_score, sk.error_rate = q, err
                    cambiadas += 1
            s.commit()
        return cambiadas

    try:
        n = await asyncio.to_thread(_work)
        if n:
            logger.info(f"[lll-4] calidad recalculada en {n} skill(s)")
        return n
    except Exception as e:
        logger.error(f"[lll-4] fallo recalculando calidad: {e!r}")
        return 0


def _puntua(eventos: list, ahora: datetime) -> tuple[float, float]:
    """Función PURA sobre los eventos de una skill → (quality_score, error_rate).
    Separada para poder probarla sin BD."""
    if not eventos:
        return 0.0, 0.0
    peso_ok = peso_total = 0.0
    fallos = 0
    contextos: set = set()
    ultimo_exito: Optional[datetime] = None
    for e in eventos:
        creado = getattr(e, "created_at", None) or ahora
        dias = max((ahora - creado).total_seconds() / 86400.0, 0.0)
        peso = 0.5 ** (dias / _VIDA_MEDIA_DIAS)
        peso_total += peso
        if getattr(e, "event", "") == "executed_ok":
            peso_ok += peso
            if ultimo_exito is None or creado > ultimo_exito:
                ultimo_exito = creado
            ctx = (getattr(e, "payload", None) or {}).get("context_key")
            if ctx:
                contextos.add(ctx)
        else:
            fallos += 1

    # ¿FUNCIONA? — proporción de éxitos, con lo reciente pesando más que lo
    # viejo cuando se mezclan aciertos y fallos.
    exito = (peso_ok / peso_total) if peso_total else 0.0

    # ¿SIGUE VIGENTE? — HALLAZGO DE LOS TESTS: esto faltaba, y la proporción de
    # arriba SOLA no podía darlo. Con un único evento, `peso_ok` y `peso_total`
    # son el mismo número y el ratio vale 1.0 tenga la edad que tenga: el peso
    # por recencia se cancelaba consigo mismo y una skill de hace seis meses
    # puntuaba exactamente igual que la de hoy — justo lo contrario de lo que
    # esta función dice hacer. La frescura decae con el ÚLTIMO éxito, así que
    # una skill que dejó de usarse se apaga sola aunque nunca haya fallado
    # (que es la forma en que las skills se estropean de verdad: el mundo
    # cambia debajo y ellas ni se enteran).
    if ultimo_exito is None:
        frescura = 0.0
    else:
        dias = max((ahora - ultimo_exito).total_seconds() / 86400.0, 0.0)
        frescura = 0.5 ** (dias / _VIDA_MEDIA_DIAS)

    cobertura = min(len(contextos) / float(ladder.LOW_RISK_AUTO_N), 1.0)
    uso = min(len(eventos) / float(_USO_PLENO), 1.0)
    calidad = (_PESO_EXITO * exito * frescura
               + _PESO_COBERTURA * cobertura + _PESO_USO * uso)
    return round(calidad, 4), round(fallos / len(eventos), 4)


# ---------------------------------------------------------------------------
# Análisis 5 — el informe semanal (+ la autopsia, la única llamada al LLM)
# ---------------------------------------------------------------------------
_CLAVE_INFORME = "learner.weekly_report"
_CLAVE_ULTIMO = "learner.weekly_report_at"

_AUTOPSIA = """Eres el analista de un asistente personal. Te doy los fallos que ha
tenido esta semana, YA clasificados por tipo y por de quién fue la culpa.

Responde SOLO con un objeto JSON, sin texto alrededor y sin markdown:
{"findings": [{"title": "...", "why": "...", "evidence": ["id de misión", ...]}]}

Reglas:
- Como mucho 3 hallazgos, los más importantes. Si no hay nada relevante, lista vacía.
- "why" en una o dos frases, en lenguaje llano, sin jerga técnica.
- NO propongas cambiar código ni configuración: solo di QUÉ está pasando.
- No inventes: si un dato no está en la lista, no existe."""


async def weekly_learning_report(force: bool = False) -> dict:
    """LLL análisis 5: qué ha aprendido Aithera esta semana, en un objeto que el
    panel (L4) y el briefing leen sin recalcular nada.

    Incluye la AUTOPSIA: la ÚNICA llamada al LLM de todo el análisis, con el
    modelo más fiable (capacidad ANALYZE, política de calidad) una vez por
    semana. Aquí el coste sí se justifica — es un batch nocturno, no el camino
    caliente, y es justo donde un modelo bueno aporta lo que ninguna consulta
    puede: leer el conjunto. Si falla o tarda, el informe sale igual con la
    parte determinista, que es la mayor."""
    if not force and not _toca_informe():
        return _informe_guardado() or {}

    from app.learner.stats import failure_summary, model_ranking, tool_ranking

    def _cuenta() -> dict:
        from app.db.database import SessionLocal
        from app.learner.models import LearnerProposal, Skill, SkillEvent

        semana = datetime.utcnow() - timedelta(days=7)
        with SessionLocal() as s:
            return {
                "skills_nuevas": s.query(Skill).filter(Skill.created_at >= semana).count(),
                "propuestas_abiertas": s.query(LearnerProposal).filter(
                    LearnerProposal.state.in_(("observed", "candidate", "proposed",
                                               "validated"))).count(),
                "aceptadas": s.query(LearnerProposal).filter(
                    LearnerProposal.state == "consolidated",
                    LearnerProposal.decided_at >= semana).count(),
                "rechazadas": s.query(LearnerProposal).filter(
                    LearnerProposal.state == "rejected",
                    LearnerProposal.decided_at >= semana).count(),
                "eventos_de_skill": s.query(SkillEvent).filter(
                    SkillEvent.created_at >= semana).count(),
            }

    try:
        cifras = await asyncio.to_thread(_cuenta)
        fallos = await asyncio.to_thread(failure_summary)
        modelos = await asyncio.to_thread(model_ranking, None, 3)
        tools = await asyncio.to_thread(tool_ranking, 3)
    except Exception as e:
        logger.error(f"[lll-5] no se pudo reunir el informe: {e!r}")
        return {}

    informe = {
        "generated_at": datetime.utcnow().isoformat(),
        "counts": cifras,
        "failures_by_blame": fallos.get("by_blame", {}),
        "top_models": modelos[:3],
        "worst_tools": [t for t in tools if t["error_rate"] > 0][:3],
        "findings": await _autopsia(error_findings()),
        "headline": _titular(cifras, fallos.get("by_blame", {})),
    }
    await asyncio.to_thread(_guarda_informe, informe)
    logger.info(f"[lll-5] informe semanal: {informe['headline']}")
    return informe


def _titular(cifras: dict, culpas: dict) -> str:
    """La frase de una línea que va al briefing. Determinista: el titular no
    puede depender de que un modelo esté disponible."""
    partes = []
    if cifras.get("skills_nuevas"):
        partes.append(f"{cifras['skills_nuevas']} procedimiento(s) nuevo(s)")
    if cifras.get("propuestas_abiertas"):
        partes.append(f"{cifras['propuestas_abiertas']} propuesta(s) esperándote")
    ajenos = culpas.get("external", 0) + culpas.get("config", 0)
    if ajenos:
        partes.append(f"{ajenos} fallo(s) por causas ajenas o de configuración")
    return "Esta semana: " + (", ".join(partes) if partes
                              else "nada nuevo que contar todavía")


async def _autopsia(items: list[dict]) -> list[dict]:
    """Los hallazgos, mirados por el modelo más fiable. Sin fallos que analizar
    no se llama a nadie: pagar una llamada de calidad para que diga "todo bien"
    es justamente el reflection theater que doc 15 §10 avisa de evitar."""
    if not items:
        return []
    import app.mel as mel

    datos = [{"que": it["kind"], "donde": it["component"], "veces": it["count"],
              "misiones": (it.get("sample_mission_ids") or [])[:3],
              "ultimo_mensaje": (it.get("last_detail") or "")[:200]}
             for it in items[:12]]
    try:
        res = await asyncio.wait_for(
            mel.complete(mel.ExecutionRequest(
                capability=mel.Capability.ANALYZE,
                prompt="<datos>\n" + json.dumps(datos, ensure_ascii=False) + "\n</datos>",
                system_prompt=_AUTOPSIA,
                policy_override="quality")),
            timeout=120.0)
    except Exception as e:
        logger.info(f"[lll-5] autopsia no disponible ({e!r}) — informe sin hallazgos")
        return []
    if not getattr(res, "ok", False):
        return []
    try:
        from app.tie import extract_json

        data = extract_json(res.text or "") or {}
    except Exception:
        return []
    hallazgos = data.get("findings") if isinstance(data, dict) else None
    if not isinstance(hallazgos, list):
        return []
    # Un hallazgo SIN evidencia enlazada se descarta: sin misiones que mirar no
    # se puede comprobar, y un diagnóstico que no se puede comprobar no es un
    # diagnóstico (misma disciplina que el grounding).
    return [h for h in hallazgos[:3]
            if isinstance(h, dict) and h.get("title") and h.get("evidence")]


def _toca_informe() -> bool:
    """Semanal de verdad, no "los lunes": si la app estuvo apagada el lunes, el
    informe sale el primer día que se encienda. El calendario no manda sobre el
    aprendizaje."""
    ultimo = _config_get(_CLAVE_ULTIMO)
    if not ultimo:
        return True
    try:
        return datetime.utcnow() - datetime.fromisoformat(ultimo) >= timedelta(days=7)
    except Exception:
        return True


def _guarda_informe(informe: dict) -> None:
    _config_set(_CLAVE_INFORME, json.dumps(informe, ensure_ascii=False))
    _config_set(_CLAVE_ULTIMO, informe["generated_at"])


def _informe_guardado() -> Optional[dict]:
    crudo = _config_get(_CLAVE_INFORME)
    if not crudo:
        return None
    try:
        return json.loads(crudo)
    except Exception:
        return None


def last_report() -> Optional[dict]:
    """El último informe, para el panel y el briefing. Lectura pura."""
    return _informe_guardado()


def _config_get(clave: str) -> Optional[str]:
    from app.db.database import Config, SessionLocal

    try:
        with SessionLocal() as s:
            fila = s.query(Config).filter(Config.key == clave).first()
            return fila.value if fila else None
    except Exception:
        return None


def _config_set(clave: str, valor: str) -> None:
    from app.db.database import Config, SessionLocal

    try:
        with SessionLocal() as s:
            fila = s.query(Config).filter(Config.key == clave).first()
            if fila is None:
                s.add(Config(key=clave, value=valor))
            else:
                fila.value = valor
            s.commit()
    except Exception as e:
        logger.info(f"[lll] no se pudo guardar {clave} ({e!r})")


# ---------------------------------------------------------------------------
# El job nocturno
# ---------------------------------------------------------------------------
async def run_nightly_analysis() -> dict:
    """Una pasada completa. La llama el scheduler de madrugada (main.py) y el
    endpoint de "analizar ahora" del panel (L4).

    Orden deliberado: primero lo que CREA propuestas (1, 2), luego lo que las
    afina (3), luego la calidad (4), y el informe al final para que cuente lo
    que acaba de pasar. Cada paso está aislado — que uno falle no cancela los
    demás, porque son independientes y perder los cuatro por uno sería tonto."""
    resumen = {"consolidation": {}, "config": [], "cross_project": [],
               "quality": 0, "report": {}}
    # [V1.1 LC2] Lo PRIMERO es la consolidación: es quien decide qué se aprende,
    # leyendo los veredictos que el juez dejó a las 04:20. Sustituye al antiguo
    # análisis 1, que decidía contando repeticiones de `state="done"`.
    try:
        from app.learner.consolidation import consolidate

        resumen["consolidation"] = await consolidate()
    except Exception as e:
        logger.error(f"[lll] consolidación falló (se sigue): {e!r}")

    for clave, corutina in (("config", analyze_error_patterns()),
                            ("cross_project", analyze_cross_project())):
        try:
            resumen[clave] = await corutina
        except Exception as e:
            logger.error(f"[lll] {clave} falló (se sigue): {e!r}")
    try:
        resumen["quality"] = await recompute_skill_quality()
    except Exception as e:
        logger.error(f"[lll] calidad falló (se sigue): {e!r}")
    try:
        resumen["report"] = await weekly_learning_report()
    except Exception as e:
        logger.error(f"[lll] informe falló: {e!r}")
    return resumen


# [V1.1 L2 — IMPLEMENTADO] `learn_from_mission` vive en `mission_learning.py` y
# se re-exporta por el barrel. Se deja el puntero para que este archivo siga
# siendo el índice del análisis del Learner.
from app.learner.mission_learning import learn_from_mission  # noqa: F401,E402
