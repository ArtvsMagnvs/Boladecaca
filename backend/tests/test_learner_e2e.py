# tests/test_learner_e2e.py — EL LEARNER ENTERO, DE PUNTA A PUNTA (V1.1 L1-L3)
#
# QUÉ ES ESTO Y EN QUÉ SE DIFERENCIA DEL RESTO: los otros archivos del Learner
# prueban piezas (la escalera, la taxonomía, la agrupación). Aquí no se prueba
# ninguna pieza: se SIMULA a Aithera trabajando una semana y se comprueba que
# el organismo aprende de verdad, con todas sus capas encadenadas y en el orden
# real en que ocurren.
#
# LA CADENA COMPLETA, sin atajos:
#   misión real → traza real (`tracer.record_start/plan/end`) → telemetría real
#   por los HOOKS DE PRODUCCIÓN (`mel._record_async`, `toolloop._record_loop_event`)
#   → evento real del bus (`tracer.emit_completed`) → el handler REAL del Learner
#   → contadores + atribución + reflexión + candidata → escalera de L1 → análisis
#   nocturno de L3 → informe → el usuario acepta → se aplica → el usuario se
#   arrepiente → se deshace.
#
# UN SOLO DOBLE, y es la frontera del LLM (`app.mel.complete`) — el mismo
# criterio del patrón S4 (doc 27 §3). Ni la BD, ni el bus, ni el tracer, ni la
# cuarentena, ni la biblioteca de skills, ni la atribución están simulados: si
# alguna de esas piezas se desconecta de otra, estos tests se caen. Que es
# exactamente el fallo que ha aparecido tres veces en este proyecto (S9b, S9c,
# el rastro): lógica correcta y DESCONECTADA.
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime

import pytest

from app.core.events import emit  # noqa: F401  (documenta que el bus es el real)
from app.db.database import Base, Config, SessionLocal, OrchestratorTrace, engine
from app.learner import (
    ladder,
    learn_this,
    proposal_service,
    register_handlers,
    run_nightly_analysis,
    skill_library,
)
from app.learner.models import (FailureStat, LearnerProposal, MissionVerdict, ModelStat,
                                Skill, SkillEvent, ToolStat)
from app.learner.stats import failure_summary, model_ranking
from app.telemetry.models import MissionEvent
from app.tie import tracer
from app.tie.contracts import Intent, IntentType, Mission, NodeState, TaskGraph, TaskNode

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _drena_tareas_del_bus(segundos: float = 5.0) -> None:
    """Espera a que el Learner termine lo que tenga entre manos.

    El bus es fire-and-forget por diseño (doc 17): `emit` crea una task y
    devuelve el control de inmediato — el usuario nunca espera a que Aithera
    aprenda. Eso, que en producción es lo correcto, aquí significa que una
    tarea de un test anterior puede aterrizar DESPUÉS de que este haya limpiado
    la BD, dejando filas fantasma que descuadran las cuentas. Se drena por el
    registro real de tareas en vuelo (`events._inflight`), no con un
    `sleep` a ojo."""
    from app.core import events as _events

    limite = asyncio.get_event_loop().time() + segundos
    while _events._inflight and asyncio.get_event_loop().time() < limite:
        await asyncio.sleep(0.01)


@pytest.fixture(autouse=True)
async def _mundo_limpio(anyio_backend):
    """Aithera recién instalada: sin nada aprendido, sin historial, sin trazas.

    Async a propósito: primero se drena lo que quedara en vuelo, LUEGO se
    limpia. Al revés, la limpieza y una tarea rezagada competirían por las
    mismas tablas."""
    import app.mel.models  # noqa: F401  (registra mel_executions antes de crear)

    Base.metadata.create_all(bind=engine)
    register_handlers()          # el cableado REAL al bus (idempotente)

    def _borra():
        with SessionLocal() as s:
            for modelo in (SkillEvent, Skill, LearnerProposal, ModelStat,
                           ToolStat, FailureStat, MissionVerdict, MissionEvent,
                           OrchestratorTrace):
                s.query(modelo).delete()
            s.query(Config).filter(Config.key.like("learner.%")).delete()
            s.commit()

    await _drena_tareas_del_bus()
    _borra()
    yield
    await _drena_tareas_del_bus()
    _borra()


