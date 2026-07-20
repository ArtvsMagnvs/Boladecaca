# app/orchestrator/conductor.py — ejecuta los objetivos de un run (R2)
#
# EL CORAZÓN DEL BLOQUE. Lo que el TIE no puede hacer solo (doc 23 §0):
#
#   1. CONCURRENCIA — varias misiones a la vez, acotadas por un semáforo. El
#      email no espera a que terminen los 15 canales de YouTube.
#   2. DEPENDENCIAS  — "cuando termines todo, avísame" arranca al final, sin que
#      nadie tenga que ordenarlo a mano.
#   3. AISLAMIENTO   — que una misión falle, o se quede esperando tu aprobación,
#      NO congela a las demás. Esto es lo que hoy es imposible: un gate deja la
#      misión entera en `waiting` y con ella todo el mensaje.
#   4. ANIDAMIENTO   — un objetivo demasiado amplio se vuelve a descomponer en
#      sub-misiones, con profundidad acotada.
#
# DÓNDE VIVE LA RECURSIÓN: aquí, y SOLO aquí. Un nodo del TIE nunca abre
# misiones; si pudiera, la profundidad sería imposible de acotar y una mala
# planificación podría desatar una cascada. Al decidirla el conductor, el límite
# (`ORCH_MAX_DEPTH`) se comprueba en un único punto.
from __future__ import annotations

import asyncio
import time

from app.core.logging_config import get_system_logger
from app.orchestrator import store
from app.orchestrator.contracts import Objective, OrchestrationRun

logger = get_system_logger("orchestrator.conductor")


async def run_objectives(run: OrchestrationRun) -> OrchestrationRun:
    """Ejecuta todos los objetivos del run respetando dependencias y
    concurrencia. Devuelve el run con cada objetivo resuelto.

    No lanza: los fallos quedan en el estado de cada objetivo, para que la
    consolidación pueda contar la verdad de lo que pasó."""
    from app.core.config import settings

    t0 = time.monotonic()
    semaforo = asyncio.Semaphore(max(1, settings.ORCH_MAX_CONCURRENT))
    store.save(run)
    _emit("orchestration.started", {"run_id": run.id, "n_objectives": len(run.objectives)})

    while True:
        if store.is_cancelled(run.id):
            for o in run.objectives:
                if o.state in ("pending", "running"):
                    o.state = "cancelled"
            break

        # Objetivos que nunca podrán ejecutarse (una dependencia suya acabó mal).
        # Se marcan ANTES de mirar el ready-set: si no, se quedarían `pending`
        # para siempre y el bucle no terminaría nunca.
        bloqueados = run.blocked()
        if bloqueados:
            for o in bloqueados:
                o.state = "skipped"
                o.error = "no se ejecutó porque un objetivo del que dependía no terminó bien"
            store.save(run)
            continue

        listos = run.ready()
        if not listos:
            break

        for o in listos:
            o.state = "running"
        store.save(run)

        # `return_exceptions=True` es el aislamiento: una misión que revienta
        # devuelve su excepción en la lista en vez de cancelar a sus hermanas.
        await asyncio.gather(
            *(_ejecutar(o, run, semaforo) for o in listos),
            return_exceptions=True,
        )
        store.save(run)

    run.state = "cancelled" if store.is_cancelled(run.id) else _estado_final(run)
    duracion = int((time.monotonic() - t0) * 1000)
    store.save(run, duration_ms=duracion)
    _emit("orchestration.completed",
          {"run_id": run.id, "ok": run.state == "done", "duration_ms": duracion})
    return run


def _estado_final(run: OrchestrationRun) -> str:
    """`done` si algo útil salió; `failed` solo si NADA salió bien. Mismo
    criterio que el executor del TIE con sus nodos (T3): entregar lo conseguido
    vale más que un veredicto binario."""
    if any(o.state == "done" for o in run.objectives):
        return "done"
    return "failed"


async def _ejecutar(objetivo: Objective, run: OrchestrationRun, semaforo: asyncio.Semaphore) -> None:
    """Un objetivo → una misión del TIE (o una descomposición, si es demasiado
    amplio). Escribe el resultado en el propio objetivo; nunca propaga."""
    from app.core.config import settings

    async with semaforo:
        if store.is_cancelled(run.id):
            objetivo.state = "cancelled"
            return
        try:
            if objetivo.needs_decomposition and objetivo.depth < settings.ORCH_MAX_DEPTH:
                await _descomponer_y_ejecutar(objetivo, run, semaforo)
            else:
                if objetivo.needs_decomposition:
                    # Tocó techo: se ejecuta como una misión normal. El TIE hará
                    # lo que pueda con su propio planner — que es exactamente lo
                    # que ocurría antes de existir esta capa.
                    logger.info(f"[conductor] {objetivo.id} pedía descomponerse pero se alcanzó "
                                f"ORCH_MAX_DEPTH={settings.ORCH_MAX_DEPTH}; se ejecuta como misión única")
                await _ejecutar_como_mision(objetivo, run)
        except asyncio.CancelledError:
            objetivo.state = "cancelled"
            raise
        except Exception as e:
            objetivo.state = "failed"
            objetivo.error = f"{type(e).__name__}: {e}"
            logger.error(f"[conductor] objetivo {objetivo.id} falló: {e}")
        finally:
            _emit("orchestration.objective_completed",
                  {"run_id": run.id, "objective_id": objetivo.id, "ok": objetivo.state == "done"})


