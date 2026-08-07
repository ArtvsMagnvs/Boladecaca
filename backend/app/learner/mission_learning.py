# app/learner/mission_learning.py — reflexión post-misión (V1.1 L2, doc 15 §4)
#
# QUÉ ES: el evento `mission.completed`/`failed` dispara un job asíncrono que
# convierte una misión terminada en tres cosas CONCRETAS. Nada de reflexión sin
# consecuencia (doc 15 §4: "cada pregunta del briefing tiene UNA salida"):
#
#   1. CONTADORES  → `model_stats` / `tool_stats` (stats.py). Determinista, 0
#      LLM, SIEMPRE — también en la charla trivial.
#   2. REFLEXIÓN   → una nota de 2-5 líneas en la Decision API, enlazada por
#      `mission_id`. Solo en misiones NO triviales.
#   3. ATRIBUCIÓN  → de quién fue cada fallo (L2b, `core/failures.py`) y, con
#      ≥3 repeticiones de la misma carencia, una propuesta `config_fix`.
#
# [V1.1 LC2, doc 41 §7] LO QUE YA NO HACE: acumular candidatas a skill. Hasta
# LC1, si el modelo decía `repeatable=true` y la misión había TERMINADO, aquí se
# abría o reforzaba una propuesta — y "terminó" incluye rechazos honestos,
# rendiciones y saludos. Ese fue el camino por el que ocho intentos FALLIDOS del
# mismo encargo acabaron propuestos como procedimiento fijo (doc 41 §0). Quién
# merece ser skill lo decide ahora la consolidación nocturna
# (`consolidation.py`), leyendo los VEREDICTOS del juez.
#
# Lo que queda aquí es EXTRACCIÓN, no juicio — que es exactamente el reparto de
# doc 41 §1: lo mecánico extrae y protege; la IA entiende y propone.
#
# PRESUPUESTO (doc 15 §4 + §10 "coste silencioso"): ≤1 llamada LLM barata por
# misión (capability ANALYZE, política economy → Ollama primero), plazo duro de
# `LEARNER_REFLECTION_BUDGET_S`, y CERO en el camino corto. Reflexionar sobre
# "¿qué hora es?" es reflection theater.
#
# NUNCA BLOQUEA: todo el job va en una task de fondo y cualquier fallo se traga
# con un log. Una misión ya respondió al usuario antes de que esto empiece.
from __future__ import annotations

import asyncio
import re
from collections import OrderedDict
from typing import Any, Optional

from app.core.config import settings
from app.core.logging_config import get_system_logger
from app.learner import ladder, stats
from app.learner.proposals import proposal_service

logger = get_system_logger("learner.mission")

# Caminos que NO merecen reflexión (doc 15 §4, nota de coste). "chat" es el
# camino corto del TIE: charla sin herramientas ni plan.
_TRIVIAL_PATHS = frozenset({"chat"})

# Ring de misiones ya procesadas: el bus es best-effort y podría entregar dos
# veces; agregar dos veces duplicaría los contadores. En memoria a propósito —
# tras un reinicio no hay eventos pendientes que reprocesar (el bus no persiste,
# doc 17), así que una tabla para esto sería peso muerto.
_procesadas: "OrderedDict[str, bool]" = OrderedDict()
_MAX_PROCESADAS = 500


def _ya_procesada(mission_id: str) -> bool:
    if mission_id in _procesadas:
        return True
    _procesadas[mission_id] = True
    while len(_procesadas) > _MAX_PROCESADAS:
        _procesadas.popitem(last=False)
    return False


# ---------------------------------------------------------------------------
# Qué hace que dos misiones sean "la misma tarea"
# ---------------------------------------------------------------------------
_PALABRA = re.compile(r"[a-zà-ÿ0-9]+", re.IGNORECASE)
# Palabras que no distinguen una tarea de otra (artículos, cortesía, deícticos).
_VACIAS = frozenset("""
a al algo ahora aqui asi como con de del el ella ellos en es esa ese eso esta este esto
gracias ha hace hacer hay la las le les lo los me mi mis muy no nos o para pero por
porfavor que quiero se ser si sin sobre su sus te tu tus un una unas unos y ya
dame damelo dime ponme hazme muestrame necesito puedes podrias favor quisiera
""".split())
# NOTA HONESTA sobre la lista: en español las formas con pronombre enclítico
# («prepárame», «resúmemelo») son infinitas y NO se intentan cubrir aquí — sería
# una lista sin fin. No hace falta: la comparación es por SIMILITUD, no por
# igualdad, así que una palabra de cortesía colada solo baja un poco el índice
# sin cambiar la conclusión. Ese es justamente el motivo de haber abandonado el
# hash exacto.