@pytest.fixture(autouse=True)
def _sin_llm(monkeypatch):
    """EL ÚNICO DOBLE. Por defecto el modelo no está disponible — así queda
    claro que todo lo determinista del Learner funciona sin él. Los tests que
    necesitan una respuesta concreta la inyectan con `_responde()`."""
    async def _no_disponible(*a, **k):
        raise RuntimeError("sin proveedor (doble de test)")
    monkeypatch.setattr("app.mel.complete", _no_disponible)
    return monkeypatch


def _responde(monkeypatch, payload: str):
    class _Res:
        ok = True
        text = payload

    async def _r(*a, **k):
        return _Res()
    monkeypatch.setattr("app.mel.complete", _r)


# ---------------------------------------------------------------------------
# El simulador de una misión REAL
# ---------------------------------------------------------------------------
async def _mision(goal: str, *, ok: bool = True, tools: tuple = ("document",),
                  project_id: int = None, fallo: str = "",
                  path: str = "planned") -> Mission:
    """Ejecuta una misión de mentira por la maquinaria de verdad.

    Escribe la traza con la API del tracer, la telemetría con los hooks de
    producción y avisa por el bus real. Lo único que no ocurre es el trabajo en
    sí — que es justo lo que al Learner no le importa: él aprende del rastro."""
    mission = Mission(id=uuid.uuid4().hex, goal=goal, channel="hub",
                      project_id=project_id)
    trace_id = tracer.record_start(mission)          # fija el contexto de misión

    tracer.record_intent(trace_id, Intent(
        type=IntentType.EXECUTE, goal=goal, confidence=0.9,
        requires_tools=list(tools), requires_planning=True,
        model_capability="reason", raw_text=goal))

    nodo = TaskNode(id="n1", goal=goal, tools=list(tools))
    nodo.state = NodeState.DONE if ok else NodeState.FAILED
    nodo.tool_calls = [{"tool": t, "action": "run", "ok": ok} for t in tools]
    grafo = TaskGraph(id=uuid.uuid4().hex, mission_id=mission.id,
                      nodes={"n1": nodo},
                      authority={"project_id": project_id} if project_id else {})
    tracer.record_plan(trace_id, grafo)

    # El camino que tomó el turno (S3) — lo mira `mission_learning` para saber
    # si merece reflexión.
    import app.telemetry as _telemetry
    _telemetry.record("path", name=path, mission_id=mission.id, trace_id=trace_id)

    # --- La telemetría de la ejecución, por los HOOKS REALES ---
    from app.mel import executor as mel_exec
    from app.mel.contracts import Capability, ExecutionRequest, ModelRef

    req = ExecutionRequest(capability=Capability.REASON, prompt=goal)
    ref = ModelRef(provider="minimax", model="M3")
    if fallo == "red":
        # El MEL clasifica el fallo con SU vocabulario y L2b lo traduce: nadie
        # aquí escribe "connection" a mano.
        mel_exec._record_async(req, ref, ok=False, latency_ms=120,
                               fallback_reason="transient",
                               error="getaddrinfo failed")
    elif fallo == "config":
        from app.tie import toolloop
        mel_exec._record_async(req, ref, ok=True, latency_ms=90)
        toolloop._record_loop_event(
            "preflight_not_ready",
            {"tools": {"search": "añade una API key de SerpAPI o Brave en "
                                 "Ajustes → Búsqueda web"}})
    elif fallo == "modelo":
        from app.tie import toolloop
        mel_exec._record_async(req, ref, ok=True, latency_ms=90)
        toolloop._record_loop_event("stalled", {"vueltas": 4})
    else:
        mel_exec._record_async(req, ref, ok=True, latency_ms=90)

    mission.state = "done" if ok else "failed"
    tracer.record_end(trace_id, outcome="hecho" if ok else "no se pudo",
                      state=mission.state)

    # La telemetría es FIRE-AND-FORGET por diseño (`create_task` + `to_thread`:
    # nunca frena el camino caliente). En producción entre que una misión
    # termina y el Learner la analiza pasan segundos y eso da igual; aquí todo
    # ocurre en microsegundos, así que hay que esperar a que aterrice — o el
    # Learner leería un timeline a medio escribir. Se espera al EFECTO, no a un
    # reloj.
    await _espera(lambda: _telemetria_escrita(mission.id),
                  que=f"escribir la telemetría de «{goal[:40]}»")

    # --- El aviso por el BUS REAL: esto es lo que despierta al Learner ---
    if ok:
        tracer.emit_completed(mission, ok=True, nodes=1)
    else:
        tracer.emit_completed(mission, ok=False, nodes=1)
    return mission


