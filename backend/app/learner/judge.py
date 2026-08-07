# backend/app/learner/judge.py — EL JUEZ (V1.1 LC1, doc 41 §3)
#
# La pieza que faltaba. Un modelo (capacidad LEARN) lee cada misión terminada y
# dictamina si SIRVIÓ, con las señales duras y "el después" delante.
#
# POR QUÉ EXISTE (doc 41 §0): el aprendizaje usaba `orchestrator_traces.state`
# como señal de éxito. Ese campo significa "la maquinaria terminó sin
# colgarse" — un rechazo honesto del planner, una rendición y un "HOLA" lo
# cumplen igual que un trabajo bien hecho. Con ese criterio el Learner propuso
# convertir en procedimiento fijo ocho intentos FALLIDOS del mismo encargo.
#
# LAS TRES REGLAS QUE LO GOBIERNAN (doc 41 §5, anti-contaminación v2):
#   1. El juez NUNCA es el modelo que ejecutó la misión. Si no hay alternativa
#      apta, se juzga igual pero la fila queda marcada `judge_bias=True` —
#      marcado, nunca en silencio.
#   2. Todo veredicto cita señales del paquete. Un `served` que no cite ninguna,
#      o que cite señales inexistentes, se DEGRADA a `unclear`.
#   3. Lo mecánico solo puede QUITAR confianza, jamás ponerla: no existe ningún
#      camino por el que un `failed` se promocione a `served` sin el juez.
#
# Nada de esto toca el camino caliente: la cola vive en background y el lote
# nocturno corre a las 04:45 con el usuario durmiendo.
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Taxonomía CERRADA de veredictos (append-only, como MemoryType/NodeState).
SERVED = "served"       # le sirvió al usuario, y hay con qué sostenerlo
PARTIAL = "partial"     # algo útil salió, pero no todo lo pedido
FAILED = "failed"       # no sirvió
UNCLEAR = "unclear"     # no se puede saber — respuesta legítima, no un fallo
VERDICTS = (SERVED, PARTIAL, FAILED, UNCLEAR)


# ---------------------------------------------------------------------------
# El prompt
# ---------------------------------------------------------------------------
# Encuadre ESCÉPTICO y en la dirección segura (doc 41 §3.3): el coste de dar por
# bueno algo que falló es alto (se convierte en procedimiento y se repite); el
# de marcar `unclear` algo que sí sirvió es bajo (se pierde una oportunidad).
_SYSTEM = """Eres el juez de aprendizaje de Aithera, un asistente personal de IA.

Tu trabajo es determinar si una misión le SIRVIÓ DE VERDAD al usuario. No
evalúas si el texto está bien escrito ni si el sistema funcionó: evalúas si la
persona obtuvo lo que pidió.

Sé escéptico. Declara "served" ÚNICAMENTE si la evidencia lo sostiene:
- hay un entregable verificado (un archivo que existe de verdad en disco), o
- el resultado responde lo pedido de forma comprobable con lo que ves, o
- el usuario siguió adelante después sin corregir ni repetir la petición.

Un texto bien redactado sin efecto NO es servir. Prometer algo no es hacerlo.

Señales que suelen indicar que NO sirvió:
- el usuario volvió a pedir lo mismo poco después (si lo pide otra vez es que
  la primera no funcionó), o respondió corrigiendo, quejándose o insistiendo;
- Aithera se rindió, rechazó el plan, o avisó de que no pudo completar algo;
- el bucle se atascó, o se afirmaron archivos que no se escribieron.

CITA SIEMPRE qué señales sostienen tu veredicto, usando los identificadores que
aparecen en la lista "senales_citables". No cites señales que no estén ahí.

Si no se puede saber con lo que tienes, responde "unclear". Es una respuesta
legítima y preferible a inventar certeza.

Responde SOLO con este JSON, sin texto alrededor:
{"verdict": "served|partial|failed|unclear",
 "confidence": 0.0-1.0,
 "reasons": "2-4 frases explicando el veredicto, en español",
 "evidence": ["id_de_senal", "..."],
 "lesson": {"type": "none|fact|procedure|skill_improvement|error_pattern|system_weakness",
            "content": "qué se aprende, o cadena vacía si nada",
            "related_skill_id": null}}

Sobre "lesson" — SE APRENDE IGUAL DEL ACIERTO QUE DEL ERROR, y son lecciones
distintas:
- si SIRVIÓ y el camino parece repetible → "procedure" (cómo se hizo bien) o
  "skill_improvement" si mejora una de las que ya existen (te doy la lista);
- si NO sirvió → "error_pattern" (qué falló y en qué condiciones vuelve a
  fallar) o "system_weakness" (le falta una capacidad, una herramienta o una
  configuración a Aithera). Un fallo bien entendido vale tanto como un éxito:
  di POR QUÉ falló, no que falló;
- si el usuario contó algo estable sobre sí mismo → "fact".

La respuesta esperada en la mayoría de misiones sigue siendo
{"type": "none", "content": ""}. NO inventes lecciones para tener algo que
decir: solo hay lección cuando de verdad se aprende algo reutilizable."""

