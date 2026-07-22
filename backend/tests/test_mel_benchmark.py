# tests/test_mel_benchmark.py — benchmark medido + políticas SPEED/BALANCED
# (2026-07-22, petición del usuario)
#
# Lo que protege:
#   1. Las sondas verificables son DETERMINISTAS (los checkers puros).
#   2. `_order_speed` pone el más rápido MEDIDO primero, manda los
#      rápidos-pero-torpes detrás, y EXCLUYE del pool principal un modelo
#      medido como muerto (el caso real MiniMax-M3-highspeed: id inválido,
#      400 de la API — jamás debe volver a ser primario de nada).
#   3. `_order_balanced` mezcla calidad conocida con velocidad medida.
#   4. `compile_all` produce también speed y balanced (5 automáticas).
#   5. `recompile_pristine` refresca SOLO las políticas no editadas.
#
# Sin red: el benchmark real (registry) no se toca — `benchmark.measured` se
# monkeypatchea con mediciones sintéticas.
from __future__ import annotations

import pytest

from app.db.database import Base, SessionLocal, engine as db_engine
from app.mel.contracts import Capability, ModelRef, PolicyName


@pytest.fixture(autouse=True)
def _tablas():
    Base.metadata.create_all(bind=db_engine)
    yield


# ---------------------------------------------------------------------------
# 1. Checkers de sondas (puros)
# ---------------------------------------------------------------------------
def test_checker_json_exige_el_objeto_exacto():
    from app.mel.benchmark import _check_json

    assert _check_json('{"tool": "browser", "action": "open_url"}')
    # tolera el vicio real de MiniMax (claves sin comillas + envoltorio)
    assert _check_json('[TOOL_CALL]\n{tool: "browser", action: "open_url"}\n[/TOOL_CALL]')
    assert not _check_json('{"tool": "browser"}')
    assert not _check_json("no es json")


def test_checker_instr_tres_lineas_exactas():
    from app.mel.benchmark import _check_instr

    assert _check_instr("Dato: uno\nDato: dos\nDato: tres")
    assert not _check_instr("Dato: uno\nDato: dos")
    assert not _check_instr("uno\ndos\ntres")


def test_checker_reason_respuesta_unica():
    from app.mel.benchmark import _check_reason

    assert _check_reason("36")
    assert _check_reason("La respuesta es 36 manzanas.")
    assert not _check_reason("24")


def test_speed_score_mapa_latencia():
    from app.mel.benchmark import _speed_score

    assert _speed_score(500) == 100      # fluido
    assert _speed_score(3000) == 100
    assert _speed_score(6000) == 50
    assert _speed_score(30000) == 10
    assert _speed_score(None) == 0       # nunca respondió


# ---------------------------------------------------------------------------
# 2-3. Órdenes medidas (con mediciones sintéticas)
# ---------------------------------------------------------------------------
_RAPIDO = ModelRef("prov_a", "rapido-bueno", False)
_LENTO_BUENO = ModelRef("prov_b", "lento-bueno", False)
_RAPIDO_TORPE = ModelRef("ollama", "rapido-torpe", True)
_MUERTO = ModelRef("prov_c", "modelo-muerto", False)
_SIN_MEDIR = ModelRef("prov_d", "sin-medir", False)

_MEDICIONES = {
    "prov_a:rapido-bueno": {"ok": True, "speed_score": 95, "quality_score": 100, "latency_ms_median": 2000},
    "prov_b:lento-bueno": {"ok": True, "speed_score": 15, "quality_score": 100, "latency_ms_median": 20000},
    "ollama:rapido-torpe": {"ok": True, "speed_score": 100, "quality_score": 0, "latency_ms_median": 400},
    "prov_c:modelo-muerto": {"ok": False, "speed_score": 0, "quality_score": 0, "latency_ms_median": None},
}


@pytest.fixture
def _mediciones_fake(monkeypatch):
    from app.mel import benchmark

    monkeypatch.setattr(benchmark, "measured", lambda ref: _MEDICIONES.get(ref.key))


