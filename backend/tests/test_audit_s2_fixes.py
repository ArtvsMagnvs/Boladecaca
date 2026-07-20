# tests/test_audit_s2_fixes.py — Regresiones de la Sesión 2 del plan de
# corrección post-auditoría v0.9.5 (doc 24 hallazgos C-1 y B-1; doc 25 S2).
#
# Contratos que protege:
#   C-1: el texto ORIGINAL del usuario (raw_text) es lo que planifica el
#        planner — el goal reescrito por el clasificador jamás lo sustituye,
#        y el contexto de memoria va marcado como solo-referencia.
#   B-1: el planner ve el catálogo REAL de acciones, puede rechazar
#        honestamente un objetivo imposible (PlanRejection → respuesta clara
#        al usuario), y los nodos de escritura tienen presupuesto ampliado.
from __future__ import annotations

import json

import pytest

from app.tie import planner
from app.tie.contracts import Intent, IntentType
from app.db.database import Base, OrchestratorTrace, SessionLocal, engine as db_engine


@pytest.fixture(autouse=True)
def _tables():
    Base.metadata.create_all(bind=db_engine)
    yield
    s = SessionLocal()
    try:
        s.query(OrchestratorTrace).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


def _fake_router(monkeypatch, responses):
    """router.complete fake. Captura los prompts (user + system) que ve el
    modelo — la clave de los tests de fidelidad."""
    calls = {"i": 0, "prompts": [], "systems": []}

    async def _complete(prompt, *, system_prompt=None, capability="chat"):
        calls["prompts"].append(prompt)
        calls["systems"].append(system_prompt or "")
        i = calls["i"]
        calls["i"] += 1
        r = responses[min(i, len(responses) - 1)]
        return {"response": r, "model": "fake-smart", "tokens": 30}

    import app.tie.router as router
    monkeypatch.setattr(router, "complete", _complete)
    return calls


def _spy_decision(monkeypatch):
    class _Dec:
        id = "dec-test-s2"

    async def _store(**kw):
        return _Dec()

    import app.services.decision_service as ds
    monkeypatch.setattr(ds, "store_decision", _store)


_PLAN_OK = json.dumps({"nodes": [
    {"id": "n1", "goal": "paso uno", "depends_on": [], "tools": []},
    {"id": "n2", "goal": "paso dos", "depends_on": ["n1"], "tools": []},
]})


# ---------------------------------------------------------------------------
# C-1 — Fidelidad del objetivo
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_c1_classify_estampa_raw_text_con_el_texto_original(monkeypatch):
    """El clasificador puede reescribir `goal` como quiera: `raw_text` lleva el
    mensaje ORIGINAL, intacto, y ningún JSON del modelo puede pisarlo."""
    from app.tie import intents

    async def _complete(prompt, *, system_prompt=None, capability="chat"):
        return {"response": json.dumps({
            "type": "execute", "goal": "REESCRITURA TOTALMENTE DISTINTA",
            "confidence": 0.9, "requires_planning": True,
            "raw_text": "INTENTO DE PISAR EL CAMPO",   # el modelo no manda aquí
        }), "model": "fake"}

    import app.tie.router as router
    monkeypatch.setattr(router, "complete", _complete)

    original = "crea un videojuego tipo Rey León con Godot en mi escritorio"
    intent = await intents.classify(original)

    assert intent.raw_text == original
    assert intent.goal == "REESCRITURA TOTALMENTE DISTINTA"   # goal es solo UI