_SYSTEM_CHAT = """Eres el juez de aprendizaje de Aithera. Te doy varios turnos
SUELTOS de conversación (charla, no misiones con herramientas). Para cada uno
dime si la respuesta le sirvió al usuario.

Sé breve: la mayoría de la charla es trivial y su veredicto es evidente. Lo que
de verdad importa aquí es detectar (a) respuestas que no sirvieron y (b) datos
estables sobre el usuario que merezca la pena recordar.

Responde SOLO con este JSON:
{"turns": [{"id": "<el id que te doy>",
            "verdict": "served|partial|failed|unclear",
            "confidence": 0.0-1.0,
            "reasons": "una frase",
            "lesson": {"type": "none|fact", "content": ""}}]}

"lesson.type" solo es "fact" cuando el usuario dice algo estable sobre sí mismo
(preferencia, contexto personal, cómo quiere que se le hable). Nunca inventes."""


# ---------------------------------------------------------------------------
# Selección del juez (regla 1: juez ≠ ejecutor)
# ---------------------------------------------------------------------------
def _executors_of(paquete: dict) -> set:
    """Los modelos que EJECUTARON la misión, según la telemetría. Son los que
    el juez no debe ser: nadie corrige su propio examen."""
    usados: set = set()
    try:
        import app.telemetry as telemetry

        tl = telemetry.mission_timeline(paquete.get("mission_id") or "")
        for clave in (tl.get("summary", {}).get("llm_by_model") or {}):
            if clave and clave != "?":
                usados.add(str(clave))
    except Exception:
        pass
    return usados


async def _ask(prompt: str, system: str, *, exclude: tuple = ()) -> tuple[Optional[dict], Optional[str]]:
    """UNA llamada de capacidad LEARN. Devuelve (json, modelo_usado).

    `exclude` es el anti-sesgo: el MEL ya sabe saltar candidatos (lo estrenó el
    auto-catálogo de E1b, por este mismo motivo). Si tras excluirlos no queda
    ninguno apto, el MEL responde igual con el que haya — y por eso quien llama
    comprueba después si el modelo que atendió estaba en la lista de excluidos,
    para marcar `judge_bias`."""
    import app.mel as mel

    peticion = mel.ExecutionRequest(
        capability=mel.Capability.LEARN,
        prompt=prompt,
        system_prompt=system,
        exclude=tuple(exclude),
    )
    try:
        res = await asyncio.wait_for(
            mel.complete(peticion),
            timeout=float(getattr(settings, "LEARNER_JUDGE_BUDGET_S", 180.0)))
    except asyncio.TimeoutError:
        logger.info("[learner/judge] el juez agotó su plazo — la misión queda sin juzgar")
        return None, None
    except Exception as e:
        logger.info(f"[learner/judge] el juez falló ({e!r}) — la misión queda sin juzgar")
        return None, None
    if not getattr(res, "ok", False):
        return None, None

    servido = getattr(res, "served_by", None)
    modelo = f"{servido.provider}:{servido.model}" if servido else None
    try:
        from app.tie import extract_json

        data = extract_json(res.text or "")
    except Exception:
        data = None
    return (data if isinstance(data, dict) else None), modelo