def test_order_speed_el_mas_rapido_digno_primero(_mediciones_fake):
    from app.mel.policies import _order_speed

    pool = [_MUERTO, _LENTO_BUENO, _RAPIDO_TORPE, _RAPIDO, _SIN_MEDIR]
    ordered = [r.key for r in _order_speed(pool, Capability.AGENTIC)]

    # rápido Y digno primero; el torpe (quality<suelo) detrás de los dignos;
    # sin medir después; el muerto SIEMPRE el último.
    assert ordered[0] == "prov_a:rapido-bueno"
    assert ordered.index("ollama:rapido-torpe") > ordered.index("prov_b:lento-bueno")
    assert ordered[-1] == "prov_c:modelo-muerto", "un modelo medido como muerto jamás sube"


def test_order_balanced_mezcla_calidad_y_velocidad(_mediciones_fake, monkeypatch):
    # OJO: la función `policies()` del barrel SOMBREA el atributo del paquete
    # (incluso con `import app.mel.policies as pol`) — el módulo real se coge
    # de sys.modules.
    import importlib
    pol = importlib.import_module("app.mel.policies")

    # score de catálogo fijo: mismo conocimiento para todos → decide la velocidad
    monkeypatch.setattr(pol, "score_of", lambda r, cap: 80)
    ordered = [r.key for r in pol._order_balanced(
        [_LENTO_BUENO, _RAPIDO, _MUERTO], Capability.CHAT)]

    assert ordered[0] == "prov_a:rapido-bueno"      # a igual calidad, gana el rápido
    assert ordered[-1] == "prov_c:modelo-muerto"    # el muerto, al final


def test_order_speed_sin_mediciones_no_rompe(monkeypatch):
    """Primer arranque (nada medido aún): cae a la heurística de coste — nunca
    una cadena vacía ni una excepción."""
    from app.mel import benchmark
    from app.mel.policies import _order_speed

    monkeypatch.setattr(benchmark, "measured", lambda ref: None)
    ordered = _order_speed([_RAPIDO, _LENTO_BUENO], Capability.CHAT)
    assert len(ordered) == 2


# ---------------------------------------------------------------------------
# 4. compile_all — las 5 automáticas
# ---------------------------------------------------------------------------
def test_compile_all_incluye_speed_y_balanced(_mediciones_fake):
    from app.mel.policies import compile_all

    out = compile_all([_RAPIDO, _LENTO_BUENO])
    assert set(out) == {"economy", "quality", "offline", "speed", "balanced"}
    assert out["speed"]["chat"][0] == "prov_a:rapido-bueno"


def test_policyname_append_only():
    assert PolicyName.SPEED.value == "speed"
    assert PolicyName.BALANCED.value == "balanced"
    # los 4 originales intactos (contrato congelado, solo se añade)
    for v in ("economy", "quality", "offline", "custom"):
        assert PolicyName(v)


# ---------------------------------------------------------------------------
# 5. recompile_pristine — solo las no editadas
# ---------------------------------------------------------------------------
def test_recompile_pristine_respeta_las_editadas(_mediciones_fake):
    from app.db.database import SessionLocal
    from app.mel.models import MelPolicy
    from app.mel.policies import policy_store

    db = SessionLocal()
    try:
        db.query(MelPolicy).delete()
        db.add(MelPolicy(name="speed", version=1, compiled={"chat": ["viejo:modelo"]},
                         pristine=True, is_active=False))
        db.add(MelPolicy(name="custom", version=7, compiled={"chat": ["mi:eleccion"]},
                         pristine=False, is_active=True))
        db.commit()
    finally:
        db.close()

    try:
        updated = policy_store.recompile_pristine([_RAPIDO, _LENTO_BUENO])
        assert "speed" in updated
        db = SessionLocal()
        try:
            speed = db.query(MelPolicy).filter(MelPolicy.name == "speed").first()
            custom = db.query(MelPolicy).filter(MelPolicy.name == "custom").first()
            assert speed.compiled["chat"][0] == "prov_a:rapido-bueno"
            assert custom.compiled == {"chat": ["mi:eleccion"]}, \
                "una política EDITADA por el usuario jamás se recompila sola"
        finally:
            db.close()
    finally:
        db = SessionLocal()
        try:
            db.query(MelPolicy).delete()
            db.commit()
        finally:
            db.close()