async def _ejecutar_como_mision(objetivo: Objective, run: OrchestrationRun) -> None:
    """Delega en el TIE por su API pública. El orquestador NO conoce el planner,
    el executor ni las trazas: solo sabe pedir una misión y leer su resultado."""
    import app.tie as tie

    contexto = _contexto_de_dependencias(objetivo, run)
    goal = objetivo.goal if not contexto else f"{objetivo.goal}\n\nContexto de pasos previos:\n{contexto}"

    mission = await tie.submit_mission(
        goal=goal,
        source=run.source,
        channel=run.channel,
        run_id=run.id,
        parent_id=objetivo.mission_id,   # None salvo en sub-misiones
    )
    objetivo.mission_id = mission.id
    objetivo.outcome = mission.outcome
    # Una misión que quedó esperando aprobación NO es un fallo: es un estado
    # legítimo que la consolidación tiene que contar tal cual.
    objetivo.state = {"done": "done", "waiting": "waiting",
                      "cancelled": "cancelled"}.get(mission.state, "failed")
    if objetivo.state == "failed":
        objetivo.error = mission.outcome or "la misión no pudo completarse"


def _contexto_de_dependencias(objetivo: Objective, run: OrchestrationRun) -> str:
    """Lo que produjeron los objetivos de los que éste depende. Sin esto, el
    "cuando termines todo, avísale" no tendría nada que contar."""
    trozos = []
    for dep_id in objetivo.depends_on:
        dep = run.by_id(dep_id)
        if dep and dep.outcome:
            trozos.append(f"- {dep.goal}: {dep.outcome[:600]}")
    return "\n".join(trozos)


async def _descomponer_y_ejecutar(objetivo: Objective, run: OrchestrationRun,
                                  semaforo: asyncio.Semaphore) -> None:
    """Un objetivo demasiado amplio se parte en sub-objetivos y se ejecutan como
    un mini-run. Sus resultados se funden en el `outcome` del objetivo padre, así
    que la consolidación final no necesita saber que hubo anidamiento."""
    from app.orchestrator import decomposer

    subobjetivos = await decomposer.decompose(
        objetivo.goal, objectives_hint=[objetivo.goal], depth=objetivo.depth + 1,
    )
    # Un solo sub-objetivo (o ninguno) no aporta nada: se ejecuta directo y se
    # evita una vuelta de descomposición inútil.
    if len(subobjetivos) <= 1:
        objetivo.needs_decomposition = False
        await _ejecutar_como_mision(objetivo, run)
        return

    for sub in subobjetivos:
        sub.id = f"{objetivo.id}.{sub.id}"
        sub.depends_on = [f"{objetivo.id}.{d}" for d in sub.depends_on]
        sub.depth = objetivo.depth + 1

    sub_run = OrchestrationRun(
        id=run.id, user_message=objetivo.goal, objectives=subobjetivos,
        channel=run.channel, source=run.source,
    )
    # Se reusa el mismo motor: las sub-misiones heredan concurrencia,
    # dependencias y aislamiento sin código nuevo. El semáforo es el MISMO
    # objeto, así que el tope global de misiones a la vez se respeta también
    # dentro del anidamiento.
    await _ejecutar_subrun(sub_run, semaforo)

    hechos = [s for s in subobjetivos if s.state == "done"]
    objetivo.state = "done" if hechos else "failed"
    objetivo.outcome = "\n".join(f"- {s.goal}: {s.outcome or '(sin resultado)'}" for s in subobjetivos)
    if not hechos:
        objetivo.error = "ninguna de las partes pudo completarse"


async def _ejecutar_subrun(sub_run: OrchestrationRun, semaforo: asyncio.Semaphore) -> None:
    """Mismo bucle de olas que `run_objectives`, pero sin tocar la persistencia
    del run padre (los sub-objetivos viven dentro del `outcome` de su objetivo,
    no como filas propias) ni volver a emitir eventos de run."""
    while True:
        bloqueados = sub_run.blocked()
        if bloqueados:
            for o in bloqueados:
                o.state = "skipped"
                o.error = "no se ejecutó porque un objetivo del que dependía no terminó bien"
            continue

        listos = sub_run.ready()
        if not listos:
            break
        for o in listos:
            o.state = "running"
        await asyncio.gather(
            *(_ejecutar(o, sub_run, semaforo) for o in listos),
            return_exceptions=True,
        )


def _emit(name: str, payload: dict) -> None:
    """Eventos del bloque (doc 17): metadatos, nunca contenido. Best-effort — el
    bus no puede tumbar una orquestación."""
    try:
        from app.core import events
        events.emit(name, source="orchestrator", payload=payload)
    except Exception:
        pass
