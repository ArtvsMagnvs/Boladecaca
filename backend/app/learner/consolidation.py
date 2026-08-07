# backend/app/learner/consolidation.py — LA CONSOLIDACIÓN (V1.1 LC2, doc 41 §4.2)
#
# Aquí es donde el Learner deja de ser una tabla de procesos.
#
# LO QUE SUSTITUYE: hasta LC1, "esto merece ser una skill" lo decidía un umbral
# — tres misiones parecidas con `state="done"` y a la bandeja. Ese umbral es el
# que propuso convertir en procedimiento fijo ocho intentos FALLIDOS del mismo
# encargo (doc 41 §0). Contar repeticiones no es entender.
#
# LO QUE HACE: una vez por noche, un modelo (capacidad LEARN) lee lo que pasó
# —lo que salió bien Y lo que salió mal, con el veredicto del juez y su lección
# delante— y DECIDE: qué merece convertirse en un procedimiento, qué mejora uno
# que ya existe, qué propuestas son la misma cosa dicha de dos maneras, cuál hay
# que retirar porque la evidencia nueva la desmiente, qué carencia de
# configuración hay detrás de una racha de fallos, y qué ve pero no puede
# proponer (eso va al informe).
#
# LO QUE **NO** HACE: aplicar nada. La IA PROPONE, la máquina TRAMITA, el
# usuario DECIDE (doc 15 §3.3). Todo aterriza en la cuarentena por la escalera
# de siempre, peldaño a peldaño, y nada se activa sin que el usuario diga sí.
#
# SE APRENDE IGUAL DEL ACIERTO QUE DEL ERROR — y son cosas distintas:
#   · de lo que SIRVIÓ sale el procedimiento (cómo hacerlo bien otra vez);
#   · de lo que FALLÓ sale el patrón de error, la carencia del sistema y, si es
#     accionable, la propuesta de configuración. Un fallo entendido evita N
#     fallos futuros; ignorarlo los garantiza.
#
# EL GROUNDING (la única pieza mecánica, y la que impide el teatro): los pasos
# de una skill propuesta tienen que mencionar herramientas que de VERDAD se
# usaron en las misiones-evidencia. Si el modelo se los inventa, la propuesta se
# degrada a observación SIN pasos — se conserva la señal, se tira la fantasía.
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from app.core.config import settings
from app.learner import ladder
from app.learner.proposals import proposal_service

logger = logging.getLogger(__name__)

# Presupuesto: 1 llamada por noche en el caso normal (doc 41 §4.2: "1-3").
MAX_VERDICTS = 60          # cuántos veredictos recientes se le dan
MAX_OPEN = 25              # propuestas abiertas que ve
MAX_REJECTED = 15          # rechazos del usuario (la calibración)
MAX_DECISIONS = 12         # decisiones que se le aceptan por pasada