def content_words(goal: str) -> set:
    """Las palabras que DISTINGUEN una tarea de otra: sin vacías y sin las
    cortas. Función pura, microsegundos."""
    return {w.lower() for w in _PALABRA.findall(goal or "")
            if w.lower() not in _VACIAS and len(w) > 3}


def similarity(a: set, b: set) -> float:
    """Jaccard. 1.0 = mismas palabras de contenido; 0.0 = nada en común."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# Umbral de "esto es el mismo encargo". 0.5 = la mitad del vocabulario útil
# compartido. Calibrado con el caso real que rompió la primera versión de esta
# función: «prepárame el resumen semanal del proyecto Aithera» vs «por favor,
# quiero el resumen semanal para el proyecto Aithera» comparten 4 de 6 palabras
# (0.67) y son obviamente el mismo trabajo; cambiar de tema baja de 0.2.
SIMILARITY_THRESHOLD = 0.5


def same_work(goal_a: str, tools_a: list, goal_b: str, tools_b: list) -> bool:
    """¿Son estas dos misiones "la misma tarea"?

    Las HERRAMIENTAS tienen que coincidir exactamente (son el procedimiento:
    leer un informe del disco y buscarlo en la web no es lo mismo aunque se
    pidan igual) y el objetivo tiene que parecerse por encima del umbral.

    HALLAZGO DE LOS TESTS DE L2 — la primera versión de esto era un hash sha1
    de "las 6 palabras más largas": exacto, barato… y roto. Dos redacciones
    naturales del MISMO encargo daban hashes distintos porque una cortesía
    larga («prepárame», «favor») desplazaba a una palabra de contenido del top
    6. Un hash exacto sobre texto libre es frágil por construcción; comparar
    conjuntos no lo es, y sigue costando microsegundos porque solo se compara
    contra las propuestas abiertas (un puñado).

    Por qué NO embeddings aquí: esto corre tras CADA misión. El clustering
    semántico de verdad es el análisis 1 del LLL (L3), en batch nocturno, que
    sí puede permitírselo. Esto solo pretende que las repeticiones OBVIAS se
    detecten gratis y en el momento."""
    if sorted(t.lower() for t in (tools_a or [])) != sorted(t.lower() for t in (tools_b or [])):
        return False
    return similarity(content_words(goal_a), content_words(goal_b)) >= SIMILARITY_THRESHOLD


# ---------------------------------------------------------------------------
# La única llamada al LLM
# ---------------------------------------------------------------------------
_SYSTEM = """Analizas UNA tarea que un asistente personal acaba de terminar, para que
aprenda de ella. Sé breve y concreto: esto se guarda, no se conversa.

Responde SOLO con un objeto JSON, sin texto alrededor y sin markdown:
{
  "reflection": "2-4 frases: qué se consiguió, qué falló y por qué",
  "repeatable": true|false,
  "skill_name": "nombre corto en imperativo si repeatable, si no cadena vacía",
  "skill_steps": ["paso 1", "paso 2"]
}

Reglas:
- "repeatable" es true SOLO si esto es un PROCEDIMIENTO que tendría sentido
  repetir con otros datos (p. ej. "preparar el resumen semanal de un proyecto").
  Una pregunta puntual, una charla o algo que dependía de este momento concreto
  NO es repeatable.