async def _espera(condicion, *, segundos: float = 6.0, que: str = ""):
    """El Learner corre en una task de fondo (no bloquea al usuario, por
    diseño). Se espera a que termine mirando su EFECTO, no su reloj."""
    limite = asyncio.get_event_loop().time() + segundos
    while asyncio.get_event_loop().time() < limite:
        if await condicion():
            return True
        await asyncio.sleep(0.02)
    raise AssertionError(f"el Learner no llegó a: {que or condicion}")


async def _propuestas(kind=None):
    return await proposal_service.pending(kind=kind)


async def _repite(goal: str, veces: int = 3, **kw) -> list:
    """El mismo encargo, `veces` días distintos. Devuelve las misiones.

    [V1.1 LC2] Ya NO espera a que aparezca una propuesta: desde el rediseño,
    terminar una misión no abre nada en la bandeja. Repetir un encargo produce
    misiones; que eso se convierta en algo aprendido depende del JUEZ y de la
    consolidación — ver `_aprende_de`."""
    misiones = []
    for i in range(veces):
        misiones.append(await _mision(goal, **kw))
        await _espera(lambda n=i + 1: _trazas_cerradas(n),
                      que=f"cerrar la traza {i + 1}")
    return misiones


async def _juzga(misiones: list, monkeypatch, *, verdict: str = "served") -> None:
    """El juez de LC1, por su camino REAL, sobre misiones REALES.

    Un solo doble: la frontera del LLM. El grounding, la selección del juez y
    la persistencia son los de producción."""
    from app.learner import judge

    _responde(monkeypatch, json.dumps({
        "verdict": verdict, "confidence": 0.9,
        "reasons": "prueba de punta a punta",
        "evidence": ["outcome_text"],
        "lesson": {"type": "none", "content": ""}}))
    for m in misiones:
        await judge.judge_mission(m.id, force=True)


async def _aprende_de(misiones: list, monkeypatch, *, nombre: str,
                      pasos: list | None = None, tools: list | None = None) -> str:
    """La cadena NUEVA de punta a punta: misiones reales → veredictos reales →
    consolidación real → candidata en la bandeja.

    Es el reemplazo honesto del atajo viejo (`_repite` esperaba a que una
    propuesta apareciera sola porque la misión había TERMINADO). Ahora hace
    falta que las misiones hayan SERVIDO — que es justo el punto de doc 41."""
    from app.learner import consolidate

    await _juzga(misiones, monkeypatch)
    _responde(monkeypatch, json.dumps({"decisions": [{
        "action": "create_skill", "name": nombre,
        "description": nombre.lower(),
        "steps": pasos if pasos is not None else [],
        "tools": tools if tools is not None else ["document"],
        "mission_ids": [m.id for m in misiones],
        "why": "se ha hecho bien varias veces"}]}))
    r = await consolidate()
    assert r["created"], "la consolidación no creó la candidata esperada"
    return r["created"][0]