# ---------------------------------------------------------------------------
# El grounding del juez (regla 2 + regla 3, doc 41 §3.5)
# ---------------------------------------------------------------------------
def apply_grounding(veredicto: str, evidencia: list, citables: set) -> tuple[str, list, Optional[str]]:
    """Comprueba que un veredicto se apoya en señales que EXISTEN.

    Determinista y mínimo a propósito: el control de un LLM no puede ser otro
    LLM (regresión infinita). Solo actúa en la dirección segura — un `served`
    sin respaldo baja a `unclear`; un `failed` JAMÁS sube. Es el mismo principio
    que el grounding del responder (S2·S6): lo mecánico puede quitar confianza,
    nunca ponerla.

    Devuelve (veredicto_final, evidencia_válida, motivo_de_la_degradación)."""
    validas = [e for e in (evidencia or []) if isinstance(e, str) and e in citables]
    if veredicto not in VERDICTS:
        return UNCLEAR, validas, "veredicto fuera de la taxonomía"
    if veredicto in (SERVED, PARTIAL) and not validas:
        motivo = ("sin evidencia citable: el veredicto no se apoya en ninguna "
                  "señal del paquete")
        return UNCLEAR, validas, motivo
    return veredicto, validas, None


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------
def _save(paquete: dict, data: dict, modelo: Optional[str], sesgado: bool,
          citables: set) -> Optional[str]:
    from app.db.database import SessionLocal
    from app.learner.models import MissionVerdict

    bruto = str(data.get("verdict") or "").strip().lower()
    final, evidencia, degradado = apply_grounding(
        bruto, data.get("evidence") or [], citables)
    razones = str(data.get("reasons") or "").strip()[:2000]
    if degradado:
        razones = (f"[degradado a unclear: {degradado}] {razones}").strip()
        logger.info(f"[learner/judge] «{bruto}» degradado a unclear ({degradado})")

    try:
        confianza = max(0.0, min(1.0, float(data.get("confidence") or 0.0)))
    except Exception:
        confianza = 0.0
    if degradado:
        confianza = min(confianza, 0.3)

    leccion = data.get("lesson") if isinstance(data.get("lesson"), dict) else None
    if leccion and str(leccion.get("type") or "none") == "none":
        leccion = None

    vid = uuid.uuid4().hex
    mission_id = str(paquete.get("mission_id") or "")
    db = SessionLocal()
    try:
        db.add(MissionVerdict(
            id=vid,
            mission_id=mission_id,
            trace_id=paquete.get("trace_id"),
            origin=str(paquete.get("origin") or "user"),
            verdict=final,
            confidence=confianza,
            reasons=razones,
            evidence=evidencia,
            signals=paquete,
            lesson=leccion,
            judge_model=modelo,
            judge_bias=bool(sesgado),
            created_at=datetime.utcnow(),
        ))
        # [LC3] RE-JUZGAR ES LEGÍTIMO Y SE VE (doc 41 §3.1): si ya había un
        # veredicto vigente para esta misión, se enlaza como sustituido —
        # nunca se borra, nunca se sobreescribe. Hasta LC3 el campo
        # `superseded_by` existía en el esquema pero nadie lo escribía; sin
        # esto, dos filas con `superseded_by IS NULL` para la misma misión
        # convivían y solo el orden por fecha decidía cuál es "la vigente"
        # — funcionaba de casualidad, no por diseño. Con el enlace explícito,
        # la historia completa de una misión re-juzgada es recorrible.
        anteriores = (db.query(MissionVerdict)
                     .filter(MissionVerdict.mission_id == mission_id,
                             MissionVerdict.superseded_by.is_(None),
                             MissionVerdict.id != vid).all())
        for previa in anteriores:
            previa.superseded_by = vid
        db.commit()
    except Exception as e:
        logger.error(f"[learner/judge] no se pudo guardar el veredicto: {e!r}")
        db.rollback()
        return None
    finally:
        db.close()

    # [LC2, doc 41 §7] La nota de los modelos pasa a medir "sirvió", no
    # "terminó": si el juez contradice lo que se contó al acabar la misión, se
    # corrige. Best-effort — el veredicto ya está guardado y es lo importante.
    try:
        from app.learner import stats

        stats.apply_verdict(str(paquete.get("mission_id") or ""),
                            served=(final == SERVED),
                            was_ok=(str(paquete.get("state") or "") == "done"))
    except Exception as e:
        logger.info(f"[learner/judge] no se pudo ajustar la nota del modelo: {e!r}")
    return vid