@pytest.mark.anyio
async def test_c1_el_planner_recibe_el_texto_original_no_el_goal_reescrito(monkeypatch):
    """EL fix del fallo C: el prompt del planner contiene el raw_text LITERAL.
    El goal reescrito por el clasificador no lo sustituye."""
    from app.tie import pipeline
    from app.tie.missions import new_mission

    calls = _fake_router(monkeypatch, [_PLAN_OK])
    _spy_decision(monkeypatch)

    # Executor y responder fuera: solo queremos ver QUÉ recibe el planner.
    async def _fake_exec(graph, mission, trace_id=None):
        mission.state = "done"
    monkeypatch.setattr(pipeline.executor, "run", _fake_exec)

    async def _fake_build(mission, graph):
        return "ok"
    monkeypatch.setattr(pipeline.responder, "build", _fake_build)

    original = "crea un videojuego tipo Rey León con Godot, sin arte, solo bloques"
    intent = Intent(type=IntentType.EXECUTE, goal="algo totalmente reescrito por el clasificador",
                    confidence=0.9, requires_planning=True, raw_text=original)
    mission = new_mission(goal=intent.goal, source="test", channel="test")

    from app.tie import tracer
    trace_id = tracer.record_start(mission, channel="test")

    await pipeline._complex_path("texto que no es el original", intent, mission, trace_id, context="")

    prompt_planner = calls["prompts"][0]
    assert original in prompt_planner, "el planner DEBE ver el texto original"
    assert "totalmente reescrito" not in prompt_planner, "el goal reescrito no planifica"


@pytest.mark.anyio
async def test_c1_contexto_marcado_como_referencia_y_objetivo_literal(monkeypatch):
    """Anti-contaminación: el contexto de memoria viaja bajo la etiqueta de
    SOLO REFERENCIA, y el objetivo bajo la de fuente única del plan."""
    calls = _fake_router(monkeypatch, [_PLAN_OK])
    _spy_decision(monkeypatch)

    intent = Intent(type=IntentType.EXECUTE, goal="g", confidence=0.9)
    contexto_contaminante = "El usuario escribe novelas de fantasía y le gustan los MMORPG."

    g = await planner.plan("haz un videojuego del Rey León en Godot", intent,
                           context=contexto_contaminante)

    assert g is not None and not isinstance(g, planner.PlanRejection)
    prompt = calls["prompts"][0]
    assert "SOLO REFERENCIA" in prompt
    assert "la ÚNICA fuente del plan" in prompt
    assert prompt.index("Rey León") < prompt.index("novelas"), \
        "el objetivo va ANTES que el contexto"
    system = calls["systems"][0]
    assert "FIDELIDAD AL OBJETIVO" in system


@pytest.mark.anyio
async def test_c1_submit_mission_con_intent_no_reclasifica(monkeypatch):
    """`submit_mission(intent=...)` no paga (ni arriesga) una segunda
    clasificación: el mecanismo que ya usaba handle_stream, ahora también aquí."""
    from app.tie import intents, pipeline

    async def _no_llamar(*a, **k):
        raise AssertionError("classify NO debe llamarse si el intent ya viene dado")
    monkeypatch.setattr(intents, "classify", _no_llamar)

    _fake_router(monkeypatch, [_PLAN_OK])
    _spy_decision(monkeypatch)

    async def _fake_exec(graph, mission, trace_id=None):
        mission.state = "done"
    monkeypatch.setattr(pipeline.executor, "run", _fake_exec)

    async def _fake_build(mission, graph):
        return "hecho"
    monkeypatch.setattr(pipeline.responder, "build", _fake_build)

    intent = Intent(type=IntentType.EXECUTE, goal="resumen", confidence=0.9,
                    requires_planning=True, raw_text="el encargo literal")
    mission = await pipeline.submit_mission("el encargo literal", source="test", intent=intent)
    assert mission.state == "done"


# ---------------------------------------------------------------------------
# B-1 — Catálogo real + rechazo honesto + presupuesto
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_b1_el_planner_ve_el_catalogo_real_de_acciones(monkeypatch):
    """El system prompt lleva el catálogo con ACCIONES (no solo nombres):
    filesystem con create_dir, shell con run_command, etc."""
    calls = _fake_router(monkeypatch, [_PLAN_OK])
    _spy_decision(monkeypatch)

    intent = Intent(type=IntentType.EXECUTE, goal="g", confidence=0.9)
    await planner.plan("crea una carpeta en mi escritorio", intent)

    system = calls["systems"][0]
    assert "CATÁLOGO REAL" in system
    assert "create_dir" in system            # acción real de filesystem
    assert "filesystem" in system