# ===========================================================================
# 1 · La semana normal: el usuario repite un encargo y Aithera se da cuenta
# ===========================================================================
class TestAprendeDeLoQueSeRepite:
    async def test_tres_encargos_juzgados_utiles_producen_una_candidata(self, monkeypatch):
        """LA HISTORIA COMPLETA de por qué existe el Learner, con el criterio
        de LC2: el usuario pide el resumen semanal tres lunes seguidos, las
        tres veces SIRVE, y al tercero la propuesta está esperando.

        La cadena entera y real: misión → traza → telemetría → bus → contadores
        (L2) → veredicto del juez (LC1) → consolidación (LC2) → escalera (L1).
        Único doble: la frontera del LLM."""
        _responde(monkeypatch,
                  '{"reflection": "Se preparó el resumen leyendo el proyecto.", '
                  '"repeatable": true, "skill_name": "Resumen semanal", '
                  '"skill_steps": ["reunir lo hecho", "redactar", "guardar"]}')

        misiones = await _repite("prepárame el resumen semanal del proyecto Aithera")
        assert await _propuestas("skill_new") == [], (
            "terminar tres misiones ya NO abre nada: hace falta que hayan servido")

        pid = await _aprende_de(misiones, monkeypatch, nombre="Resumen semanal",
                                pasos=["reunir lo hecho", "redactar"],
                                tools=["document"])
        cand = await proposal_service.get(pid)
        assert cand["state"] == "candidate", (
            f"a las {ladder.MIN_REP} misiones juzgadas útiles sube sola la escalera")
        assert cand["risk"] == "medium"
        assert {e["kind"] for e in cand["evidence"]} == {"judged_success"}

        # ...y lo determinista también quedó: los contadores.
        #
        # Se ESPERA al efecto: desde LC2, `_repite` solo espera a que las trazas
        # se cierren (que es lo que el usuario ve), y el Learner agrega en una
        # task de fondo. Dar por hecho que ya terminó sería medir un reloj en
        # vez de un resultado.
        await _espera(lambda: _contadas(3), que="agregar las 3 misiones")
        fila = model_ranking()[0]
        assert fila["missions"] == 3 and fila["missions_ok"] == 3
        assert fila["mission_success_rate"] == 1.0

    async def test_tres_encargos_juzgados_FALLIDOS_no_producen_nada(self, monkeypatch):
        """El caso Melendi, de punta a punta. Ocho peticiones seguidas porque
        ninguna funcionaba se leían como una costumbre; ahora la cadena entera
        se niega a convertirlas en un procedimiento."""
        from app.learner import consolidate

        _responde(monkeypatch, '{"reflection": "r", "repeatable": true, '
                               '"skill_name": "Poner música", "skill_steps": ["a"]}')
        misiones = await _repite("pon la canción de melendi", ok=False)
        await _juzga(misiones, monkeypatch, verdict="failed")

        # La IA ve los fallos y decide, correctamente, no proponer nada.
        _responde(monkeypatch, '{"decisions": []}')
        r = await consolidate()
        assert r["created"] == []
        assert await _propuestas("skill_new") == []

    async def test_la_reflexion_queda_enlazada_a_su_mision(self, monkeypatch):
        """El diario de trabajo: se puede volver a una misión y leer qué se
        pensó de ella (el delta #2 de doc 14 §4.1 existía justo para esto)."""
        _responde(monkeypatch, '{"reflection": "Salió bien y rápido.", '
                               '"repeatable": false, "skill_name": "", "skill_steps": []}')
        mision = await _mision("mira mi correo de esta mañana", tools=("email",))

        from app.services.decision_service import history

        await _espera(lambda: _hay_decision(mision.id), que="guardar la reflexión")
        decisiones = await history(mission_id=mision.id)
        assert decisiones and "Salió bien" in decisiones[0].body

    async def test_la_charla_trivial_no_gasta_ni_un_token(self, monkeypatch):
        """Reflexionar sobre "¿qué hora es?" es reflection theater (doc 15 §4).
        Los contadores sí corren — son gratis."""
        llamadas = []

        async def _cuenta(*a, **k):
            llamadas.append(1)
            raise RuntimeError("no debería llamarse")
        monkeypatch.setattr("app.mel.complete", _cuenta)

        await _mision("¿qué hora es?", path="chat", tools=())
        await _espera(lambda: _hay_contadores(), que="agregar los contadores")
        assert llamadas == [], "el camino corto no paga reflexión"


