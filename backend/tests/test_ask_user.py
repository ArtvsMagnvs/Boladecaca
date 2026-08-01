# tests/test_ask_user.py — [2026-08-02] PREGUNTAR AL USUARIO y esperar.
#
# EL FALLO QUE CIERRA (reportado por el usuario con un caso real): el
# orquestador de Cordyceps necesitaba preguntar "¿confirmo que el stack es
# Unity?" y "¿A, B o C?" — y no tenía NINGUNA forma de hacerlo. Como no podía
# preguntar, hizo lo único que le quedaba: terminar la misión como "Completada"
# escribiendo la pregunta en el resumen final, donde ya no sirve de nada. La
# tarea no se completó porque no había canal de pregunta.
#
# Lo que se blinda aquí:
#   1. La espera es INDEFINIDA (exigencia explícita del usuario: "da igual si
#      son 4 horas o dos días"). No hay timeout que la mate.
#   2. La respuesta del usuario llega ENTERA al modelo, no un "aprobado".
#   3. El modo AUTÓNOMO no se auto-responde una pregunta (autonomía es "no me
#      pidas permiso", nunca "invéntate mi criterio").
#   4. Una pregunta abierta se persiste, así que sobrevive a un reinicio y se
#      puede resolver desde cualquier pantalla.
from __future__ import annotations

import asyncio

import pytest

from app.automation import approval_gate, permission_service
from app.automation.models import Approval
from app.db.database import Base, SessionLocal, engine as db_engine
from app.tie import toolloop


@pytest.fixture(autouse=True)
def _clean():
    Base.metadata.create_all(bind=db_engine)
    permission_service.apply_profile("manual")
    yield
    s = SessionLocal()
    try:
        s.query(Approval).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()
    permission_service.apply_profile("manual")


async def _pending_question_id() -> str:
    """El gate de pregunta abierto (sondeando: lo abre otra corrutina)."""
    for _ in range(80):
        for a in approval_gate.list_pending():
            if a.kind == permission_service.USER_QUESTION_KIND:
                return a.id
        await asyncio.sleep(0.05)
    raise AssertionError("no se abrió ninguna pregunta")


# ---------------------------------------------------------------------------
# 1) El ciclo completo: preguntar → esperar → responder → seguir
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_ask_user_devuelve_la_respuesta_del_usuario():
    tarea = asyncio.create_task(toolloop.ask_user(
        "¿El stack es Unity o un motor genérico?",
        ["Unity (recomendado)", "Motor genérico"],
        "Stack",
        approval_gate,
        mission_id="m-1",
    ))
    gate_id = await _pending_question_id()

    # Mientras nadie responde, la tarea NO termina.
    await asyncio.sleep(0.3)
    assert not tarea.done(), "no puede continuar sin respuesta"

    await approval_gate.resolve(gate_id, approved=True, note="Unity, versión 2022 LTS")
    respondida, respuesta = await asyncio.wait_for(tarea, timeout=5)

    assert respondida is True
    assert respuesta == "Unity, versión 2022 LTS", "el modelo recibe el TEXTO, no un 'aprobado'"


@pytest.mark.anyio
async def test_la_pregunta_guarda_enunciado_y_opciones():
    tarea = asyncio.create_task(toolloop.ask_user(
        "¿Qué hago con el agente huérfano?",
        ["Vincularlo al proyecto", "Borrarlo y crear otro"],
        "Agente",
        approval_gate,
        mission_id="m-2",
    ))
    gate_id = await _pending_question_id()

    appr = approval_gate.get(gate_id)
    payload = appr.action_payload or {}
    assert payload["question"] == "¿Qué hago con el agente huérfano?"
    assert payload["options"] == ["Vincularlo al proyecto", "Borrarlo y crear otro"]
    assert payload["header"] == "Agente"
    assert payload["mission_id"] == "m-2", "sin esto la UI no puede ligarla a su misión"
    assert appr.action_type == "user_question"

    await approval_gate.resolve(gate_id, approved=True, note="Vincularlo")
    await asyncio.wait_for(tarea, timeout=5)


@pytest.mark.anyio
async def test_pregunta_descartada_se_reporta_como_tal():
    tarea = asyncio.create_task(toolloop.ask_user(
        "¿Sigo?", ["Sí", "No"], "", approval_gate, mission_id="m-3",
    ))
    gate_id = await _pending_question_id()
    await approval_gate.resolve(gate_id, approved=False, note="ahora no")
    respondida, _ = await asyncio.wait_for(tarea, timeout=5)
    assert respondida is False