def verdict_of(mission_id: str) -> Optional[dict]:
    """El veredicto VIGENTE de una misión (el no sustituido), o None."""
    from app.db.database import SessionLocal
    from app.learner.models import MissionVerdict

    db = SessionLocal()
    try:
        fila = (db.query(MissionVerdict)
                .filter(MissionVerdict.mission_id == str(mission_id),
                        MissionVerdict.superseded_by.is_(None))
                .order_by(MissionVerdict.created_at.desc()).first())
        if fila is None:
            return None
        return {"id": fila.id, "mission_id": fila.mission_id,
                "verdict": fila.verdict, "confidence": fila.confidence,
                "reasons": fila.reasons, "evidence": list(fila.evidence or []),
                "lesson": fila.lesson, "origin": fila.origin,
                "judge_model": fila.judge_model, "judge_bias": bool(fila.judge_bias),
                "created_at": fila.created_at.isoformat() if fila.created_at else None}
    except Exception as e:
        logger.info(f"[learner/judge] verdict_of falló: {e!r}")
        return None
    finally:
        db.close()


def verdict_history(mission_id: str) -> list[dict]:
    """[LC3] TODOS los veredictos que ha tenido esta misión, del más antiguo
    al más reciente — incluidos los sustituidos por un re-juicio. Re-juzgar
    (doc 41 §8) nunca borra, así que la historia completa tiene que poder
    recorrerse: es lo que hace comprobable "mi discrepancia quedó
    registrada" en vez de una promesa vacía."""
    from app.db.database import SessionLocal
    from app.learner.models import MissionVerdict

    db = SessionLocal()
    try:
        filas = (db.query(MissionVerdict)
                 .filter(MissionVerdict.mission_id == str(mission_id))
                 .order_by(MissionVerdict.created_at.asc()).all())
        return [{"id": f.id, "verdict": f.verdict, "confidence": f.confidence,
                 "reasons": f.reasons, "evidence": list(f.evidence or []),
                 "lesson": f.lesson, "origin": f.origin,
                 "judge_model": f.judge_model, "judge_bias": bool(f.judge_bias),
                 "superseded_by": f.superseded_by,
                 "created_at": f.created_at.isoformat() if f.created_at else None}
                for f in filas]
    except Exception as e:
        logger.info(f"[learner/judge] verdict_history falló: {e!r}")
        return []
    finally:
        db.close()


def calibration_summary() -> dict:
    """[LC3] La sección "calibración" de la pestaña Salud: cómo de fiable ha
    sido el juez, medido por lo que el propio sistema puede observar sin
    adivinar nada — nunca una nota inventada.

    Dos señales, ambas de solo lectura sobre lo que ya existe: (1) cuántos
    veredictos se re-juzgaron a mano y de esos cuántos CAMBIARON de veredicto
    (el usuario discrepaba con razón) frente a cuántos CONFIRMARON el
    original (quería una segunda opinión, no la tenía); (2) la fracción de
    veredictos dados por un juez SESGADO (sin alternativa al modelo que
    ejecutó la misión, regla 1 de doc 41 §5) — cuantos más, menos se puede
    fiar uno del conjunto sin mirar el detalle."""
    from app.db.database import SessionLocal
    from app.learner.models import MissionVerdict

    db = SessionLocal()
    try:
        total = db.query(MissionVerdict).count()
        sesgados = (db.query(MissionVerdict)
                    .filter(MissionVerdict.judge_bias.is_(True)).count())
        sustituidas = (db.query(MissionVerdict)
                       .filter(MissionVerdict.superseded_by.isnot(None)).all())
        rejuzgadas = len(sustituidas)
        cambiaron = 0
        if sustituidas:
            ids_sucesores = {f.superseded_by for f in sustituidas if f.superseded_by}
            sucesores = (db.query(MissionVerdict.id, MissionVerdict.verdict)
                         .filter(MissionVerdict.id.in_(ids_sucesores)).all()
                         if ids_sucesores else [])
            verdict_por_id = {sid: v for sid, v in sucesores}
            for f in sustituidas:
                nuevo = verdict_por_id.get(f.superseded_by)
                if nuevo and nuevo != f.verdict:
                    cambiaron += 1
        return {
            "total_verdicts": total,
            "biased_verdicts": sesgados,
            "bias_rate": (sesgados / total) if total else 0.0,
            "rejudged": rejuzgadas,
            "rejudge_changed_verdict": cambiaron,
            "rejudge_confirmed": rejuzgadas - cambiaron,
        }
    except Exception as e:
        logger.info(f"[learner/judge] calibration_summary falló: {e!r}")
        return {"total_verdicts": 0, "biased_verdicts": 0, "bias_rate": 0.0,
                "rejudged": 0, "rejudge_changed_verdict": 0, "rejudge_confirmed": 0}
    finally:
        db.close()


