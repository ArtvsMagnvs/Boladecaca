# tests/test_lc1_juez.py — EL JUEZ (V1.1 LC1, doc 41)
#
# Lo que estos tests defienden, en una frase: que Aithera no vuelva a aprender
# de sus propios fracasos.
#
# El caso que abre el archivo es el real (doc 41 §0): el usuario pidió ocho
# veces seguidas "pon la canción de Melendi" — ocho veces porque ninguna
# funcionó — y el Learner lo interpretó como una costumbre y propuso
# convertirlo en procedimiento fijo. La señal que lo delata ("me lo volvieron a
# pedir tres minutos después, corrigiendo") existía en la base de datos y nadie
# la miraba.
#
# UN SOLO DOBLE, la frontera del LLM (`app.mel.complete`) — patrón S4, doc 27
# §3. La BD, el tracer, la telemetría, el empaquetador de señales y el
# grounding son los REALES: si alguna de esas piezas se desconecta de otra,
# esto se cae. Es el modo de fallo que ya ha aparecido cinco veces en este
# proyecto (lógica correcta y desconectada).
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta

import pytest

from app.core import corpus
from app.db.database import Base, ChatMessage, OrchestratorTrace, SessionLocal, engine
from app.learner import judge, signals
from app.learner.models import MissionVerdict
from app.mel.contracts import Capability, ModelRef
from app.mel.policies import is_capable
from app.telemetry.models import MissionEvent
from app.tie import tracer
from app.tie.contracts import Intent, IntentType, Mission, NodeState, TaskGraph, TaskNode

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _mundo_limpio():
    """Se limpia al ENTRAR y al SALIR. Al entrar también, porque
    `mission_verdicts`/`orchestrator_traces` son tablas globales que otros
    archivos de test escriben sin conocer esta fixture (la lección de L2b y de
    A4: limpiar solo al salir deja que el residuo del archivo anterior se cuele
    en el primer test de éste)."""
    Base.metadata.create_all(bind=engine)

    def _borra():
        with SessionLocal() as s:
            for modelo in (MissionVerdict, MissionEvent, OrchestratorTrace, ChatMessage):
                s.query(modelo).delete()
            s.commit()

    _borra()
    corpus.reset_cache()
    os.environ.pop(corpus.ENV_FLAG, None)
    yield
    _borra()
    os.environ.pop(corpus.ENV_FLAG, None)
    corpus.reset_cache()


def _responde(monkeypatch, payload, modelo: str = "ollama:deepseek-r1:8b",
              registro: list | None = None):
    """El único doble: la frontera del LLM. `registro` captura la petición para
    poder comprobar qué se le pidió al MEL (p. ej. a quién excluyó)."""
    class _Servido:
        def __init__(self, key):
            self.provider, self.model = key.split(":", 1)

    class _Res:
        ok = True

        def __init__(self, texto, key):
            self.text = texto
            self.served_by = _Servido(key)

    texto = payload if isinstance(payload, str) else json.dumps(payload)

    async def _r(req, *a, **k):
        if registro is not None:
            registro.append(req)
        return _Res(texto, modelo)

    monkeypatch.setattr("app.mel.complete", _r)


# ---------------------------------------------------------------------------
# El simulador: una misión real, escrita por la maquinaria real
# ---------------------------------------------------------------------------
def _mision(goal: str, *, ok: bool = True, outcome: str = "hecho",
            session_id: str | None = None, node_output: str = "",
            targets: tuple = (), source: str = "user") -> Mission:
    m = Mission(id=uuid.uuid4().hex, goal=goal, channel="hub",
                session_id=session_id, source=source)
    trace_id = tracer.record_start(m)
    tracer.record_intent(trace_id, Intent(
        type=IntentType.EXECUTE, goal=goal, confidence=0.9,
        requires_tools=["browser"], requires_planning=True, raw_text=goal))

    nodo = TaskNode(id="n1", goal=goal, tools=["browser"])
    nodo.state = NodeState.DONE if ok else NodeState.FAILED
    nodo.tool_calls = [{"tool": "browser", "action": "play_media", "ok": ok}]
    for ruta in targets:
        nodo.tool_calls.append({"tool": "filesystem", "action": "write_file",
                                "ok": True, "target": ruta})
    if node_output:
        nodo.result = {"output": node_output}
    tracer.record_plan(trace_id, TaskGraph(id=uuid.uuid4().hex, mission_id=m.id,
                                           nodes={"n1": nodo}))
    m.state = "done" if ok else "failed"
    tracer.record_end(trace_id, outcome=outcome, state=m.state)
    m.trace_id = trace_id
    return m