_SYSTEM = """Eres el sistema de aprendizaje de Aithera, un asistente personal
de IA. Una vez al día repasas lo que Aithera hizo y decides QUÉ SE APRENDE.

Te doy: misiones ya juzgadas (con veredicto y lección), las propuestas que
esperan decisión del usuario, las que el usuario YA RECHAZÓ con su motivo, y el
catálogo de habilidades que Aithera ya tiene.

APRENDE DE LAS DOS CARAS:
- De lo que SIRVIÓ: si el mismo trabajo salió bien varias veces y el camino es
  repetible, propón convertirlo en un procedimiento. Los pasos SALEN DE LO QUE
  DE VERDAD SE HIZO (te doy las herramientas usadas en cada misión): no
  inventes pasos ni herramientas que no aparezcan.
- De lo que FALLÓ: di qué falló y POR QUÉ, y si se puede arreglar. Si a Aithera
  le falta una configuración, una herramienta o una capacidad, dilo. Si una
  propuesta abierta se apoya en misiones que ahora resultan haber fallado,
  RETÍRALA.

CALIBRA CON LOS RECHAZOS: si el usuario ya dijo que no a algo parecido, y su
motivo sigue aplicando, no lo vuelvas a proponer. Su "no" es información.

SÉ EXIGENTE. Es mucho mejor no proponer nada que llenar la bandeja de ruido:
cada propuesta le cuesta atención a una persona. Una petición repetida porque
FALLABA no es una costumbre — no la conviertas en procedimiento.

Responde SOLO con este JSON, sin texto alrededor:
{"decisions": [
  {"action": "create_skill",
   "name": "nombre corto en imperativo",
   "description": "para qué sirve, una frase",
   "steps": ["paso 1", "paso 2"],
   "tools": ["las herramientas que aparecen en las misiones-evidencia"],
   "mission_ids": ["ids de las misiones que lo sostienen"],
   "why": "por qué merece la pena"},

  {"action": "improve_skill", "skill_id": "...", "change": "qué cambiar",
   "mission_ids": ["..."], "why": "..."},

  {"action": "merge_candidates", "proposal_ids": ["...", "..."],
   "why": "son lo mismo dicho distinto"},

  {"action": "drop_candidate", "proposal_id": "...",
   "why": "la evidencia nueva la desmiente"},

  {"action": "config_fix", "title": "qué le falta a Aithera",
   "detail": "qué tiene que hacer el usuario", "why": "..."},

  {"action": "finding", "text": "lo que ves y no puedes proponer"}
]}

Si no hay nada que aprender esta noche, responde {"decisions": []}. Es una
respuesta perfectamente buena y la más común."""


# ---------------------------------------------------------------------------
# La entrada: qué ve la IA
# ---------------------------------------------------------------------------
def _verdicts_recientes(limite: int = MAX_VERDICTS) -> list[dict]:
    """Los veredictos de trabajo REAL, los buenos y los malos.

    `origin=user` es la barrera contra aprender del propio banco de pruebas
    (doc 41 §6), y `superseded_by is None` deja fuera los re-juzgados: cuenta
    el veredicto vigente, no su historia."""
    from app.core import corpus
    from app.db.database import SessionLocal
    from app.learner.models import MissionVerdict

    with SessionLocal() as s:
        filas = (s.query(MissionVerdict)
                 .filter(MissionVerdict.origin == corpus.USER,
                         MissionVerdict.superseded_by.is_(None))
                 .order_by(MissionVerdict.created_at.desc())
                 .limit(limite).all())
        out = []
        for f in filas:
            senales = f.signals if isinstance(f.signals, dict) else {}
            # Las herramientas que de VERDAD se usaron: son las que el
            # grounding comprobará después contra los pasos propuestos.
            tools: set = set()
            for n in (senales.get("nodes") or []):
                for t in (n.get("tools_used") or []):
                    if t:
                        tools.add(str(t))
            out.append({
                "mission_id": f.mission_id,
                "goal": (senales.get("goal") or "")[:300],
                "verdict": f.verdict,
                "confidence": round(float(f.confidence or 0), 2),
                "reasons": (f.reasons or "")[:400],
                "lesson": f.lesson if isinstance(f.lesson, dict) else None,
                "tools_used": sorted(tools),
                "project_id": senales.get("project_id"),
                "failures": [
                    {"kind": p.get("failure_kind"), "blame": p.get("blame"),
                     "reason": (p.get("reason") or "")[:160]}
                    for p in (senales.get("execution", {}).get("problems") or [])
                ][:4],
            })
        return out


