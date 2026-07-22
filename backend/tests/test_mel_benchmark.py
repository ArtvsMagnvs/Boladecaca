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