# ===========================================================================
# 2 · La justicia: de quién fue cada fallo
# ===========================================================================
class TestAtribuyeLosFallos:
    async def test_la_red_se_cae_y_el_modelo_no_paga_el_pato(self, monkeypatch):
        """EL CONTRATO Nº 5 DE LA FASE, de punta a punta y por los hooks de
        producción: el MEL clasifica el fallo con su vocabulario, L2b lo
        traduce, y el modelo sale con el 100% intacto."""
        _responde(monkeypatch, '{"reflection": "r", "repeatable": false, '
                               '"skill_name": "", "skill_steps": []}')
        await _mision("busca vuelos a Roma", tools=("search",))
        await _espera(lambda: _hay_contadores(), que="la primera misión")

        await _mision("busca hoteles en Roma", tools=("search",),
                      ok=False, fallo="red")
        await _espera(lambda: _fallos_registrados(), que="atribuir el fallo")

        fila = model_ranking()[0]
        assert fila["missions"] == 2 and fila["missions_excused"] == 1
        assert fila["mission_success_rate"] == 1.0, (
            "castigar al modelo por un timeout de DNS es medir ruido")
        assert failure_summary()["by_blame"].get("external") == 1

    async def test_el_modelo_se_atasca_y_eso_SI_cuenta(self, monkeypatch):
        """La otra mitad: excusar de más sería igual de falso que excusar de
        menos."""
        _responde(monkeypatch, '{"reflection": "r", "repeatable": false, '
                               '"skill_name": "", "skill_steps": []}')
        await _mision("resume este informe")
        await _espera(lambda: _hay_contadores(), que="la primera misión")

        await _mision("resume aquel otro informe", ok=False, fallo="modelo")
        await _espera(lambda: _fallos_registrados(), que="atribuir el atasco")

        fila = model_ranking()[0]
        assert fila["missions_excused"] == 0
        assert fila["mission_success_rate"] == 0.5, "aquí la culpa sí es suya"
        assert failure_summary()["by_blame"].get("model") == 1

    async def test_una_configuracion_que_falta_acaba_en_algo_que_hacer(self, monkeypatch):
        """El aprendizaje que de verdad le sirve al usuario: tres tropiezos con
        lo mismo y aparece una tarjeta que dice QUÉ configurar y DÓNDE — sin
        gastar un solo token, y sin poder aplicarse sola (configurar es suyo)."""
        _responde(monkeypatch, '{"reflection": "r", "repeatable": false, '
                               '"skill_name": "", "skill_steps": []}')
        # Uno cada vez, como un usuario real: el Learner digiere en tareas de
        # fondo y tres tropiezos simultáneos no son tres días distintos.
        for i in range(3):
            await _mision(f"búscame información sobre el tema {i}",
                          tools=("search",), fallo="config")
            await _espera(lambda n=i + 1: _fallos_contados(n),
                          que=f"contar el tropiezo {i + 1}")
        await _espera(lambda: _existe_propuesta("config_fix"),
                      que="proponer el arreglo de configuración")

        props = await _propuestas("config_fix")
        assert len(props) == 1, "una tarjeta por carencia, no una por tropiezo"
        assert props[0]["payload"]["settings_tab"] == "conexiones", (
            "un aviso sin destino es una queja: tiene que decir a dónde ir")
        assert props[0]["payload"]["component"] == "tool:search", (
            "y de qué herramienta hablamos")
        assert props[0]["risk"] == "low"
        assert "SerpAPI" in props[0]["summary"]

        from app.learner import registered_kinds
        assert "config_fix" not in registered_kinds(), (
            "sin applier: el panel ofrece 'Ir a Ajustes', no 'Aceptar'")


# ===========================================================================
# 3 · La madrugada: el análisis en batch
# ===========================================================================
class TestLaPasadaNocturna:
    async def test_la_madrugada_decide_con_veredictos_no_contando(self, monkeypatch):
        """[LC2] Lo que justifica que la pasada nocturna exista, con el criterio
        nuevo: tres misiones que el momento NO capturó siguen sin producir nada
        por sí solas — pero de madrugada, con los veredictos delante, la
        consolidación las convierte en una candidata."""
        _responde(monkeypatch, '{"reflection": "r", "repeatable": false, '
                               '"skill_name": "", "skill_steps": []}')
        misiones = await _repite("prepárame el informe mensual de gastos")
        assert await _propuestas("skill_new") == [], "el momento no lo vio"

        await _juzga(misiones, monkeypatch)
        _responde(monkeypatch, json.dumps({"decisions": [{
            "action": "create_skill", "name": "Informe mensual de gastos",
            "description": "informe mensual", "steps": [],
            "tools": ["document"],
            "mission_ids": [m.id for m in misiones],
            "why": "tres veces el mismo trabajo, y las tres sirvieron"}]}))

        resumen = await run_nightly_analysis()
        assert resumen["consolidation"]["created"], "la madrugada sí lo vio"
        cand = await _la_candidata()
        assert cand["state"] == "candidate"
        assert cand["payload"]["definition"]["steps"] == [], (
            "sin pasos observados no se inventan: eso lo escribe el usuario")

    async def test_el_informe_semanal_resume_lo_ocurrido(self, monkeypatch):
        """Sin modelo disponible (el doble por defecto): el informe sale igual
        porque la parte que importa es determinista."""
        _responde(monkeypatch, '{"reflection": "r", "repeatable": false, '
                               '"skill_name": "", "skill_steps": []}')
        await _mision("una tarea cualquiera")
        await _mision("otra que se cae", ok=False, fallo="red")
        await _espera(lambda: _fallos_registrados(), que="registrar el fallo")

        async def _sin_modelo(*a, **k):
            raise RuntimeError("sin proveedor")
        monkeypatch.setattr("app.mel.complete", _sin_modelo)

        resumen = await run_nightly_analysis()
        informe = resumen["report"]
        assert informe["headline"].startswith("Esta semana")
        assert informe["failures_by_blame"].get("external") == 1
        assert informe["findings"] == [], "sin modelo, sin autopsia — pero hay informe"

        from app.learner import last_report
        assert last_report()["generated_at"] == informe["generated_at"], (
            "queda guardado para el panel, sin recalcular")