async def _espera_telemetria(mission_id: str, segundos: float = 3.0) -> None:
    """La telemetría es fire-and-forget por diseño (`create_task` + `to_thread`:
    nunca frena el camino caliente). Hay que esperar al EFECTO, y hay que
    hacerlo con `asyncio.sleep` — un `time.sleep` dentro de un test async
    BLOQUEA el event loop, así que la tarea que escribe la telemetría no
    llegaría a correr nunca y la espera sería un cuelgue garantizado."""
    import asyncio

    limite = asyncio.get_event_loop().time() + segundos
    while asyncio.get_event_loop().time() < limite:
        if signals._from_timeline(mission_id)["llm_calls"]:
            return
        await asyncio.sleep(0.01)


def _turno(session_id: str, texto: str, cuando: datetime, rol: str = "user") -> None:
    with SessionLocal() as s:
        s.add(ChatMessage(role=rol, content=texto, session_id=session_id,
                          created_at=cuando))
        s.commit()


# ===========================================================================
# 1 · EL CASO MELENDI — el fallo que abre doc 41
# ===========================================================================
async def test_caso_melendi_el_juez_ve_que_se_lo_volvieron_a_pedir(monkeypatch):
    """La regresión EXACTA del post-mortem.

    Ocho peticiones casi idénticas seguidas no son una costumbre: son ocho
    intentos porque ninguno funcionó. El sistema mecánico veía `state="done"`
    ocho veces y proponía un procedimiento. Aquí se comprueba que esa señal —"me
    lo volvieron a pedir, corrigiendo"— LLEGA al juez, que es lo que le permite
    entenderlo como lo entendería una persona."""
    sid = "sesion-melendi"
    m = _mision("pon la cancion de melendi", session_id=sid,
                outcome="He puesto la canción de Melendi.")

    # Lo que pasó DESPUÉS, que es donde estaba la verdad todo el tiempo.
    ahora = datetime.utcnow()
    _turno(sid, "no ha sonado nada, ponla otra vez", ahora + timedelta(minutes=3))
    _turno(sid, "pon la cancion de melendi", ahora + timedelta(minutes=4))

    paquete = signals.collect(m.id)
    assert paquete is not None
    despues = paquete["aftermath"]
    assert despues["available"] is True
    assert despues["repeats"] >= 1, "no se detectó que volvieran a pedir lo mismo"
    assert despues["minutes_to_repeat"] is not None
    textos = " ".join(x["text"] for x in despues["next_messages"])
    assert "otra vez" in textos, "el juez no ve la corrección del usuario"

    # Y con esa señal delante, un juez que dictamina `failed` queda registrado
    # como tal: nada mecánico lo promociona (regla 3, doc 41 §5).
    _responde(monkeypatch, {
        "verdict": "failed", "confidence": 0.9,
        "reasons": "El usuario dijo que no había sonado y volvió a pedirlo.",
        "evidence": ["user_followup", "repeated_request"],
        "lesson": {"type": "none", "content": ""},
    })
    assert await judge.judge_mission(m.id)
    v = judge.verdict_of(m.id)
    assert v["verdict"] == "failed"
    assert judge.served(m.id) is False


async def test_sin_veredicto_no_consta_que_sirviera():
    """Fail-closed, la regla que sustituye a `state == "done"`.

    Una misión terminada sin colgarse NO es una misión que sirvió. Que
    `served()` devuelva False mientras no haya juicio es lo correcto: no saber
    si algo funcionó no es lo mismo que saber que funcionó, y confundir las dos
    cosas es literalmente el bug que cierra esta sesión."""
    m = _mision("lo que sea")
    assert judge.verdict_of(m.id) is None
    assert judge.served(m.id) is False


# ===========================================================================
# 2 · EL GROUNDING DEL JUEZ (§3.5) — lo mecánico solo QUITA confianza
# ===========================================================================
async def test_served_sin_evidencia_citable_se_degrada_a_unclear(monkeypatch):
    """Un `served` que no se apoya en ninguna señal del paquete no vale.

    El control de un LLM no puede ser otro LLM (regresión infinita), así que es
    un chequeo determinista y mínimo — el mismo principio que el grounding del
    responder (S2·S6)."""
    m = _mision("haz algo")
    _responde(monkeypatch, {
        "verdict": "served", "confidence": 0.95,
        "reasons": "Salió perfecto.",
        "evidence": [],                      # ← ninguna señal
        "lesson": {"type": "none", "content": ""},
    })
    await judge.judge_mission(m.id)
    v = judge.verdict_of(m.id)
    assert v["verdict"] == "unclear"
    assert "sin evidencia citable" in v["reasons"]
    assert v["confidence"] <= 0.3