# ---------------------------------------------------------------------------
# [2026-07-22, orden del usuario] EXCLUSIÓN TOTAL de modelos no capaces
#
# La regla: un fallo REAL medido en una tarea excluye al modelo de TODAS las
# posiciones de esa capacidad (ni primario ni respaldos), en TODAS las
# políticas — incluido Personalizado. Un respaldo que no puede cumplir la
# tarea no es red de seguridad, es un fallo aplazado.
# La contra-regla: cuota/conexión/timeout JAMÁS excluyen (no son capacidad),
# y sin datos v2 no se excluye.
# ---------------------------------------------------------------------------
def _persist_tasks(provider: str, model: str, tasks: dict, ok: bool = True):
    from datetime import datetime

    from app.db.database import SessionLocal
    from app.mel import benchmark
    from app.mel.models import MelBenchmark

    db = SessionLocal()
    try:
        db.query(MelBenchmark).filter(MelBenchmark.provider == provider,
                                      MelBenchmark.model == model).delete()
        db.add(MelBenchmark(provider=provider, model=model, ok=ok,
                            speed_score=50, quality_score=50, tasks=tasks,
                            updated_at=datetime.utcnow()))
        db.commit()
    finally:
        db.close()
    benchmark.invalidate_unfit_cache()


@pytest.fixture
def _limpia_benchmarks():
    from app.db.database import SessionLocal
    from app.mel import benchmark
    from app.mel.models import MelBenchmark

    yield
    db = SessionLocal()
    try:
        db.query(MelBenchmark).filter(MelBenchmark.provider.in_(
            ["provx", "provy"])).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()
    benchmark.invalidate_unfit_cache()


def test_fallo_real_medido_excluye_de_todas_las_posiciones(_limpia_benchmarks):
    """El caso que el usuario señaló: '¿solo no ponerlo de primario? ¿y si el
    primario falla, ponemos de respaldo uno que NO FUNCIONA?'. Un modelo con
    fallo real en tareas de tools no aparece en NINGUNA posición de agentic."""
    from app.mel.policies import _compile_policy, is_capable

    torpe = ModelRef("provx", "torpe", False)
    bueno = ModelRef("provy", "bueno", False)
    _persist_tasks("provx", "torpe", {
        "files_create": {"ok": False, "failure_kind": "wrong_result"},
        "files_edit": {"ok": True, "failure_kind": None},
    })

    assert not is_capable(torpe, Capability.AGENTIC)
    assert is_capable(bueno, Capability.AGENTIC)      # sin datos → no se excluye

    for pol in (PolicyName.QUALITY, PolicyName.ECONOMY, PolicyName.SPEED, PolicyName.BALANCED):
        chains = _compile_policy(pol, [torpe, bueno])
        assert "provx:torpe" not in chains["agentic"], (
            f"{pol.value}: el no-capaz apareció en la cadena de agentic")
        assert "provx:torpe" in chains["chat"], (
            f"{pol.value}: la exclusión es POR CAPACIDAD, no global")


def test_cuota_conexion_timeout_jamas_excluyen(_limpia_benchmarks):
    """fable/sonnet/haiku fallaron por cuota 429 — eso NO es incapacidad. Si
    esto excluyera, conectar Claude con la cuota agotada lo inutilizaría."""
    from app.mel.policies import is_capable

    ref = ModelRef("provx", "torpe", False)
    _persist_tasks("provx", "torpe", {
        "files_create": {"ok": False, "failure_kind": "quota"},
        "files_edit": {"ok": False, "failure_kind": "connection"},
        "web_read": {"ok": False, "failure_kind": "timeout"},
        "doc_csv": {"ok": False, "failure_kind": "bench_error"},
    })
    assert is_capable(ref, Capability.AGENTIC)


