# tests/test_progress_rastro.py — el rastro de actividad en vivo (2026-08-02)
#
# LO QUE CIERRA (petición del usuario): una misión decía "me pongo con ello" y
# el chat se quedaba mudo hasta la respuesta final. Ahora va contando lo que
# hace, en frases cortas "acción + objeto", igual que se ve trabajar a Claude.
#
# Tres cosas que probar, y en este orden de importancia:
#   1. Narrar NO PUEDE romper nada (sin cola, cola llena, frase imposible).
#   2. El rastro llega DE VERDAD desde el toolloop real (no basta con que la
#      función pura funcione: ya pasó dos veces en este proyecto que la lógica
#      estuviera bien y desconectada — S9b, S9c).
#   3. Las líneas nunca se cuelan en el TEXTO de la respuesta.
from __future__ import annotations

import asyncio

import pytest

from app.tie import progress


@pytest.fixture(autouse=True)
def _sin_cola():
    """Cada test parte sin cola ligada y la suelta al salir: el contextvar es
    de módulo y un residuo se colaría en el siguiente test."""
    progress.unbind()
    yield
    progress.unbind()


# ===========================================================================
# 1 — Narrar es OBSERVACIÓN: jamás puede romper el trabajo real
# ===========================================================================
class TestNuncaRompe:
    def test_sin_cola_ligada_es_un_no_op(self):
        progress.emit("esto no va a ninguna parte")   # no debe lanzar

    def test_linea_vacia_no_encola(self):
        q = progress.bind()
        progress.emit("")
        progress.emit(None)  # type: ignore[arg-type]
        assert q.empty()

    def test_cola_llena_tira_lo_viejo_y_no_bloquea(self):
        q = progress.bind()
        for i in range(progress._MAX_PENDING + 25):
            progress.emit(f"linea {i}")
        assert q.qsize() == progress._MAX_PENDING
        # Se conservan las ÚLTIMAS: el rastro es "qué pasa ahora".
        assert q.get_nowait() == "linea 25"

    def test_linea_larguisima_se_recorta(self):
        q = progress.bind()
        progress.emit("x" * 900)
        assert len(q.get_nowait()) <= 180

    def test_describe_nunca_lanza(self):
        # Params basura, tool inexistente, acción None: siempre algo legible.
        assert progress.describe("no_existe", "raro", {"a": object()})
        assert progress.describe("filesystem", "read_file", None)
        assert progress.describe("", "", {})


# ===========================================================================
# 2 — Las frases: acción + objeto corto (la decisión del usuario)
# ===========================================================================
class TestFrases:
    @pytest.mark.parametrize("tool,action,params,esperado", [
        ("filesystem", "read_file", {"path": "C:\\proy\\GDD.docx"}, "Leyendo GDD.docx"),
        ("document", "read_docx", {"path": "/home/x/informe.docx"}, "Leyendo informe.docx"),
        ("search", "search_web", {"query": "Unity ECS"}, "Buscando en la web: Unity ECS"),
        ("browser", "open_url", {"url": "https://www.youtube.com/watch?v=a"}, "Abriendo www.youtube.com"),
        ("aithera", "list_projects", {}, "Consultando tus proyectos"),
        ("email", "list_inbox_preview", {"limit": 5}, "Revisando el correo"),
        ("memory", "save_memory", {"content": "x"}, "Guardando en la memoria"),
    ])
    def test_frase_exacta(self, tool, action, params, esperado):
        assert progress.describe(tool, action, params) == esperado

    def test_una_ruta_se_queda_en_el_nombre_del_archivo(self):
        larga = "C:/Users/Alejandro/Desktop/CLAUDE/Cordyceps/docs/DeadlyCypros_GDD_MVP.docx"
        assert progress.describe("document", "read_docx", {"path": larga}).endswith("GDD_MVP.docx")

    def test_un_comando_de_shell_NO_se_trocea_como_ruta(self):
        """Regresión: el acortado por 'tiene barras' dejaba
        `python -m pytest tests/ -q` en ' -q'."""
        frase = progress.describe("shell", "run", {"command": "python -m pytest tests/ -q"})
        assert "pytest" in frase and frase.endswith("-q")

    def test_tool_desconocida_sigue_siendo_legible(self):
        frase = progress.describe("tool_del_futuro", "hacer_algo", {"query": "cosa"})
        assert "tool_del_futuro" in frase and "cosa" in frase

    def test_sin_objeto_util_no_deja_la_frase_coja(self):
        # "Leyendo " a secas no dice nada: cae al genérico.
        assert progress.describe("filesystem", "read_file", {}) == "Usando filesystem"