async def _entrada() -> dict:
    """Todo lo que la IA necesita ver, en una estructura."""
    veredictos = await asyncio.to_thread(_verdicts_recientes)
    abiertas = await proposal_service.pending()
    rechazadas = await proposal_service.decided(limit=60)

    from app.learner.library import skill_library

    catalogo = await asyncio.to_thread(skill_library.list_compact)

    sirvieron = [v for v in veredictos if v["verdict"] in ("served", "partial")]
    fallaron = [v for v in veredictos if v["verdict"] == "failed"]

    return {
        # El pre-agrupador Jaccard es una PISTA, no una decisión: agrupa lo que
        # se parece para que la IA no tenga que descubrirlo, y ella decide si
        # el grupo es de verdad el mismo trabajo.
        "trabajos_que_funcionaron": _pre_agrupa(sirvieron),
        "misiones_que_fallaron": fallaron[:20],
        "propuestas_esperando_decision": [
            {"id": p["id"], "kind": p["kind"], "title": p["title"],
             "state": p["state"], "evidencias": len(p.get("evidence") or [])}
            for p in abiertas[:MAX_OPEN]
        ],
        "el_usuario_ya_rechazo": [
            {"title": p["title"], "motivo": (p.get("decision_note") or "")[:200]}
            for p in rechazadas
            if p.get("state") == "rejected"
        ][:MAX_REJECTED],
        "habilidades_que_ya_existen": catalogo,
    }


def _pre_agrupa(veredictos: list[dict]) -> list[dict]:
    """Jaccard sobre palabras de contenido — DEGRADADO a pre-agrupador.

    Hasta LC1 esta comparación DECIDÍA (tres parecidas → propuesta). Ahora solo
    sugiere: junta lo que se parece y se lo pone delante a la IA con las
    herramientas de cada misión, que es lo que ella necesita para juzgar si es
    el mismo trabajo o dos cosas que suenan igual."""
    from app.learner.mission_learning import (
        SIMILARITY_THRESHOLD, content_words, similarity,
    )

    grupos: list[list[dict]] = []
    for v in veredictos:
        palabras = content_words(v["goal"])
        if not palabras:
            continue
        for g in grupos:
            if similarity(palabras, content_words(g[0]["goal"])) >= SIMILARITY_THRESHOLD:
                g.append(v)
                break
        else:
            grupos.append([v])

    salida = []
    for g in sorted(grupos, key=len, reverse=True)[:12]:
        tools: set = set()
        for v in g:
            tools.update(v["tools_used"])
        salida.append({
            "ejemplo": g[0]["goal"],
            "veces": len(g),
            "mission_ids": [v["mission_id"] for v in g],
            "herramientas_usadas": sorted(tools),
            "lecciones": [v["lesson"]["content"] for v in g
                          if v.get("lesson") and v["lesson"].get("content")][:3],
        })
    return salida


# ---------------------------------------------------------------------------
# El grounding: los pasos no se inventan
# ---------------------------------------------------------------------------
def check_steps_grounded(steps: list, tools_declaradas: list,
                         tools_observadas: set,
                         vocabulario: Optional[set] = None) -> tuple[bool, str]:
    """¿Los pasos propuestos se apoyan en lo que de verdad se hizo?

    Determinista y en la dirección segura, como todo el grounding de este
    proyecto: las herramientas que la propuesta declara (y las que sus pasos
    nombran) tienen que estar entre las que las misiones-evidencia usaron DE
    VERDAD. Si no, no se tira la señal — se degrada a observación SIN pasos:
    "esto se repite" sigue siendo cierto; "y se hace así" deja de constar.

    `vocabulario` es el conjunto de nombres de herramienta que el Learner ha
    OBSERVADO en el conjunto de misiones que está repasando. Se pasa desde
    fuera a propósito y no se lee del ToolManager: el Learner no importa
    `app.tools` — observa, no ejecuta, y esa frontera la vigila el contrato de
    producto nº 4 (que es justo quien cazó el primer intento de escribir esto).
    La consecuencia práctica es incluso mejor: se compara contra lo que se ha
    visto usar, no contra lo que existe en el catálogo.

    Devuelve (está_anclado, motivo)."""
    if not tools_observadas:
        return False, "ninguna herramienta observada en las misiones-evidencia"

    declaradas = {str(t).strip().lower() for t in (tools_declaradas or []) if str(t).strip()}
    observadas = {str(t).strip().lower() for t in tools_observadas}
    fuera = declaradas - observadas
    if fuera:
        return False, ("herramientas que no se usaron en las misiones: "
                       + ", ".join(sorted(fuera)))

    # Y las que los PASOS nombran: un paso puede citar una tool sin declararla.
    texto = " ".join(str(p).lower() for p in (steps or []))
    conocidas = {str(t).strip().lower() for t in (vocabulario or set())}
    nombradas = {t for t in conocidas if t and t in texto}
    inventadas = nombradas - observadas
    if inventadas:
        return False, ("los pasos nombran herramientas que no se usaron: "
                       + ", ".join(sorted(inventadas)))
    return True, "pasos anclados en las herramientas realmente usadas"