async def test_served_con_evidencia_inventada_tambien_se_degrada(monkeypatch):
    """Citar señales que no existen es igual de malo que no citar ninguna."""
    m = _mision("haz algo")
    _responde(monkeypatch, {
        "verdict": "served", "confidence": 0.9, "reasons": "Confía en mí.",
        "evidence": ["el_usuario_aplaudio", "todo_perfecto"],
        "lesson": {"type": "none", "content": ""},
    })
    await judge.judge_mission(m.id)
    assert judge.verdict_of(m.id)["verdict"] == "unclear"


async def test_un_failed_nunca_se_promociona(monkeypatch):
    """La asimetría es deliberada: lo mecánico puede quitar confianza, jamás
    ponerla. No existe ningún camino por el que un `failed` suba a `served`."""
    m = _mision("haz algo", ok=False, outcome="no se pudo")
    _responde(monkeypatch, {"verdict": "failed", "confidence": 0.1,
                            "reasons": "Falló.", "evidence": [],
                            "lesson": {"type": "none", "content": ""}})
    await judge.judge_mission(m.id)
    assert judge.verdict_of(m.id)["verdict"] == "failed"


async def test_served_con_entregable_en_disco_se_respeta(monkeypatch, tmp_path):
    """El contrario: cuando la evidencia SÍ existe, el veredicto del juez se
    respeta tal cual. El grounding no es un filtro pesimista, es un chequeo."""
    archivo = tmp_path / "plan.md"
    archivo.write_text("contenido real", encoding="utf-8")
    m = _mision("escribe el plan", outcome="He escrito plan.md con el plan.",
                targets=(str(archivo),))

    paquete = signals.collect(m.id)
    assert str(archivo) in paquete["deliverables"]["on_disk"]
    assert "deliverable_on_disk" in signals.citable_ids(paquete)

    _responde(monkeypatch, {
        "verdict": "served", "confidence": 0.9,
        "reasons": "El archivo existe en disco.",
        "evidence": ["deliverable_on_disk"],
        "lesson": {"type": "none", "content": ""}})
    await judge.judge_mission(m.id)
    assert judge.verdict_of(m.id)["verdict"] == "served"
    assert judge.served(m.id) is True


# ===========================================================================
# 3 · ANTI-SESGO: el juez nunca es el ejecutor (§5 regla 1)
# ===========================================================================
async def test_el_juez_pide_excluir_a_los_modelos_que_ejecutaron(monkeypatch):
    """Nadie corrige su propio examen. El MEL ya sabe saltar candidatos
    (`exclude`, estrenado por el auto-catálogo de E1b por este mismo motivo);
    aquí se comprueba que el juez lo USA de verdad."""
    m = _mision("haz algo")
    # La telemetría dice quién ejecutó — por el hook real del MEL.
    from app.mel import executor as mel_exec
    from app.mel.contracts import ExecutionRequest

    import app.telemetry as _telemetry
    _telemetry.set_mission(m.id, m.trace_id)
    mel_exec._record_async(ExecutionRequest(capability=Capability.REASON, prompt="x"),
                           ModelRef(provider="minimax", model="M3"),
                           ok=True, latency_ms=50)
    _telemetry.set_mission(None, None)

    await _espera_telemetria(m.id)

    peticiones: list = []
    _responde(monkeypatch, {"verdict": "unclear", "confidence": 0.5,
                            "reasons": "-", "evidence": [],
                            "lesson": {"type": "none", "content": ""}},
              modelo="ollama:deepseek-r1:8b", registro=peticiones)
    await judge.judge_mission(m.id)
    assert peticiones, "el juez no llegó a llamar al MEL"
    assert "minimax:M3" in peticiones[0].exclude, (
        "el juez no excluyó al modelo que ejecutó la misión")
    assert judge.verdict_of(m.id)["judge_bias"] is False