def served(mission_id: str) -> bool:
    """¿Consta que esta misión SIRVIÓ? Fail-closed: sin veredicto, NO.

    Es la función que sustituye a `state == "done"` en todo el aprendizaje. Que
    devuelva False cuando aún no se ha juzgado es lo correcto: no saber si algo
    funcionó no es lo mismo que saber que funcionó, y confundirlos es
    exactamente lo que hizo el Learner mecánico."""
    v = verdict_of(mission_id)
    return bool(v and v["verdict"] == SERVED)


# ---------------------------------------------------------------------------
# Juzgar UNA misión
# ---------------------------------------------------------------------------
def _skill_catalog(limite: int = 40) -> list[dict]:
    """[LC2, doc 41 §4.1] Las skills que YA existen, compactas. Viajan con el
    juez para que pueda decir "esto MEJORA la skill X" en vez de sugerir una
    duplicada — que es como una biblioteca de skills acaba llena de variantes
    del mismo procedimiento con nombres distintos."""
    try:
        from app.learner.library import skill_library

        return [{"id": s.get("id"), "name": s.get("name"),
                 "description": (s.get("description") or "")[:160]}
                for s in skill_library.list_compact(limit=limite)]
    except Exception as e:
        logger.info(f"[learner/judge] sin catálogo de skills ({e!r})")
        return []


def _prompt_for(paquete: dict, citables: set) -> str:
    resumen = dict(paquete)
    resumen["senales_citables"] = sorted(citables)
    catalogo = _skill_catalog()
    if catalogo:
        resumen["skills_que_ya_existen"] = catalogo
    return ("Juzga esta misión:\n\n"
            + json.dumps(resumen, ensure_ascii=False, indent=1, default=str)[:14000])


async def judge_mission(mission_id: str, *, force: bool = False) -> Optional[str]:
    """Juzga UNA misión y guarda el veredicto. Devuelve su id, o None.

    Nunca lanza: juzgar es observación, y una observación que falla no puede
    tumbar nada. Sin veredicto, el aprendizaje simplemente no cuenta con esa
    misión (fail-closed)."""
    if not mission_id:
        return None
    try:
        if not force and verdict_of(mission_id) is not None:
            return None                      # ya juzgada — juzgar es idempotente

        from app.core import corpus
        from app.learner import signals

        paquete = signals.collect(mission_id)
        if not paquete:
            return None
        if not corpus.is_real(paquete.get("origin") or "user"):
            # Corpus de pruebas: se registra el veredicto igualmente (auditable)
            # pero sin gastar una llamada al modelo — de esto no se aprende.
            return _save(paquete,
                         {"verdict": UNCLEAR, "confidence": 0.0,
                          "reasons": "Corpus de pruebas: no alimenta el aprendizaje.",
                          "evidence": []},
                         None, False, set())

        citables = signals.citable_ids(paquete)
        ejecutores = _executors_of(paquete)
        data, modelo = await _ask(_prompt_for(paquete, citables), _SYSTEM,
                                  exclude=tuple(sorted(ejecutores)))
        if not data:
            return None
        sesgado = bool(modelo and modelo in ejecutores)
        if sesgado:
            logger.info(f"[learner/judge] sin juez alternativo: {modelo} se juzga "
                        f"a sí mismo (veredicto marcado como sesgado)")
        return _save(paquete, data, modelo, sesgado, citables)
    except Exception as e:
        logger.error(f"[learner/judge] juzgar {mission_id} falló: "
                     f"{type(e).__name__}: {e}")
        return None


# ---------------------------------------------------------------------------
# La cola: juzgar en background, con retardo para que exista "el después"
# ---------------------------------------------------------------------------
_cola: dict[str, float] = {}          # mission_id → cuándo toca (monotónico)
_tarea: Optional[asyncio.Task] = None
_TICK_S = 20.0


def enqueue(mission_id: str, *, delay_min: Optional[float] = None) -> None:
    """Encola una misión para juzgarla dentro de un rato.

    El retardo NO es un capricho: sin él, "el después" está vacío y se perdería
    la señal más informativa. Volver a encolar la misma misión no duplica nada;
    solo puede ADELANTAR su turno (lo hace `hurry` cuando el usuario escribe)."""
    if not mission_id:
        return
    espera = (delay_min if delay_min is not None
              else float(getattr(settings, "LEARNER_JUDGE_DELAY_MIN", 10.0)))
    cuando = asyncio.get_event_loop().time() + max(0.0, espera) * 60.0
    anterior = _cola.get(mission_id)
    _cola[mission_id] = min(anterior, cuando) if anterior is not None else cuando
    _ensure_worker()