# ---------------------------------------------------------------------------
# La llamada
# ---------------------------------------------------------------------------
async def _pregunta(entrada: dict) -> Optional[dict]:
    import app.mel as mel

    peticion = mel.ExecutionRequest(
        capability=mel.Capability.LEARN,
        prompt=("Esto es lo que Aithera hizo últimamente. Decide qué se aprende:\n\n"
                + json.dumps(entrada, ensure_ascii=False, indent=1,
                             default=str)[:16000]),
        system_prompt=_SYSTEM,
    )
    try:
        res = await asyncio.wait_for(
            mel.complete(peticion),
            timeout=float(getattr(settings, "LEARNER_JUDGE_BUDGET_S", 180.0)))
    except asyncio.TimeoutError:
        logger.info("[learner/consolidación] agotó su plazo — esta noche no se aprende")
        return None
    except Exception as e:
        logger.info(f"[learner/consolidación] falló ({e!r}) — esta noche no se aprende")
        return None
    if not getattr(res, "ok", False):
        return None
    try:
        from app.tie import extract_json

        data = extract_json(res.text or "")
    except Exception:
        data = None
    return data if isinstance(data, dict) else None


# ---------------------------------------------------------------------------
# La tramitación: lo mecánico aplica lo que la IA decidió
# ---------------------------------------------------------------------------
async def _crear_skill(d: dict, por_mision: dict,
                       vocabulario: Optional[set] = None) -> Optional[str]:
    nombre = str(d.get("name") or "").strip()
    if not nombre:
        return None
    ids = [str(x) for x in (d.get("mission_ids") or []) if str(x) in por_mision]
    if len(set(ids)) < ladder.MIN_REP:
        # La regla de "una racha no es un patrón" (doc 15 §3.3) no la decide la
        # IA: es política del sistema y se comprueba aquí.
        logger.info(f"[learner/consolidación] «{nombre}» descartada: "
                    f"{len(set(ids))} misión(es) de {ladder.MIN_REP}")
        return None

    observadas: set = set()
    for mid in ids:
        observadas.update(por_mision[mid]["tools_used"])

    pasos = [str(p).strip() for p in (d.get("steps") or []) if str(p).strip()]
    anclado, motivo = check_steps_grounded(pasos, d.get("tools") or [], observadas,
                                           vocabulario)
    if not anclado:
        logger.info(f"[learner/consolidación] «{nombre}» sin pasos: {motivo}")
        pasos = []

    pid = await proposal_service.create(
        kind="skill_new", risk="medium", state="observed",
        title=f"Procedimiento: {nombre}",
        summary=(str(d.get("why") or "").strip()
                 or "Este trabajo se ha hecho bien varias veces."),
        payload={"name": nombre,
                 "description": str(d.get("description") or "")[:280],
                 "definition": {"steps": pasos},
                 "tools": sorted(observadas),
                 "grounded": anclado,
                 "grounding_note": motivo,
                 "created_by": "consolidation"},
        project_id=None)

    # Una evidencia por misión JUZGADA ÚTIL. `context_key` = mission_id, así
    # que la protección contra rachas de L1 aplica sola.
    for mid in dict.fromkeys(ids):
        v = por_mision[mid]
        await proposal_service.add_evidence(pid, {
            "kind": "judged_success",
            "context_key": mid,
            "payload": {"goal": v["goal"][:200], "project_id": v.get("project_id"),
                        "verdict": v["verdict"], "confidence": v["confidence"]},
        })
    return pid