def test_datos_v1_sin_failure_kind_no_excluyen(_limpia_benchmarks):
    """La primera tanda (contaminada por cuota, sin clasificación) jamás puede
    usarse para excluir: solo los datos v2 con failure_kind cuentan."""
    from app.mel.policies import is_capable

    ref = ModelRef("provx", "torpe", False)
    _persist_tasks("provx", "torpe", {
        "files_create": {"ok": False, "error": "429 ..."},   # formato v1
    })
    assert is_capable(ref, Capability.AGENTIC)


def test_memory_save_no_computa_para_agentic(_limpia_benchmarks):
    """La fiabilidad guardar→recuperable es deuda de PLATAFORMA (roadmap
    pre-1.0): un fallo ahí no descalifica al modelo en agentic."""
    from app.mel.policies import is_capable

    ref = ModelRef("provx", "torpe", False)
    _persist_tasks("provx", "torpe", {
        "memory_save": {"ok": False, "failure_kind": "wrong_result"},
        "files_create": {"ok": True, "failure_kind": None},
    })
    assert is_capable(ref, Capability.AGENTIC)


def test_code_write_real_excluye_solo_de_code(_limpia_benchmarks):
    from app.mel.policies import is_capable

    ref = ModelRef("provx", "torpe", False)
    _persist_tasks("provx", "torpe", {
        "code_write": {"ok": False, "failure_kind": "no_tools"},
        "files_create": {"ok": True, "failure_kind": None},
    })
    assert not is_capable(ref, Capability.CODE)
    assert is_capable(ref, Capability.AGENTIC)


def test_modelo_muerto_medido_no_es_capaz_de_nada(_limpia_benchmarks):
    from app.mel.policies import is_capable

    ref = ModelRef("provx", "torpe", False)
    _persist_tasks("provx", "torpe", {}, ok=False)   # ni una sonda respondió
    for cap in (Capability.CHAT, Capability.AGENTIC, Capability.REASON):
        assert not is_capable(ref, cap)


def test_set_primary_y_set_slot_rechazan_no_capaz_medido(_limpia_benchmarks):
    """Ni siquiera en Personalizado: NUNCA es posible asignar un modelo a una
    tarea que no puede realizar (orden del usuario, 2026-07-22)."""
    from app.mel.policies import policy_store

    torpe = ModelRef("provx", "torpe", False)
    bueno = ModelRef("provy", "bueno", True)
    _persist_tasks("provx", "torpe", {
        "files_create": {"ok": False, "failure_kind": "wrong_result"},
    })
    policy_store.ensure_compiled([torpe, bueno])

    assert policy_store.set_primary("custom", "agentic", "provx:torpe",
                                    [torpe, bueno]) is False
    assert policy_store.set_slot("custom", "agentic", 1, "provx:torpe",
                                 [torpe, bueno]) is False
    # En una capacidad donde SÍ es capaz, se acepta con normalidad.
    assert policy_store.set_primary("custom", "chat", "provx:torpe",
                                    [torpe, bueno]) is True


def test_cadena_persistida_con_no_capaz_se_filtra_en_ejecucion(_limpia_benchmarks):
    """Retroactivo: una política guardada ANTES de conocerse la medición no
    puede seguir ejecutando el modelo no capaz — el filtro corre en
    active_chain/chain_for_named, sin tocar lo persistido."""
    from app.db.database import SessionLocal
    from app.mel.models import MelPolicy
    from app.mel.policies import policy_store

    torpe = ModelRef("provx", "torpe", False)
    bueno = ModelRef("provy", "bueno", True)
    _persist_tasks("provx", "torpe", {
        "files_create": {"ok": False, "failure_kind": "wrong_result"},
    })
    db = SessionLocal()
    try:
        db.query(MelPolicy).delete()
        db.add(MelPolicy(name="custom", version=1, pristine=False, is_active=True,
                         compiled={"agentic": ["provx:torpe", "provy:bueno"]}))
        db.commit()
    finally:
        db.close()
    try:
        chain = policy_store.active_chain(Capability.AGENTIC, [torpe, bueno])
        assert [r.key for r in chain] == ["provy:bueno"], (
            "el no-capaz persistido debe filtrarse en ejecución")
    finally:
        db = SessionLocal()
        try:
            db.query(MelPolicy).delete()
            db.commit()
        finally:
            db.close()