# ===========================================================================
# 4 · El usuario decide: aceptar, y arrepentirse
# ===========================================================================
class TestElUsuarioManda:
    async def test_el_ciclo_entero_de_una_propuesta_aceptada_y_deshecha(self, monkeypatch):
        """LA PRUEBA DE FUEGO del organismo completo: de una repetición
        observada a una skill real en la biblioteca, y de vuelta.

        Encadena L2 (observar) → L1 (escalera + cuarentena + applier + undo).
        Y comprueba la promesa que hace que todo esto sea usable: que el
        usuario pueda arrepentirse."""
        _responde(monkeypatch,
                  '{"reflection": "r", "repeatable": true, '
                  '"skill_name": "Cerrar el mes", '
                  '"skill_steps": ["exportar", "cuadrar", "archivar"]}')
        misiones = await _repite("cierra el mes contable")
        pid = await _aprende_de(misiones, monkeypatch, nombre="Cerrar el mes",
                                pasos=["exportar", "cuadrar", "archivar"],
                                tools=["document"])

        prop = await proposal_service.get(pid)
        assert prop["state"] == "candidate"

        # Nada se aplica desde 'candidate': hay que subir el peldaño explícito.
        with pytest.raises(ValueError):
            await proposal_service.apply(prop["id"])

        await proposal_service.promote_to_proposed(prop["id"])
        await proposal_service.approve(prop["id"], note="sí, hazlo")
        aplicada = await proposal_service.apply(prop["id"])
        assert aplicada["state"] == "consolidated"

        skills = await skill_library.list()
        assert len(skills) == 1
        assert skills[0].name == "Cerrar el mes"
        assert skills[0].status.value == "draft", (
            "ni siquiera aceptada nace activa: la escalera sigue mandando")

        # ...y el arrepentimiento.
        await proposal_service.undo(prop["id"])
        final = await proposal_service.get(prop["id"])
        assert final["state"] == "reverted"
        assert (await skill_library.get(skills[0].id)).status.value == "deprecated", (
            "deshacer depreca, nunca borra: la historia no se tira")
        historial = await skill_library.history(skills[0].id)
        assert any(e["event"] == "deprecated" for e in historial)

    async def test_el_learner_no_escribio_fuera_de_su_casa(self, monkeypatch):
        """El invariante constitucional (doc 15), medido sobre la simulación
        entera: tras una semana de aprender, aceptar y deshacer, NINGUNA tabla
        ajena al Learner cambió de tamaño."""
        _responde(monkeypatch, '{"reflection": "r", "repeatable": true, '
                               '"skill_name": "x", "skill_steps": ["a"]}')
        propias = {"skills", "skill_events", "learner_proposals", "model_stats",
                   "tool_stats", "failure_stats", "mission_verdicts",
                   # lo que escribe el RASTRO de la simulación, no el Learner:
                   # las trazas y la telemetría las pone el TIE/MEL al trabajar,
                   # las decisiones son la API por la que el Learner SÍ puede
                   # escribir (doc 15), y `config` guarda el informe semanal.
                   "orchestrator_traces", "mission_events", "mel_executions",
                   "decisions", "config"}

        def _censo():
            with SessionLocal() as s:
                out = {}
                for tabla in Base.metadata.tables:
                    if tabla in propias:
                        continue
                    try:
                        out[tabla] = s.execute(
                            __import__("sqlalchemy").text(
                                f"SELECT COUNT(*) FROM {tabla}")).scalar()
                    except Exception:
                        pass
                return out

        antes = _censo()
        misiones = await _repite("una tarea que se repite")
        pid = await _aprende_de(misiones, monkeypatch, nombre="Tarea repetida")
        prop = await proposal_service.get(pid)
        await proposal_service.promote_to_proposed(prop["id"])
        await proposal_service.approve(prop["id"])
        await proposal_service.apply(prop["id"])
        await run_nightly_analysis()

        assert _censo() == antes, (
            "el Learner observa y propone; no toca el mundo de nadie más")