# ---------------------------------------------------------------------------
# 2) LA EXIGENCIA EXPLÍCITA DEL USUARIO: espera indefinida
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_la_espera_no_caduca():
    """"La respuesta por mi parte tiene espera indefinida, no va con timeout.
    Hasta que yo no responda, no se continúa, da igual si son 4 horas o dos
    días" (el usuario, 2026-08-02).

    No se pueden esperar 4 horas en un test, pero SÍ se puede demostrar lo que
    importa: que nada dentro del código pone un plazo — el gate sigue
    `pending` y la corrutina sigue viva mucho después de que cualquier timeout
    razonable (los 120s de A-2, los 300s del ToolManager) habría disparado.
    Se comprueba adelantando el reloj que usa la espera."""
    dormidas: list[float] = []
    real_sleep = asyncio.sleep

    async def _sleep_instantaneo(segundos):
        dormidas.append(segundos)
        await real_sleep(0)

    original = toolloop.asyncio.sleep
    toolloop.asyncio.sleep = _sleep_instantaneo
    try:
        tarea = asyncio.create_task(toolloop.ask_user(
            "¿Espero?", [], "", approval_gate, mission_id="m-4",
        ))
        gate_id = await _pending_question_id()
        while sum(dormidas) < 6 * 60 * 60:      # 6 HORAS de espera simulada
            await real_sleep(0)
            if tarea.done():
                break
        assert not tarea.done(), "la espera caducó sola: eso es exactamente lo que no debe pasar"
        assert approval_gate.get(gate_id).status == "pending"

        await approval_gate.resolve(gate_id, approved=True, note="por fin")
        respondida, respuesta = await asyncio.wait_for(tarea, timeout=5)
        assert (respondida, respuesta) == (True, "por fin")
    finally:
        toolloop.asyncio.sleep = original


# ---------------------------------------------------------------------------
# 3) El modo Autónomo NO responde por el usuario
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_autonomo_total_no_auto_responde_una_pregunta():
    """El perfil `full` auto-aprueba CUALQUIER gate (fix 2026-07-20). Una
    pregunta es la única excepción: auto-aprobarla le devolvería al modelo la
    nota "auto (permiso pre-autorizado)" COMO SI fuera la respuesta del
    usuario — inventándole un criterio que nunca dio."""
    permission_service.apply_profile("full")
    assert permission_service.autonomy_is_full() is True
    # Un gate normal SÍ se auto-aprueba (no-regresión del modo autónomo).
    assert permission_service.is_kind_pre_authorized("tie.plan_approval") is True
    # Una pregunta, NO.
    assert permission_service.is_kind_pre_authorized(permission_service.USER_QUESTION_KIND) is False

    tarea = asyncio.create_task(toolloop.ask_user(
        "¿Unity o genérico?", ["Unity", "Genérico"], "", approval_gate, mission_id="m-5",
    ))
    gate_id = await _pending_question_id()
    await asyncio.sleep(0.3)
    assert not tarea.done(), "en autónomo total la pregunta SIGUE esperando al usuario"
    assert approval_gate.get(gate_id).status == "pending"

    await approval_gate.resolve(gate_id, approved=True, note="Unity")
    respondida, respuesta = await asyncio.wait_for(tarea, timeout=5)
    assert respuesta == "Unity"


# ---------------------------------------------------------------------------
# 4) Casos de forma
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_sin_canal_de_aprobacion_lo_dice_en_vez_de_colgarse():
    respondida, motivo = await toolloop.ask_user("¿Algo?", [], "", None)
    assert respondida is False and "no hay canal" in motivo


@pytest.mark.anyio
async def test_pregunta_vacia_se_rechaza():
    respondida, motivo = await toolloop.ask_user("   ", [], "", approval_gate)
    assert respondida is False and "no se formuló" in motivo


@pytest.mark.parametrize("entrada,esperado", [
    (["A", "B"], ["A", "B"]),
    ([{"label": "A"}, {"text": "B"}], ["A", "B"]),
    (["A", "A", "B"], ["A", "B"]),                       # sin duplicados
    (["a"] * 20, ["a"]),                                  # dedup + tope
    (None, []),
    ("no es lista", []),
])
def test_normalizacion_de_opciones(entrada, esperado):
    assert toolloop._as_options(entrada) == esperado


def test_tope_de_seis_opciones():
    assert len(toolloop._as_options([f"op{i}" for i in range(20)])) == 6


# ---------------------------------------------------------------------------
# 5) El catálogo la anuncia (si el modelo no la ve, no existe)
# ---------------------------------------------------------------------------
def test_ask_user_esta_en_el_catalogo_de_la_tool_interna():
    from app.tools.aithera_tool import AitheraTool

    acciones = {a["id"]: a for a in AitheraTool().list_actions()}
    assert "ask_user" in acciones, "si no está en el catálogo, el modelo nunca la usará"
    assert set(acciones["ask_user"]["params"]) >= {"question", "options"}
    assert acciones["ask_user"]["requires_confirmation"] is False, (
        "preguntar no puede requerir a su vez una aprobación: sería una pregunta para preguntar"
    )