async def test_si_no_hay_juez_alternativo_se_marca_el_sesgo(monkeypatch):
    """Si el único modelo apto es el que ejecutó, se juzga igual — pero
    MARCADO. Nunca en silencio: un veredicto sesgado sigue siendo información,
    un veredicto sesgado disfrazado de imparcial es una mentira."""
    m = _mision("haz algo")
    from app.mel import executor as mel_exec
    from app.mel.contracts import ExecutionRequest

    import app.telemetry as _telemetry
    _telemetry.set_mission(m.id, m.trace_id)
    mel_exec._record_async(ExecutionRequest(capability=Capability.REASON, prompt="x"),
                           ModelRef(provider="ollama", model="deepseek-r1:8b"),
                           ok=True, latency_ms=50)
    _telemetry.set_mission(None, None)

    await _espera_telemetria(m.id)

    _responde(monkeypatch, {"verdict": "unclear", "confidence": 0.4,
                            "reasons": "-", "evidence": [],
                            "lesson": {"type": "none", "content": ""}},
              modelo="ollama:deepseek-r1:8b")
    await judge.judge_mission(m.id)
    assert judge.verdict_of(m.id)["judge_bias"] is True


# ===========================================================================
# 4 · HIGIENE DEL CORPUS (§6) — no se aprende del banco de pruebas
# ===========================================================================
async def test_una_mision_de_pruebas_no_gasta_una_llamada_al_juez(monkeypatch):
    """Con la marca de corpus de prueba puesta, la misión nace `origin=test` y
    se archiva como `unclear` SIN llamar a ningún modelo. Registrada (auditable)
    pero fuera del aprendizaje: ningún sistema serio aprende de su propio banco
    de pruebas."""
    os.environ[corpus.ENV_FLAG] = "1"
    corpus.reset_cache()
    m = _mision("test-campanya 01: abre una web")

    llamadas: list = []
    _responde(monkeypatch, {"verdict": "served", "confidence": 1.0,
                            "reasons": "-", "evidence": ["outcome_text"],
                            "lesson": {"type": "none", "content": ""}},
              registro=llamadas)
    assert await judge.judge_mission(m.id)
    assert llamadas == [], "se gastó una llamada al modelo en corpus de pruebas"
    v = judge.verdict_of(m.id)
    assert v["origin"] == "test"
    assert v["verdict"] == "unclear"
    assert judge.served(m.id) is False


async def test_el_origen_queda_escrito_en_la_traza():
    """El origen se decide al CREAR la misión, no después: la marca la pone el
    entorno que lanza el trabajo y de madrugada ya no existe."""
    m1 = _mision("trabajo de verdad")
    os.environ[corpus.ENV_FLAG] = "e2e"
    corpus.reset_cache()
    m2 = _mision("trabajo de un test")
    os.environ.pop(corpus.ENV_FLAG)
    corpus.reset_cache()

    assert tracer.mission_snapshot(m1.id)["origin"] == "user"
    assert tracer.mission_snapshot(m2.id)["origin"] == "e2e"


async def test_las_misiones_de_prueba_no_entran_en_la_cola_de_juicio():
    """`unjudged` es lo que alimenta el catch-up y el backfill: si dejara pasar
    el corpus de pruebas, la contaminación volvería por la puerta de atrás."""
    real = _mision("trabajo de verdad")
    os.environ[corpus.ENV_FLAG] = "1"
    corpus.reset_cache()
    prueba = _mision("prueba automatizada")
    os.environ.pop(corpus.ENV_FLAG)
    corpus.reset_cache()

    pendientes = judge.unjudged(limit=50)
    assert real.id in pendientes
    assert prueba.id not in pendientes


# ===========================================================================
# 5 · CATCH-UP Y BACKFILL
# ===========================================================================
async def test_juzgar_es_idempotente(monkeypatch):
    """Juzgar dos veces la misma misión no crea dos veredictos. Importa porque
    la cola, el catch-up y el backfill pueden apuntar a la misma misión."""
    m = _mision("haz algo")
    _responde(monkeypatch, {"verdict": "partial", "confidence": 0.6,
                            "reasons": "-", "evidence": ["outcome_text"],
                            "lesson": {"type": "none", "content": ""}})
    assert await judge.judge_mission(m.id)
    assert await judge.judge_mission(m.id) is None
    with SessionLocal() as s:
        assert s.query(MissionVerdict).filter(
            MissionVerdict.mission_id == m.id).count() == 1


async def test_el_backfill_recupera_lo_no_juzgado_y_no_repite(monkeypatch):
    """La pasada nocturna deja el histórico con veredictos de verdad, y
    ejecutarla dos veces no duplica nada."""
    ms = [_mision(f"encargo {i}") for i in range(3)]
    _responde(monkeypatch, {"verdict": "served", "confidence": 0.8,
                            "reasons": "-", "evidence": ["outcome_text"],
                            "lesson": {"type": "none", "content": ""}})

    r1 = await judge.run_nightly_judging()
    assert r1["judged"] == 3
    for m in ms:
        assert judge.verdict_of(m.id) is not None

    r2 = await judge.run_nightly_judging()
    assert r2["judged"] == 0, "el backfill volvió a juzgar lo ya juzgado"