# ===========================================================================
# 5 · "Aprende esto": la vía del usuario, en la misma cuarentena
# ===========================================================================
class TestElUsuarioEnsena:
    async def test_lo_ensenado_y_lo_observado_conviven_igual(self, monkeypatch):
        """Las dos direcciones del aprendizaje acaban en el mismo sitio y con
        el mismo estado. Lo que cambia es la PROVENANCE, que se conserva para
        que el panel pueda decir quién enseñó qué."""
        _responde(monkeypatch, '{"name": "Cerrar el mes", "description": "cierre", '
                               '"steps": ["exportar", "cuadrar"], "confident": true}')
        res = await learn_this("para cerrar el mes exporto los movimientos y los "
                               "cuadro con el banco antes de archivar")
        assert res.ok

        _responde(monkeypatch, '{"reflection": "r", "repeatable": true, '
                               '"skill_name": "Otra cosa", "skill_steps": ["a"]}')
        misiones = await _repite("hazme otra cosa distinta")
        pid = await _aprende_de(misiones, monkeypatch, nombre="Otra cosa")
        prop = await proposal_service.get(pid)
        await proposal_service.promote_to_proposed(prop["id"])
        await proposal_service.approve(prop["id"])
        await proposal_service.apply(prop["id"])

        skills = {s.name: s for s in await skill_library.list()}
        assert set(skills) == {"Cerrar el mes", "Otra cosa"}
        assert all(s.status.value == "draft" for s in skills.values()), (
            "la misma puerta para las dos")
        assert skills["Cerrar el mes"].created_by == "user_taught"
        # [LC2] La provenance de lo OBSERVADO pasa de `local_learning_loop` (la
        # acumulación mecánica, retirada) a `consolidation`: quien decidió que
        # esto merecía ser una skill fue la consolidación nocturna, leyendo
        # veredictos. Lo que el test defiende —que se sepa quién enseñó qué—
        # sigue intacto; lo que cambia es que ahora dice la verdad.
        assert skills["Otra cosa"].created_by == "consolidation"

    async def test_por_la_tool_real_que_usa_el_chat(self, monkeypatch):
        """El cableado de verdad: `aithera.learn_skill`, que es por donde llega
        cuando el usuario lo dice hablando."""
        from app.tools.aithera_tool import AitheraTool

        _responde(monkeypatch, '{"name": "Preparar la reunión", "description": "d", '
                               '"steps": ["revisar agenda", "sacar notas"], '
                               '"confident": true}')
        out = await AitheraTool().execute("learn_skill", {
            "notes": "antes de cada reunión reviso la agenda y saco las notas "
                     "de la anterior para tenerlas a mano",
            "source": "conversación"})
        assert out["success"]
        skill = await skill_library.get(out["result"]["skill_id"])
        assert skill.status.value == "draft" and skill.created_by == "user_taught"


# ===========================================================================
# 6 · EL JUEZ EN LA CADENA REAL (V1.1 LC1, doc 41)
# ===========================================================================
class TestElJuezEntraEnLaCadena:
    """La pieza nueva, probada por donde de verdad entra: el bus.

    Hasta LC1 el Learner leía `state="done"` y lo tomaba por éxito. Aquí se
    comprueba que el veredicto llega por la MISMA vía que todo lo demás (el
    evento real `mission.completed` → el handler real del juez), y que
    `served()` es fail-closed mientras no haya juicio."""

    async def test_el_juez_esta_suscrito_de_verdad(self, monkeypatch):
        """La comprobación anti-"correcto pero desconectado" (el modo de fallo
        que ya ha aparecido cinco veces en este proyecto): no basta con que el
        juez funcione — tiene que ESTAR ENCHUFADO al bus."""
        from app.learner import judge, register_judge

        register_judge()                     # idempotente, como en el lifespan
        judge._cola.clear()

        m = await _mision("prepara el informe del trimestre")
        await _espera(_encolada, que="que el juez encole la misión terminada")
        assert m.id in judge._cola

    async def test_del_evento_al_veredicto_sin_atajos(self, monkeypatch):
        """La cadena entera: misión real → traza real → evento real → cola del
        juez → veredicto en la BD. El único doble sigue siendo el LLM."""
        from app.learner import judge, register_judge, served

        register_judge()
        judge._cola.clear()
        m = await _mision("busca las facturas del mes y hazme el resumen")

        assert served(m.id) is False, "sin juicio no puede constar que sirvió"

        _responde(monkeypatch, '{"verdict": "served", "confidence": 0.85, '
                               '"reasons": "Terminó y el usuario no corrigió.", '
                               '"evidence": ["outcome_text"], '
                               '"lesson": {"type": "none", "content": ""}}')
        await _espera(_encolada, que="encolar")
        assert await judge.drain_now() >= 1
        assert served(m.id) is True

    async def test_el_juez_no_es_quien_falla_al_aprender(self, monkeypatch):
        """Un juez caído no puede tumbar nada. Sin veredicto, el Learner
        simplemente no cuenta con esa misión — que es la respuesta honesta."""
        from app.learner import judge, register_judge, served

        register_judge()
        judge._cola.clear()
        m = await _mision("algo que hacer")
        # `_sin_llm` (la fixture) deja `mel.complete` lanzando: el juez falla.
        await _espera(_encolada, que="encolar")
        assert await judge.drain_now() == 0
        assert served(m.id) is False
        # Y lo determinista de L2 siguió su curso pese a todo.
        await _espera(_hay_contadores, que="los contadores de siempre")