@pytest.mark.anyio
async def test_b1_cannot_devuelve_rechazo_honesto(monkeypatch):
    """{"cannot": ...} del modelo → PlanRejection con el motivo, no None ni grafo."""
    _fake_router(monkeypatch, [json.dumps({
        "cannot": "necesitaría ejecutar Godot, que no está entre mis herramientas"
    })])
    _spy_decision(monkeypatch)

    intent = Intent(type=IntentType.EXECUTE, goal="g", confidence=0.9)
    res = await planner.plan("compila un juego con Godot", intent)

    assert isinstance(res, planner.PlanRejection)
    assert "Godot" in res.reason


@pytest.mark.anyio
async def test_b1_rechazo_honesto_llega_al_usuario_como_respuesta(monkeypatch):
    """El PlanRejection atraviesa el pipeline y se convierte en una respuesta
    clara — nunca en misión fantasma ni en degradación a charla."""
    from app.tie import pipeline
    from app.tie.missions import new_mission
    from app.tie import tracer

    _fake_router(monkeypatch, [json.dumps({"cannot": "no tengo esa capacidad"})])
    _spy_decision(monkeypatch)

    ejecutado = {"run": False}

    async def _fake_exec(graph, mission, trace_id=None):
        ejecutado["run"] = True
    monkeypatch.setattr(pipeline.executor, "run", _fake_exec)

    intent = Intent(type=IntentType.EXECUTE, goal="g", confidence=0.9,
                    requires_planning=True, raw_text="objetivo imposible")
    mission = new_mission(goal="g", source="test", channel="test")
    trace_id = tracer.record_start(mission, channel="test")

    await pipeline._complex_path("objetivo imposible", intent, mission, trace_id, context="")

    assert not ejecutado["run"], "nada se ejecuta tras un rechazo honesto"
    assert "no tengo esa capacidad" in (mission.outcome or "")
    assert mission.state == "done"            # es una respuesta, no un fallo del sistema


def test_b1_techo_de_nodos_flexible():
    """El techo pasó de 4-6 a 8 (decisión doc 25 §S2): un plan de 7 nodos con
    dependencias válidas ya no se rechaza."""
    assert planner._MAX_REASONABLE_NODES == 8


def test_b1_nodos_de_escritura_reciben_presupuesto_ampliado():
    """Un nodo con filesystem/shell/git recibe TIE_TOOL_MAX_ITERS_WRITE; uno de
    consulta (email) se queda con el base."""
    from app.core.config import settings
    from app.tie.runtime import _iters_for

    assert _iters_for(["filesystem"]) == settings.TIE_TOOL_MAX_ITERS_WRITE
    assert _iters_for(["shell", "search"]) == settings.TIE_TOOL_MAX_ITERS_WRITE
    assert _iters_for(["email"]) == settings.TIE_TOOL_MAX_ITERS
    assert _iters_for([]) == settings.TIE_TOOL_MAX_ITERS
    assert settings.TIE_TOOL_MAX_ITERS_WRITE > settings.TIE_TOOL_MAX_ITERS


# ---------------------------------------------------------------------------
# C-1b — Aislamiento de memoria por proyecto (petición directa del usuario:
# trabaja en VARIOS videojuegos a la vez; la memoria de uno JAMÁS puede
# colarse en las misiones de otro)
# ---------------------------------------------------------------------------
def _mem_item(item_id, content, project_id=None):
    from datetime import datetime
    from app.memory import MemoryItem, MemoryType

    meta = {"project_id": project_id} if project_id is not None else {}
    return MemoryItem(id=item_id, content=content, memory_type=MemoryType.PROJECT,
                      source="workspace", created_at=datetime(2026, 7, 1), metadata=meta)