async def test_la_cola_encola_y_drena(monkeypatch):
    """La cola existe para que el juicio NUNCA toque el camino caliente. El
    retardo es deliberado (hace falta que exista "el después"); `drain_now` es
    lo que permite forzarlo en tests y en el cierre ordenado."""
    m = _mision("haz algo")
    judge.enqueue(m.id, delay_min=999)       # nunca le tocaría por su cuenta
    assert judge.pending_count() == 1
    _responde(monkeypatch, {"verdict": "unclear", "confidence": 0.5,
                            "reasons": "-", "evidence": [],
                            "lesson": {"type": "none", "content": ""}})
    assert await judge.drain_now() == 1
    assert judge.pending_count() == 0
    assert judge.verdict_of(m.id) is not None


# ===========================================================================
# 6 · SEÑALES DURAS: que lleguen de verdad, no que "existan"
# ===========================================================================
async def test_la_rendicion_llega_al_paquete():
    """NEW-4 detecta rendiciones; aquí se comprueba que el juez las VE. Una
    misión que se rinde por escrito y aparece como éxito era el caso NEW-4."""
    m = _mision("haz lo imposible",
                outcome="No he podido completar el objetivo del paso.",
                node_output="No puedo completar este objetivo: me faltan tools.")
    p = signals.collect(m.id)
    assert p["honesty"]["final_is_surrender"] is True
    assert "n1" in p["honesty"]["surrendered_nodes"]
    assert "surrender" in signals.citable_ids(p)


async def test_un_entregable_afirmado_y_no_escrito_se_ve(tmp_path):
    """La mitad de la Sesión B que el juez reutiliza: qué se AFIRMÓ frente a qué
    se escribió de verdad."""
    m = _mision("escribe el plan",
                outcome="He escrito CORDYCEPS_PLAN_2026.md con el plan completo.")
    p = signals.collect(m.id)
    assert p["deliverables"]["claimed"], "no se detectó el archivo afirmado"
    assert p["deliverables"]["written"] == []
    assert "claimed_without_write" in signals.citable_ids(p)


async def test_sin_sesion_no_hay_despues_y_no_se_inventa():
    """Una misión que no nace del chat (automatización, WPMS) no tiene después
    que leer. La respuesta correcta es decirlo, no rellenarlo con lo que haya."""
    m = _mision("job nocturno", session_id=None)
    p = signals.collect(m.id)
    assert p["aftermath"]["available"] is False
    assert p["aftermath"]["next_messages"] == []
    assert "user_followup" not in signals.citable_ids(p)


async def test_el_despues_no_se_mezcla_entre_conversaciones():
    """`chat_messages` es plano entre pestañas: sin el `session_id` de la traza
    habría que adivinar por tiempo, y el juez leería la conversación de otra
    pestaña como si fuera la respuesta a esta misión."""
    m = _mision("busca vuelos", session_id="pestana-A")
    ahora = datetime.utcnow()
    _turno("pestana-A", "gracias, justo eso", ahora + timedelta(minutes=2))
    _turno("pestana-B", "esto está mal, hazlo otra vez", ahora + timedelta(minutes=2))

    p = signals.collect(m.id)
    textos = " ".join(x["text"] for x in p["aftermath"]["next_messages"])
    assert "justo eso" in textos
    assert "otra vez" not in textos, "se coló la conversación de otra pestaña"


# ===========================================================================
# 7 · LA CAPACIDAD `LEARN` EN EL MEL
# ===========================================================================
def test_un_razonador_local_sirve_para_aprender_y_un_modelo_pequeno_no():
    """La capacidad existe para que el usuario pueda elegir el modelo que
    aprende — y le conviene un razonador LOCAL: trabaja de madrugada, sin prisa
    y sin coste. Pero no vale cualquiera."""
    from app.mel.catalog import supports_learn

    assert supports_learn("ollama", "deepseek-r1:14b") is True
    assert supports_learn("ollama", "qwq:32b") is True
    assert supports_learn("anthropic", "claude-opus-5") is True
    assert supports_learn("ollama", "llama3") is False
    # Los agentes CLI arrancan un proceso por llamada: no son jueces de fondo.
    assert supports_learn("claude_code", "opus") is False