async def _mejorar_skill(d: dict, por_mision: dict) -> Optional[str]:
    """[LC3, petición directa del usuario] Una "mejora" no se propone solo
    porque la IA lo sugiera: antes se COMPARA con la versión actual — se
    generan las respuestas que daría un agente guiado por cada versión ante
    tareas REALES de las misiones-evidencia, y un juez independiente decide
    si hay una mejora clara y consistente. Sin eso, no se propone: "incumbente
    que gana = sin propuesta" (mismo criterio que SE1, doc 27 §6, en su forma
    segura de texto-contra-texto, sin ejecutar nada).

    Si la comparación no se pudo hacer (sin tareas de ejemplo, MEL caído), la
    propuesta SÍ se crea pero marcada `verified=False`: no proponer nada
    porque el sistema de pruebas estaba ocupado sería peor que ser honesto
    sobre no haber podido comprobarlo — el usuario decide con esa información
    delante, nunca a ciegas y nunca engañado."""
    sid = str(d.get("skill_id") or "").strip()
    cambio = str(d.get("change") or "").strip()
    if not sid or not cambio:
        return None
    from app.learner.library import skill_library

    skill = await skill_library.get(sid)
    if skill is None:
        return None

    ids = [str(x) for x in (d.get("mission_ids") or []) if str(x) in por_mision][:6]
    tareas = [por_mision[mid]["goal"] for mid in dict.fromkeys(ids) if por_mision[mid].get("goal")]

    comparacion = None
    try:
        from app.learner import comparison

        comparacion = await comparison.compare_skill_change(
            skill_name=skill.name, current_description=skill.description,
            proposed_change=cambio, sample_tasks=tareas)
    except Exception as e:
        logger.info(f"[learner/consolidación] comparación de «{skill.name}» falló: {e!r}")
        comparacion = None

    if comparacion is not None and not comparacion.get("improved"):
        logger.info(f"[learner/consolidación] «Mejorar: {skill.name}» descartada: "
                    f"la comparación no encontró una mejora real "
                    f"({comparacion.get('verdict', '')[:120]})")
        return None

    payload = {"skill_id": sid, "change": cambio[:600],
              "mission_ids": ids, "created_by": "consolidation",
              "current_description": skill.description,
              "verified": comparacion is not None,
              "comparison": comparacion}
    return await proposal_service.create(
        kind="skill_improve", risk="medium", state="observed",
        title=f"Mejorar: {skill.name}",
        summary=str(d.get("why") or "")[:400],
        payload=payload,
        subject_id=sid)


async def _fusionar(d: dict) -> int:
    """Dos propuestas que son lo mismo: se conserva la que más evidencia tiene
    y las otras se cierran con nota. Nunca se borra nada — `rejected` con
    motivo es auditable; un DELETE no."""
    ids = [str(x) for x in (d.get("proposal_ids") or [])]
    if len(ids) < 2:
        return 0
    filas = [p for p in [await proposal_service.get(i) for i in ids] if p]
    if len(filas) < 2:
        return 0
    ganadora = max(filas, key=lambda p: len(p.get("evidence") or []))
    n = 0
    for p in filas:
        if p["id"] == ganadora["id"]:
            continue
        for ev in (p.get("evidence") or []):
            try:
                await proposal_service.add_evidence(ganadora["id"], ev)
            except Exception:
                pass                 # una evidencia repetida o inválida no importa
        try:
            await proposal_service.reject(
                p["id"], note=f"fusionada con «{ganadora['title']}» — "
                              f"{str(d.get('why') or 'son el mismo trabajo')[:160]}")
            n += 1
        except Exception as e:
            logger.info(f"[learner/consolidación] no se pudo fusionar {p['id']}: {e!r}")
    return n