- No inventes lo que no está en los datos. Si algo falló, dilo tal cual.
- En "skill_steps", describe el procedimiento GENERAL, sin nombres propios,
  fechas ni datos personales de esta ejecución concreta."""


def _resumen_para_el_modelo(snap: dict) -> str:
    """Los datos de la misión, compactos. Van DELIMITADOS como datos, nunca
    como órdenes (disciplina anti-inyección de PU8): el objetivo lo escribió el
    usuario y las salidas de nodo pueden traer texto de terceros."""
    lineas = [f"OBJETIVO: {snap.get('goal', '')}",
              f"RESULTADO: {snap.get('state', '?')}"]
    for n in snap.get("nodes") or []:
        tools = ", ".join(f"{c.get('tool')}.{c.get('action')}"
                          f"{'' if c.get('ok') else ' (falló)'}"
                          for c in (n.get("tool_calls") or []))
        linea = f"  - paso «{n.get('goal', '')[:120]}» → {n.get('state')}"
        if tools:
            linea += f" | herramientas: {tools}"
        if n.get("error"):
            linea += f" | error: {str(n['error'])[:160]}"
        lineas.append(linea)
    if snap.get("outcome"):
        lineas.append(f"RESPUESTA FINAL: {str(snap['outcome'])[:600]}")
    return "<datos>\n" + "\n".join(lineas) + "\n</datos>"


async def _reflect(snap: dict) -> Optional[dict]:
    """UNA llamada, capability ANALYZE, política economy, con plazo duro.
    Devuelve el dict parseado o None — que el modelo falle no puede impedir que
    los contadores (lo determinista) se hayan guardado."""
    import app.mel as mel

    peticion = mel.ExecutionRequest(
        capability=mel.Capability.ANALYZE,
        prompt=_resumen_para_el_modelo(snap),
        system_prompt=_SYSTEM,
        policy_override="economy",
    )
    try:
        res = await asyncio.wait_for(
            mel.complete(peticion),
            timeout=float(getattr(settings, "LEARNER_REFLECTION_BUDGET_S", 20.0)))
    except asyncio.TimeoutError:
        logger.info("[learner] reflexión agotó su plazo — se queda en contadores")
        return None
    except Exception as e:
        logger.info(f"[learner] reflexión falló ({e!r}) — se queda en contadores")
        return None
    if not getattr(res, "ok", False):
        return None

    try:
        from app.tie import extract_json   # utilidad pública del TIE, no una copia

        data = extract_json(res.text or "")
    except Exception:
        data = None
    return data if isinstance(data, dict) else None


# ---------------------------------------------------------------------------
# El job
# ---------------------------------------------------------------------------
async def learn_from_mission(mission_id: str, *, ok: bool = True) -> Optional[str]:
    """Aprende de UNA misión terminada. Devuelve el id de la propuesta creada o
    reforzada, si la hay. Nunca lanza."""
    if not mission_id or _ya_procesada(mission_id):
        return None
    try:
        return await _learn(mission_id, ok=ok)
    except Exception as e:
        logger.error(f"[learner] mission learning de {mission_id} falló "
                     f"(ignorado): {type(e).__name__}: {e}")
        return None


async def _propose_config_fixes() -> int:
    """[L2b, doc 27 §5] La primera consecuencia ACCIONABLE de la atribución, y
    sin gastar un solo token: si la misma configuración lleva ≥3 veces
    estorbando, se propone arreglarla con el texto exacto de qué falta y a qué
    pestaña de Ajustes ir.

    NO se registra applier para `config_fix` — y eso es deliberado, no un
    olvido: configurar una API key es del usuario, no de Aithera. La garantía
    de L1 (una propuesta sin applier no se puede consolidar) hace que el panel
    ofrezca "Ir a Ajustes" en vez de "Aceptar". Riesgo bajo: no cambia nada del
    mundo por sí misma.

    Idempotente por `dedup_key`: mientras la carencia siga sin arreglarse, la
    propuesta existente se actualiza en su contador; nunca se acumulan diez
    tarjetas de lo mismo."""
    try:
        huecos = await asyncio.to_thread(stats.config_gaps)
        if not huecos:
            return 0
        abiertas = await proposal_service.pending(kind="config_fix")
        ya = {(p.get("payload") or {}).get("dedup_key") for p in abiertas}
        creadas = 0
        for hueco in huecos:
            if hueco["dedup_key"] in ya:
                continue
            await proposal_service.create(
                kind="config_fix", risk="low", state="observed",
                title=f"Falta configurar: {hueco['component']}",
                summary=(hueco["detail"] or "")[:400]
                        or "Esta parte del sistema no está configurada y ha "
                           "impedido completar varias tareas.",
                payload={"dedup_key": hueco["dedup_key"],
                         "kind_detected": hueco.get("kind"),
                         "component": hueco["component"],
                         "settings_tab": hueco["settings_tab"],
                         "occurrences": hueco["count"],
                         "sample_mission_ids": hueco["sample_mission_ids"]})
            creadas += 1
            logger.info(f"[learner] configuración pendiente propuesta: {hueco['component']} "
                        f"({hueco['count']} veces)")
        return creadas
    except Exception as e:
        logger.info(f"[learner] propuestas de configuración no generadas (no crítico): {e!r}")
        return 0


async def _learn(mission_id: str, *, ok: bool) -> Optional[str]:
    # (1) Contadores — SIEMPRE, hasta en la charla. Van primero a propósito: si
    # el modelo se cae después, lo barato ya está guardado. [L2b] `record_mission`
    # devuelve además la atribución de esta misión (kind dominante, culpa, y si
    # queda excusada de contar contra el modelo).
    escritos = await stats.record_mission(mission_id, ok=ok)
    if not ok and escritos.get("dominant_kind"):
        logger.info(f"[learner] {mission_id} falló por '{escritos['dominant_kind']}' "
                    f"(culpa: {escritos.get('blame')}"
                    f"{', excusada' if escritos.get('excused') else ''})")
    # Que una configuración falte se detecta con CUALQUIER fallo registrado,
    # aunque la misión acabara BIEN: una misión puede completarse sin la
    # herramienta que el preflight excluyó (usando otra vía) y aun así estar
    # dejando esa carencia sin arreglar. Y se comprueba también en la charla
    # trivial, que no merece reflexión pero sí puede topar con lo mismo.
    if escritos.get("failures"):
        await _propose_config_fixes()

    # ¿Merece reflexión? El camino corto no (doc 15 §4).
    def _timeline():
        from app.telemetry import mission_timeline
        return mission_timeline(mission_id)

    timeline = await asyncio.to_thread(_timeline)
    camino = ((timeline or {}).get("summary") or {}).get("path") or "desconocido"
    if camino in _TRIVIAL_PATHS:
        logger.debug(f"[learner] {mission_id}: camino '{camino}', solo contadores {escritos}")
        return None

    # El snapshot lo sirve el TIE por su accesor de LECTURA (nunca leemos su
    # esquema): import diferido para no acoplar el arranque del Learner al TIE.
    def _snap():
        from app.tie import tracer
        return tracer.mission_snapshot(mission_id)

    snap = await asyncio.to_thread(_snap)
    if not snap or not (snap.get("goal") or "").strip():
        return None

    # (2) Reflexión → Decision API. Una nota inútil no se guarda.
    data = await _reflect(snap)
    reflexion = str((data or {}).get("reflection") or "").strip()
    if reflexion:
        await _store_reflection(snap, reflexion, ok=ok)

    # (3) [V1.1 LC2, doc 41 §7] La acumulación MECÁNICA de candidatas se RETIRA.
    #
    # Hasta aquí, esta línea llamaba a `_accumulate_candidate`: si el modelo
    # decía `repeatable=true` y la misión había terminado, se abría (o se
    # reforzaba) una propuesta de skill. Ese es exactamente el camino por el que
    # ocho intentos FALLIDOS del mismo encargo acabaron propuestos como
    # procedimiento fijo — "terminó" no es "sirvió" (doc 41 §0).
    #
    # Quien decide ahora es la consolidación nocturna (`consolidation.py`), que
    # mira los VEREDICTOS del juez, ve el conjunto y también aprende de lo que
    # falló. Lo determinista de esta función —contadores, atribución de fallos y
    # la reflexión en la Decision API— se queda: es extracción, no juicio.
    return None


async def _store_reflection(snap: dict, reflexion: str, *, ok: bool) -> None:
    """La nota va a la Decision API con `mission_id` — el delta #2 de doc 14
    §4.1 existía justo para esto: poder recorrer después qué se decidió y cómo
    salió, misión a misión."""
    try:
        from app.services.decision_service import store_decision

        objetivo = (snap.get("goal") or "")[:180]
        await store_decision(
            title=f"Reflexión: {objetivo}",
            body=reflexion,
            reason="aprendizaje post-misión (Mission Learning, doc 15 §4)",
            impact="low",
            mission_id=snap.get("mission_id") or snap.get("trace_id"),
        )
    except Exception as e:
        logger.info(f"[learner] no se pudo guardar la reflexión (no crítico): {e!r}")


# ---------------------------------------------------------------------------
# Suscripción al bus
# ---------------------------------------------------------------------------
_SETTLE = ("mission.completed", "mission.failed")
_registrado = False


async def _on_mission_settled(event) -> None:
    payload = getattr(event, "payload", None) or {}
    mission_id = payload.get("mission_id")
    if not mission_id:
        return
    ok = event.name == "mission.completed" and bool(payload.get("ok", True))
    await learn_from_mission(mission_id, ok=ok)


def register_handlers() -> None:
    """Cablea el Learner al bus. Lo llama el `lifespan`. Idempotente."""
    global _registrado
    if _registrado:
        return
    from app.core.events import subscribe

    for nombre in _SETTLE:
        subscribe(nombre, _on_mission_settled)
    _registrado = True
    logger.info("[learner] Mission Learning suscrito a mission.completed/failed")