def hurry(session_id: Optional[str] = None) -> None:
    """El usuario ha vuelto a escribir: ya hay "después" que leer, así que las
    misiones en espera pueden juzgarse ahora. Sin `session_id` adelanta todas —
    es lo que hace el lote nocturno."""
    ahora = asyncio.get_event_loop().time()
    for mid in list(_cola):
        _cola[mid] = min(_cola[mid], ahora)
    _ensure_worker()


def _ensure_worker() -> None:
    global _tarea
    if _tarea is None or _tarea.done():
        try:
            _tarea = asyncio.create_task(_worker())
        except RuntimeError:
            _tarea = None            # sin loop (tests síncronos): nada que drenar


async def _worker() -> None:
    """Drena la cola. Un fallo juzgando una misión no puede parar el resto."""
    while _cola:
        ahora = asyncio.get_event_loop().time()
        listas = [m for m, t in _cola.items() if t <= ahora]
        if not listas:
            await asyncio.sleep(_TICK_S)
            continue
        for mid in listas:
            _cola.pop(mid, None)
            try:
                await judge_mission(mid)
            except Exception as e:
                logger.error(f"[learner/judge] cola: {mid} falló ({e!r})")


async def drain_now() -> int:
    """Juzga TODO lo encolado sin esperar. Para los tests y para el cierre
    ordenado; en producción la cola se drena sola."""
    n = 0
    pendientes = list(_cola)
    _cola.clear()
    for mid in pendientes:
        if await judge_mission(mid):
            n += 1
    return n


def pending_count() -> int:
    return len(_cola)


# ---------------------------------------------------------------------------
# Suscripción al bus
# ---------------------------------------------------------------------------
_SETTLE = ("mission.completed", "mission.failed")
_registrado = False


async def _on_mission_settled(event) -> None:
    payload = getattr(event, "payload", None) or {}
    mid = payload.get("mission_id")
    if mid:
        enqueue(str(mid))


def register_handlers() -> None:
    """Cablea el juez al bus. Lo llama el `lifespan`. Idempotente."""
    global _registrado
    if _registrado:
        return
    from app.core.events import subscribe

    for nombre in _SETTLE:
        subscribe(nombre, _on_mission_settled)
    _registrado = True
    logger.info("[learner/judge] el juez escucha mission.completed/failed")


# ---------------------------------------------------------------------------
# La pasada nocturna: catch-up + backfill + lote de charla
# ---------------------------------------------------------------------------
def unjudged(limit: int = 100, days: int = 30) -> list[str]:
    """Misiones REALES terminadas y todavía sin veredicto, de la más reciente a
    la más antigua. Cubre a la vez el catch-up (lo del día que la cola no llegó
    a juzgar porque el backend se apagó) y el backfill del histórico: son el
    mismo problema."""
    from app.db.database import SessionLocal
    from app.learner.models import MissionVerdict
    from app.tie import tracer

    out: list[str] = []
    try:
        recientes = tracer.recent_missions(days=days, limit=max(limit * 3, 60),
                                           state=None)
    except Exception as e:
        logger.info(f"[learner/judge] unjudged: sin historial ({e!r})")
        return out

    from app.core import corpus

    candidatas = [m for m in recientes
                  if m.get("state") in ("done", "failed", "cancelled")
                  and corpus.is_real(corpus.origin_of(m.get("origin"),
                                                      goal=m.get("goal") or ""))]
    if not candidatas:
        return out

    db = SessionLocal()
    try:
        ids = [str(m.get("mission_id")) for m in candidatas if m.get("mission_id")]
        ya = {r[0] for r in db.query(MissionVerdict.mission_id)
              .filter(MissionVerdict.mission_id.in_(ids)).all()} if ids else set()
    except Exception:
        ya = set()
    finally:
        db.close()

    for m in candidatas:
        mid = str(m.get("mission_id") or "")
        if mid and mid not in ya:
            out.append(mid)
        if len(out) >= limit:
            break
    return out