# ---------------------------------------------------------------------------
# helpers de espera (miran EFECTOS, no relojes)
# ---------------------------------------------------------------------------
async def _encolada() -> bool:
    """El juez ha recibido la misión por el bus y la tiene esperando turno."""
    from app.learner import judge

    return judge.pending_count() >= 1


async def _existe_propuesta(kind: str) -> bool:
    return bool(await proposal_service.pending(kind=kind))


async def _la_candidata(kind: str = "skill_new") -> dict:
    """La propuesta con MÁS evidencia de su tipo.

    No `[0]` a propósito: el Learner trabaja en tareas de fondo (no bloquea al
    usuario, por diseño) y una de un test anterior puede aterrizar después de
    que este haya limpiado, dejando una propuesta huérfana más nueva. Mirar la
    que de verdad ha acumulado hace estos tests independientes del orden en que
    pytest los ejecute — que es como deben ser."""
    props = await proposal_service.pending(kind=kind)
    return max(props, key=lambda p: len(p["evidence"])) if props else {}


async def _evidencias(kind: str, n: int) -> bool:
    cand = await _la_candidata(kind)
    return bool(cand) and len(cand["evidence"]) >= n


async def _contadas(n: int) -> bool:
    """Al menos `n` misiones ya agregadas en `model_stats`."""
    filas = model_ranking()
    return bool(filas) and int(filas[0]["missions"]) >= n


async def _hay_contadores() -> bool:
    with SessionLocal() as s:
        return s.query(ModelStat).count() > 0


async def _fallos_registrados() -> bool:
    with SessionLocal() as s:
        return s.query(FailureStat).count() > 0


async def _fallos_contados(n: int) -> bool:
    """Que la MISMA carencia lleve ya `n` tropiezos contados."""
    with SessionLocal() as s:
        fila = s.query(FailureStat).filter(FailureStat.blame == "config").first()
    return bool(fila) and int(fila.count or 0) >= n


async def _trazas_cerradas(n: int) -> bool:
    """Trazas TERMINADAS, salgan bien o mal. `_misiones_en_traza` solo cuenta
    las `done`, y desde LC2 hay tests que repiten un encargo que FALLA — con el
    filtro de éxito, esa espera no se cumpliría nunca."""
    with SessionLocal() as s:
        return s.query(OrchestratorTrace).filter(
            OrchestratorTrace.state.in_(("done", "failed", "cancelled"))).count() >= n


async def _misiones_en_traza(n: int) -> bool:
    with SessionLocal() as s:
        return s.query(OrchestratorTrace).filter(
            OrchestratorTrace.state == "done").count() >= n


async def _hay_decision(mission_id: str) -> bool:
    from app.services.decision_service import history

    return bool(await history(mission_id=mission_id))


async def _telemetria_escrita(mission_id: str) -> bool:
    """La llamada al modelo y el camino, ya en la BD: es lo que el Learner
    necesita leer para agregar contadores y atribuir el fallo."""
    with SessionLocal() as s:
        etapas = {r[0] for r in s.query(MissionEvent.stage)
                  .filter(MissionEvent.mission_id == mission_id).all()}
    return {"llm_call", "path"} <= etapas