# ===========================================================================
# 3 — El drenaje: lo emitido llega, en orden, y el latido sigue existiendo
# ===========================================================================
class TestDrenaje:
    @pytest.mark.anyio
    async def test_lo_emitido_llega_en_orden_y_se_vacia_al_final(self):
        q = progress.bind()

        async def trabajo():
            progress.emit("uno")
            await asyncio.sleep(0.01)
            progress.emit("dos")
            await asyncio.sleep(0.01)
            # RÁFAGA final sin ningún await por medio: el drenaje solo puede
            # recoger UNA por vuelta del `wait`, así que sin el vaciado de
            # cierre estas se perderían siempre. (La primera versión de este
            # test emitía una sola línea al final y la mutación NO la detectaba:
            # la carrera getter/task la salvaba por casualidad.)
            progress.emit("tres")
            progress.emit("cuatro")
            progress.emit("cinco")
            return "hecho"

        task = asyncio.ensure_future(trabajo())
        vistos = [p async for (k, p) in progress.drain_until(task, q, heartbeat_s=5) if k == "activity"]
        assert await task == "hecho"
        assert vistos == ["uno", "dos", "tres", "cuatro", "cinco"]

    @pytest.mark.anyio
    async def test_sin_actividad_sigue_habiendo_latido(self):
        """El latido de S4 (ningún turno mudo más de N s) no se pierde."""
        q = progress.bind()

        async def callado():
            await asyncio.sleep(0.25)

        task = asyncio.ensure_future(callado())
        kinds = [k async for (k, _p) in progress.drain_until(task, q, heartbeat_s=1)]
        # heartbeat_s se compara en segundos: con 0.25s de trabajo no hay latido,
        # pero tampoco puede colgarse ni inventar actividad.
        await task
        assert all(k in ("status", "activity") for k in kinds)

    @pytest.mark.anyio
    async def test_una_excepcion_del_trabajo_no_la_traga_el_drenaje(self):
        q = progress.bind()

        async def revienta():
            progress.emit("voy a fallar")
            raise RuntimeError("boom")

        task = asyncio.ensure_future(revienta())
        vistos = [p async for (k, p) in progress.drain_until(task, q, heartbeat_s=5) if k == "activity"]
        assert vistos == ["voy a fallar"]
        with pytest.raises(RuntimeError, match="boom"):
            await task

    @pytest.mark.anyio
    async def test_dos_misiones_concurrentes_no_mezclan_su_rastro(self):
        """Lo que hace correcto el enrutado por contexto: la cola se hereda al
        crear la tarea, así que cada misión escribe en la suya."""
        async def mision(nombre: str, q_out: list):
            q = progress.bind()

            async def trabajo():
                progress.emit(f"{nombre}-1")
                await asyncio.sleep(0.02)
                progress.emit(f"{nombre}-2")

            task = asyncio.ensure_future(trabajo())
            async for k, p in progress.drain_until(task, q, heartbeat_s=5):
                if k == "activity":
                    q_out.append(p)
            await task

        a, b = [], []
        await asyncio.gather(
            asyncio.create_task(mision("A", a)),
            asyncio.create_task(mision("B", b)),
        )
        assert a == ["A-1", "A-2"]
        assert b == ["B-1", "B-2"]


