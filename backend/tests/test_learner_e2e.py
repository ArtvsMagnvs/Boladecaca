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
from app.learner.models import FailureStat, LearnerProposal, ModelStat, Skill, SkillEvent, ToolStat
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
                           ToolStat, FailureStat, MissionEvent, OrchestratorTrace):
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


async def _repite(goal: str, veces: int = 3, **kw):
    """El mismo encargo, `veces` días distintos — esperando a que el Learner
    digiera cada uno antes del siguiente.

    NO es cosmética: el Learner corre en tareas de fondo, y si dos misiones del
    mismo trabajo terminan a la vez, las dos leen la bandeja antes de que
    ninguna haya escrito y cada una crea su propuesta. En producción eso es
    benigno y raro (el análisis nocturno de L3 las reconcilia con `same_work`,
    y dos personas no piden lo mismo el mismo milisegundo), pero simular un
    usuario que pregunta tres veces de golpe no sería simular un usuario."""
    for i in range(veces):
        await _mision(goal, **kw)
        await _espera(lambda n=i + 1: _evidencias("skill_new", n),
                      que=f"digerir la repetición {i + 1}")


# ===========================================================================
# 1 · La semana normal: el usuario repite un encargo y Aithera se da cuenta
# ===========================================================================
class TestAprendeDeLoQueSeRepite:
    async def test_tres_veces_el_mismo_encargo_produce_una_candidata(self, monkeypatch):
        """LA HISTORIA COMPLETA de por qué existe el Learner. El usuario pide
        el resumen semanal tres lunes seguidos, con otras palabras cada vez.
        Nadie le dice nada a Aithera: al tercero, la propuesta está esperando.

        Encadena L2 (reflexión + acumulación) con L1 (la escalera) sobre
        misiones, trazas, telemetría y bus REALES."""
        _responde(monkeypatch,
                  '{"reflection": "Se preparó el resumen leyendo el proyecto.", '
                  '"repeatable": true, "skill_name": "Resumen semanal", '
                  '"skill_steps": ["reunir lo hecho", "redactar", "guardar"]}')

        await _mision("prepárame el resumen semanal del proyecto Aithera")
        await _espera(lambda: _existe_propuesta("skill_new"),
                      que="crear la primera observación")
        assert (await _la_candidata())["state"] == "observed", (
            "una vez no es un patrón")

        await _mision("quiero el resumen semanal para el proyecto Aithera")
        await _espera(lambda: _evidencias("skill_new", 2), que="sumar la 2.ª")
        assert (await _la_candidata())["state"] == "observed"

        await _mision("hazme el resumen semanal del proyecto Aithera")
        await _espera(lambda: _evidencias("skill_new", 3), que="sumar la 3.ª")

        cand = await _la_candidata()
        assert cand["state"] == "candidate", (
            f"a las {ladder.MIN_REP} veces sube sola la escalera")
        assert cand["risk"] == "medium"

        # ...y lo determinista también quedó: los contadores.
        fila = model_ranking()[0]
        assert fila["missions"] == 3 and fila["missions_ok"] == 3
        assert fila["mission_success_rate"] == 1.0

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
    async def test_ve_lo_que_ninguna_mision_suelta_pudo_ver(self, monkeypatch):
        """El caso que justifica que L3 exista: tres misiones que el momento
        NO capturó (el modelo dijo `repeatable=false` cada vez, que es lo que
        pasa cuando falla el clasificador). De madrugada, contando, el patrón
        salta igual."""
        _responde(monkeypatch, '{"reflection": "r", "repeatable": false, '
                               '"skill_name": "", "skill_steps": []}')
        for _ in range(3):
            await _mision("prepárame el informe mensual de gastos")
        await _espera(lambda: _misiones_en_traza(3), que="cerrar las 3 trazas")
        assert await _propuestas("skill_new") == [], "el momento no lo vio"

        resumen = await run_nightly_analysis()
        assert resumen["repeated"], "la madrugada sí"
        cand = await _la_candidata()
        assert cand["state"] == "candidate"
        assert cand["payload"]["definition"]["steps"] == [], (
            "no se inventa los pasos: eso lo escribe el usuario al aceptarla")

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
        await _repite("cierra el mes contable")

        prop = await _la_candidata()
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
                   "tool_stats", "failure_stats",
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
        await _repite("una tarea que se repite")
        prop = await _la_candidata()
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
        await _repite("hazme otra cosa distinta")
        prop = await _la_candidata()
        await proposal_service.promote_to_proposed(prop["id"])
        await proposal_service.approve(prop["id"])
        await proposal_service.apply(prop["id"])

        skills = {s.name: s for s in await skill_library.list()}
        assert set(skills) == {"Cerrar el mes", "Otra cosa"}
        assert all(s.status.value == "draft" for s in skills.values()), (
            "la misma puerta para las dos")
        assert skills["Cerrar el mes"].created_by == "user_taught"
        assert skills["Otra cosa"].created_by == "local_learning_loop"

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


# ---------------------------------------------------------------------------
# helpers de espera (miran EFECTOS, no relojes)
# ---------------------------------------------------------------------------
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