@pytest.mark.anyio
async def test_c1b_contexto_excluye_memoria_de_otros_proyectos(monkeypatch):
    """El filtro determinista del store: pidiendo contexto PARA el proyecto 1,
    los items del proyecto 2 NO entran, por relevante que los considere la
    búsqueda semántica. Los items sin etiqueta (conocimiento general) sí."""
    from app.memory.stores.local_store import LocalMemoryStore

    store = LocalMemoryStore()

    async def _fake_search(query, memory_types=None, top_k=8, filters=None):
        return [
            _mem_item("a", "Juego A: el boss del nivel 3 usa ataques de fuego", project_id=1),
            _mem_item("b", "Juego B: protagonista felino con doble salto", project_id=2),
            _mem_item("c", "Preferencia general: el usuario documenta en español"),
        ]
    monkeypatch.setattr(store, "search", _fake_search)

    ctx = await store.context("mecánicas del juego", project_id=1)

    assert "boss del nivel 3" in ctx          # su propio proyecto: entra
    assert "doble salto" not in ctx           # OTRO proyecto: excluido SIEMPRE
    assert "documenta en español" in ctx      # sin etiqueta: conocimiento general


@pytest.mark.anyio
async def test_c1b_sin_project_id_no_se_filtra(monkeypatch):
    """Sin misión de proyecto no hay frontera que aplicar: el comportamiento
    anterior queda intacto (cero regresión)."""
    from app.memory.stores.local_store import LocalMemoryStore

    store = LocalMemoryStore()

    async def _fake_search(query, memory_types=None, top_k=8, filters=None):
        return [_mem_item("a", "del proyecto uno", project_id=1),
                _mem_item("b", "del proyecto dos", project_id=2)]
    monkeypatch.setattr(store, "search", _fake_search)

    ctx = await store.context("cualquier cosa")
    assert "proyecto uno" in ctx and "proyecto dos" in ctx


@pytest.mark.anyio
async def test_c1b_enricher_propaga_el_project_id(monkeypatch):
    """El enricher pasa project_id al MOS y lo incluye en su clave de caché
    (dos proyectos con la misma query NO comparten contexto cacheado)."""
    from app.tie import enricher

    enricher.clear_cache()
    visto = []

    async def _fake_context(query, max_tokens=1500, memory_types=None, project_id=None):
        visto.append(project_id)
        return f"ctx-del-proyecto-{project_id}"

    from app.memory import memory_router
    monkeypatch.setattr(memory_router, "context", _fake_context)

    c1 = await enricher.enrich("misma query", project_id=1)
    c2 = await enricher.enrich("misma query", project_id=2)

    assert visto == [1, 2], "cada proyecto hace SU consulta (la caché no los mezcla)"
    assert c1 == "ctx-del-proyecto-1" and c2 == "ctx-del-proyecto-2"
    enricher.clear_cache()


@pytest.mark.anyio
async def test_c1b_escritura_en_mision_de_proyecto_queda_etiquetada(monkeypatch):
    """La otra mitad: una memoria guardada DENTRO de una misión del proyecto 7
    sale etiquetada project_id=7 aunque el modelo no lo incluya — determinista,
    inyectado por el toolloop, no confiado al LLM."""
    from app.tie import toolloop
    from app.tie.authority import Authority
    from app.tools.tool_manager import tool_manager

    import app.mel as mel
    from app.mel import ExecutionResult, ServedBy, Usage

    respuestas = [
        json.dumps({"tool": {"tool_id": "memory", "action": "save_memory",
                             "params": {"content": "el boss usa fuego"}}}),
        '{"answer": "guardado"}',
    ]

    async def _complete(req):
        return ExecutionResult(text=respuestas.pop(0), ok=True,
                               served_by=ServedBy("fake", "m"), usage=Usage(tokens=1))
    monkeypatch.setattr(mel, "complete", _complete)

    capturado = {}

    async def _spy(**kwargs):
        capturado.update(kwargs)
        return {"success": True, "result": {"id": "m1"}, "error": None}
    monkeypatch.setattr(tool_manager, "execute", _spy)

    res = await toolloop.run(
        instruction="guarda esta nota del juego", context="",
        allowed_tools=["memory"], tool_manager=tool_manager, max_iters=3,
        authority=Authority(project_id=7, allowed_tools=["memory"]),
    )

    assert res.ok
    assert capturado["params"]["metadata"]["project_id"] == 7