# ===========================================================================
# 4 — CABLEADO REAL: el toolloop de verdad alimenta el rastro
# ===========================================================================
@pytest.mark.anyio
async def test_el_toolloop_real_emite_el_rastro(monkeypatch, tmp_path):
    """No basta con que `describe`/`emit` funcionen por separado: ya ha pasado
    dos veces en este proyecto (S9b, S9c) que la lógica fuera correcta y
    estuviera DESCONECTADA. Aquí corre `toolloop.run` de verdad, con el
    ToolManager real escribiendo en disco real; lo único fake es el LLM."""
    from app.tie import toolloop
    from app.tools import tool_manager

    objetivo = tmp_path / "nota.txt"
    objetivo.write_text("hola", encoding="utf-8")

    guiones = [
        '{"tool": {"tool_id": "filesystem", "action": "read_file", "params": {"path": "%s"}}}'
        % str(objetivo).replace("\\", "\\\\"),
        '{"answer": "El archivo dice hola."}',
    ]
    estado = {"i": 0}

    async def fake_complete(req):
        from app.mel import ExecutionResult, ServedBy, Usage

        i = estado["i"]
        estado["i"] += 1
        return ExecutionResult(
            ok=True, text=guiones[min(i, len(guiones) - 1)],
            served_by=ServedBy(provider="fake", model="fake"), usage=Usage(),
        )

    import app.mel as mel

    monkeypatch.setattr(mel, "complete", fake_complete)

    q = progress.bind()
    res = await toolloop.run(
        instruction="lee la nota",
        context="",
        allowed_tools=["filesystem"],
        tool_manager=tool_manager,
        max_iters=4,
    )
    lineas = []
    while not q.empty():
        lineas.append(q.get_nowait())

    assert res.ok, res.error
    assert any("nota.txt" in l for l in lineas), f"el rastro no menciona el archivo leído: {lineas}"
    assert any(l.startswith("Leyendo") for l in lineas), lineas


# ===========================================================================
# 5 — El chat del ORQUESTADOR: sondea, no escucha un stream
# ===========================================================================
# El fallo real reportado por el usuario ("no ha mostrado mensajes de progreso,
# ha mostrado 'Trabajando…' hasta terminar"): probó en el chat de la tarjeta de
# proyecto, que lanza la misión con POST /api/agents/{id}/execute y SONDEA la
# fila de `agent_executions`. Ahí no hay SSE, así que el rastro tiene que
# quedar PERSISTIDO en la propia ejecución para poder leerse.
@pytest.mark.anyio
async def test_el_rastro_se_persiste_en_la_ejecucion_del_agente():
    import json

    from app.agents.agent_manager import agent_manager
    from app.db.database import (Agent, AgentExecution, Base, SessionLocal,
                                 engine as db_engine)

    Base.metadata.create_all(bind=db_engine)
    db = SessionLocal()
    try:
        agente = Agent(name="Rastro test", agent_type="generic", is_active=True,
                       allowed_tools="[]", project_id=None)
        db.add(agente)
        db.commit()
        db.refresh(agente)
        ex = AgentExecution(agent_id=agente.id, task_description="x", status="running")
        db.add(ex)
        db.commit()
        db.refresh(ex)
        ex_id, ag_id = ex.id, agente.id
    finally:
        db.close()

    try:
        cola = progress.bind()
        drenador = asyncio.ensure_future(agent_manager._drain_progress(ex_id, cola))
        progress.emit("Leyendo GDD.docx")
        progress.emit("Paso 2 de 3: redactar")
        for _ in range(50):                       # espera activa corta
            await asyncio.sleep(0.02)
            db = SessionLocal()
            try:
                fila = db.get(AgentExecution, ex_id)
                guardado = json.loads(fila.progress) if fila and fila.progress else []
            finally:
                db.close()
            if len(guardado) >= 2:
                break
        drenador.cancel()

        assert guardado == ["Leyendo GDD.docx", "Paso 2 de 3: redactar"], guardado
    finally:
        db = SessionLocal()
        try:
            db.query(AgentExecution).filter(AgentExecution.id == ex_id).delete()
            db.query(Agent).filter(Agent.id == ag_id).delete()
            db.commit()
        finally:
            db.close()