def test_lo_que_la_ui_filtra_y_lo_que_la_ejecucion_permite_coinciden(monkeypatch):
    """EL INVARIANTE, calcado del de visión (B·WEB-2) y por el mismo fallo: si
    la lista de Inteligencia ofrece un modelo que `set_primary` rechaza por
    dentro, el usuario ve que su elección "no se guarda" y nadie le explica por
    qué. La UI y la ejecución tienen que compartir el MISMO criterio."""
    import app.mel as mel
    from app.mel import registry

    disponibles = [
        ModelRef(provider="ollama", model="llama3", is_local=True),
        ModelRef(provider="ollama", model="deepseek-r1:14b", is_local=True),
        ModelRef(provider="anthropic", model="claude-opus-5"),
        ModelRef(provider="claude_code", model="opus"),
    ]
    monkeypatch.setattr(registry, "list_available", lambda: disponibles)

    por_key = {m["key"]: m for m in mel.list_models()}
    for ref in disponibles:
        no_aptas = set(por_key[ref.key]["unfit"])
        for cap in Capability:
            assert is_capable(ref, cap) == (cap.value not in no_aptas), (
                f"{ref.key} / {cap.value}: la UI y la ejecución no coinciden")


def test_learn_esta_en_el_enum_y_no_desplaza_a_nadie():
    """`Capability` es append-only: añadir LEARN no puede cambiar el valor de
    ninguna capacidad ya existente (hay políticas persistidas con esos
    strings)."""
    assert Capability.LEARN.value == "learn"
    for nombre, valor in (("CHAT", "chat"), ("REASON", "reason"),
                          ("ANALYZE", "analyze"), ("VISION", "vision")):
        assert getattr(Capability, nombre).value == valor


# ===========================================================================
# 8 · EL LOTE DE CHARLA (§3.4) — todo recibe veredicto
# ===========================================================================
async def test_la_charla_se_juzga_agrupada_en_una_sola_llamada(monkeypatch):
    """La charla trivial no crea misión desde A·VOZ-3, así que se juzga por
    turnos y en LOTE: todo recibe veredicto y el coste se controla agrupando,
    no omitiendo."""
    sid = "sesion-charla"
    base = datetime.utcnow()
    with SessionLocal() as s:
        for i, (rol, txt) in enumerate([("user", "¿qué hora es?"),
                                        ("assistant", "Son las 10:15."),
                                        ("user", "prefiero que me hables de tú"),
                                        ("assistant", "Hecho, te hablo de tú.")]):
            s.add(ChatMessage(role=rol, content=txt, session_id=sid,
                              created_at=base + timedelta(seconds=i)))
        s.commit()

    llamadas: list = []
    with SessionLocal() as s:
        ids = [f"chat:{f.id}" for f in s.query(ChatMessage)
               .filter(ChatMessage.role == "user").order_by(ChatMessage.id).all()]
    _responde(monkeypatch, {"turns": [
        {"id": ids[0], "verdict": "served", "confidence": 0.9,
         "reasons": "Respondió la hora.", "lesson": {"type": "none", "content": ""}},
        {"id": ids[1], "verdict": "served", "confidence": 0.9,
         "reasons": "Aceptó el tuteo.",
         "lesson": {"type": "fact", "content": "Prefiere que se le hable de tú."}},
    ]}, registro=llamadas)

    assert await judge.judge_chat_batch() == 2
    assert len(llamadas) == 1, "se hizo una llamada por turno en vez de una agrupada"
    v = judge.verdict_of(ids[1])
    assert v["verdict"] == "served"
    assert v["lesson"]["type"] == "fact"


async def test_el_lote_de_charla_ignora_ids_que_el_modelo_se_invente(monkeypatch):
    """Mismo criterio que el grounding: lo que el modelo dice sobre algo que no
    le dimos, no cuenta."""
    sid = "sesion-charla-2"
    base = datetime.utcnow()
    with SessionLocal() as s:
        s.add(ChatMessage(role="user", content="hola", session_id=sid,
                          created_at=base))
        s.add(ChatMessage(role="assistant", content="Hola.", session_id=sid,
                          created_at=base + timedelta(seconds=1)))
        s.commit()

    _responde(monkeypatch, {"turns": [
        {"id": "chat:999999", "verdict": "served", "confidence": 1.0,
         "reasons": "inventado", "lesson": {"type": "none", "content": ""}},
    ]})
    assert await judge.judge_chat_batch() == 0