async def run_nightly_judging() -> dict:
    """La pasada nocturna del juez. Corre ANTES del análisis del Learner: la
    consolidación necesita veredictos, no estados.

    Tres cosas, en orden: adelantar lo que estuviera en cola, juzgar lo que
    quedó sin veredicto (catch-up + backfill), y el lote agrupado de charla."""
    resumen = {"queued": 0, "judged": 0, "chat_turns": 0}
    try:
        hurry()
        resumen["queued"] = await drain_now()
    except Exception as e:
        logger.info(f"[learner/judge] drenar la cola falló: {e!r}")

    tope = int(getattr(settings, "LEARNER_JUDGE_BACKFILL", 100))
    try:
        for mid in unjudged(limit=tope):
            if await judge_mission(mid):
                resumen["judged"] += 1
    except Exception as e:
        logger.error(f"[learner/judge] backfill nocturno falló: {e!r}")

    try:
        resumen["chat_turns"] = await judge_chat_batch()
    except Exception as e:
        logger.info(f"[learner/judge] lote de charla falló: {e!r}")

    logger.info(f"[learner/judge] pasada nocturna: {resumen}")
    return resumen


# ---------------------------------------------------------------------------
# El lote de charla (doc 41 §3.4)
# ---------------------------------------------------------------------------
# La charla trivial NO crea misión desde A·VOZ-3 (crear una traza por "hola" era
# ruido y latencia). Así que aquí la unidad es el TURNO del chat, con un id
# sintético `chat:<id>` para que la tabla siga siendo uniforme. Se juzga en UNA
# llamada agrupada: todo recibe veredicto, y el coste se controla agrupando.
_CHAT_PREFIX = "chat:"


async def judge_chat_batch(limit: Optional[int] = None) -> int:
    """Juzga en bloque los turnos de charla recientes sin veredicto."""
    from app.db.database import ChatMessage, SessionLocal
    from app.learner.models import MissionVerdict

    tope = int(limit or getattr(settings, "LEARNER_CHAT_BATCH", 25))
    desde = datetime.utcnow() - timedelta(days=2)
    db = SessionLocal()
    try:
        filas = (db.query(ChatMessage)
                 .filter(ChatMessage.created_at >= desde)
                 .order_by(ChatMessage.id.desc()).limit(tope * 4).all())
        filas = list(reversed(filas))
        ids = [f"{_CHAT_PREFIX}{f.id}" for f in filas]
        ya = {r[0] for r in db.query(MissionVerdict.mission_id)
              .filter(MissionVerdict.mission_id.in_(ids)).all()} if ids else set()
    except Exception as e:
        logger.info(f"[learner/judge] lote de charla: sin datos ({e!r})")
        return 0
    finally:
        db.close()

    # Se emparejan turnos usuario→asistente: juzgar una respuesta sin la
    # pregunta no significa nada.
    pares: list[dict] = []
    for i, f in enumerate(filas):
        if f.role != "user":
            continue
        clave = f"{_CHAT_PREFIX}{f.id}"
        if clave in ya:
            continue
        respuesta = next((g for g in filas[i + 1:i + 3] if g.role == "assistant"), None)
        if respuesta is None:
            continue
        pares.append({"id": clave,
                      "usuario": (f.content or "")[:600],
                      "aithera": (respuesta.content or "")[:900]})
        if len(pares) >= tope:
            break
    if not pares:
        return 0

    data, modelo = await _ask(
        "Turnos de conversación a juzgar:\n\n"
        + json.dumps(pares, ensure_ascii=False, indent=1)[:12000], _SYSTEM_CHAT)
    if not data or not isinstance(data.get("turns"), list):
        return 0

    por_id = {p["id"]: p for p in pares}
    n = 0
    for t in data["turns"]:
        if not isinstance(t, dict):
            continue
        clave = str(t.get("id") or "")
        par = por_id.get(clave)
        if par is None:
            continue                 # el modelo se inventó un id: se ignora
        paquete = {"mission_id": clave, "trace_id": None, "origin": "user",
                   "goal": par["usuario"], "state": "chat",
                   "outcome": par["aithera"], "kind": "chat_turn"}
        # La charla no tiene señales duras que citar, así que el grounding no
        # puede exigirlas: se le dan como citables las dos que sí existen.
        citables = {"outcome_text", "user_message"}
        t.setdefault("evidence", ["outcome_text"])
        if _save(paquete, t, modelo, False, citables):
            n += 1
    return n