async def _retirar(d: dict) -> bool:
    pid = str(d.get("proposal_id") or "").strip()
    if not pid:
        return False
    try:
        await proposal_service.reject(
            pid, note=str(d.get("why") or "la evidencia nueva la desmiente")[:200])
        return True
    except Exception as e:
        logger.info(f"[learner/consolidación] no se pudo retirar {pid}: {e!r}")
        return False


async def _config_fix(d: dict) -> Optional[str]:
    """Lo que se aprende de los FALLOS y sí se puede accionar. Sin applier a
    propósito (igual que el `config_fix` determinista de L2b): configurar es
    del usuario, y la escalera lo hace imposible por construcción."""
    titulo = str(d.get("title") or "").strip()
    if not titulo:
        return None
    return await proposal_service.create(
        kind="config_fix", risk="low", state="proposed",
        title=titulo[:200],
        summary=str(d.get("detail") or d.get("why") or "")[:400],
        payload={"detail": str(d.get("detail") or "")[:600],
                 "why": str(d.get("why") or "")[:400],
                 "created_by": "consolidation"})


async def consolidate() -> dict:
    """La pasada nocturna. Nunca lanza: si la IA no está disponible, esta noche
    simplemente no se aprende — y mañana los veredictos siguen ahí."""
    resumen = {"created": [], "improved": [], "merged": 0, "dropped": 0,
               "config": [], "findings": []}
    try:
        entrada = await _entrada()
    except Exception as e:
        logger.error(f"[learner/consolidación] no se pudo reunir la entrada: {e!r}")
        return resumen

    if not entrada["trabajos_que_funcionaron"] and not entrada["misiones_que_fallaron"]:
        logger.info("[learner/consolidación] nada juzgado que repasar")
        return resumen

    data = await _pregunta(entrada)
    if not data or not isinstance(data.get("decisions"), list):
        return resumen

    # Índice por misión para el grounding: qué herramientas se usaron de verdad.
    # `vocabulario` es la unión — el repertorio de nombres de herramienta que el
    # Learner ha VISTO usar en esta tanda. Es contra eso, y no contra el
    # catálogo del ToolManager, contra lo que se comprueba si un paso nombra
    # algo que en estas misiones no pasó (el Learner no importa `app.tools`).
    por_mision: dict = {}
    vocabulario: set = set()
    for g in entrada["trabajos_que_funcionaron"]:
        vocabulario.update(g["herramientas_usadas"])
        for mid in g["mission_ids"]:
            por_mision[mid] = {"goal": g["ejemplo"], "tools_used": g["herramientas_usadas"],
                               "verdict": "served", "confidence": 1.0,
                               "project_id": None}
    for v in entrada["misiones_que_fallaron"]:
        vocabulario.update(v.get("tools_used") or [])

    for d in data["decisions"][:MAX_DECISIONS]:
        if not isinstance(d, dict):
            continue
        accion = str(d.get("action") or "")
        try:
            if accion == "create_skill":
                pid = await _crear_skill(d, por_mision, vocabulario)
                if pid:
                    resumen["created"].append(pid)
            elif accion == "improve_skill":
                pid = await _mejorar_skill(d, por_mision)
                if pid:
                    resumen["improved"].append(pid)
            elif accion == "merge_candidates":
                resumen["merged"] += await _fusionar(d)
            elif accion == "drop_candidate":
                resumen["dropped"] += 1 if await _retirar(d) else 0
            elif accion == "config_fix":
                pid = await _config_fix(d)
                if pid:
                    resumen["config"].append(pid)
            elif accion == "finding":
                texto = str(d.get("text") or "").strip()
                if texto:
                    resumen["findings"].append(texto[:400])
        except Exception as e:      # una decisión rota no cancela las demás
            logger.info(f"[learner/consolidación] decisión «{accion}» descartada: {e!r}")

    logger.info(f"[learner/consolidación] {resumen}")
    return resumen
