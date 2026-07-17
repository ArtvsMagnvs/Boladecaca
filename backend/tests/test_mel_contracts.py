# tests/test_mel_contracts.py — contratos + catálogo + compilador + registry (MEL E1)
#
# Blinda lo que NO debe cambiar de firma (contratos congelados), que el compilador
# de políticas produce cadenas sensatas y nunca vacías con modelos disponibles, y
# que la resolución de nombre coloquial de modelo funciona (la usará E2b).
import dataclasses

import pytest

from app.mel import (
    Capability,
    Constraints,
    ExecutionRequest,
    ExecutionResult,
    ModelRef,
    PolicyName,
)
from app.mel.contracts import DecisionTrace
from app.mel.policies import compile_all, default_active, _order_economy, _order_quality
from app.mel import registry


# ---------------------------------------------------------------------------
# Contratos congelados
# ---------------------------------------------------------------------------
def test_capability_enum_completo_y_append_only():
    # Las 8 activas + 3 reservadas (doc 19 §3). Si cambia el ORDEN o desaparece
    # una, es una rotura de contrato.
    activos = ["chat", "classify", "extract", "summarize", "draft", "reason", "code", "analyze"]
    reservados = ["research", "vision", "agentic"]
    valores = [c.value for c in Capability]
    for v in activos + reservados:
        assert v in valores


def test_execution_request_congelado_con_model_override():
    req = ExecutionRequest(capability=Capability.CHAT, prompt="hola")
    # defaults seguros
    assert req.system_prompt is None
    assert req.policy_override is None
    assert req.model_override is None            # [E2b] el campo existe desde E1
    assert isinstance(req.constraints, Constraints)
    assert req.context_tags == {}
    # frozen: no se puede mutar
    with pytest.raises(dataclasses.FrozenInstanceError):
        req.prompt = "otro"


def test_modelref_key():
    r = ModelRef(provider="anthropic", model="claude-opus-4-8", is_local=False)
    assert r.key == "anthropic:claude-opus-4-8"


def test_decision_trace_round_trip():
    t = DecisionTrace(capability="chat", policy="economy", chain=["a:1", "b:2"],
                      skipped=[("a:1", "breaker")], chosen="b:2")
    d = t.to_dict()
    assert d["capability"] == "chat"
    assert d["chain"] == ["a:1", "b:2"]
    assert d["skipped"] == [["a:1", "breaker"]]
    assert d["chosen"] == "b:2"
    assert d["id"] == t.id


def test_execution_result_defaults():
    r = ExecutionResult(text="hola", ok=True)
    assert r.error is None and r.served_by is None and r.decision_id is None


# ---------------------------------------------------------------------------
# Compilador de políticas
# ---------------------------------------------------------------------------
def _avail():
    return [
        ModelRef("anthropic", "claude-opus-4-8", False),
        ModelRef("deepseek", "deepseek-v4-flash", False),
        ModelRef("ollama", "llama3", True),
    ]


def test_compilador_nunca_cadena_vacia_con_modelos():
    comp = compile_all(_avail())
    for policy in ("economy", "quality"):
        for cap in Capability:
            assert comp[policy][cap.value], f"{policy}/{cap.value} quedó sin cadena"


def test_offline_solo_locales():
    comp = compile_all(_avail())
    for cap in Capability:
        for key in comp["offline"][cap.value]:
            assert key.startswith("ollama:"), f"offline coló un no-local: {key}"


def test_offline_degradada_sin_local():
    # Sin ningún modelo local, Offline queda vacía por capacidad (degradada).
    solo_cloud = [ModelRef("anthropic", "claude-opus-4-8", False)]
    comp = compile_all(solo_cloud)
    assert comp["offline"]["chat"] == []
    # pero Quality sí tiene cadena
    assert comp["quality"]["chat"] == ["anthropic:claude-opus-4-8"]


def test_quality_ordena_por_score_y_economy_por_coste():
    avail = _avail()
    # En CODE, deepseek es barato y bueno → Economy lo pone primero.
    eco = [r.key for r in _order_economy(avail, Capability.CODE)]
    assert eco[0] == "deepseek:deepseek-v4-flash"
    # En REASON, opus tiene el mejor score → Quality lo pone primero.
    qual = [r.key for r in _order_quality(avail, Capability.REASON)]
    assert qual[0] == "anthropic:claude-opus-4-8"


def test_default_active_economy_si_hay_local():
    assert default_active(_avail()) == "economy"
    assert default_active([ModelRef("anthropic", "claude-opus-4-8", False)]) == "quality"


def test_una_sola_config_degenera_a_cadena_de_1():
    solo = [ModelRef("minimax", "MiniMax-M2.7-highspeed", False)]
    comp = compile_all(solo)
    assert comp["economy"]["chat"] == ["minimax:MiniMax-M2.7-highspeed"]
    assert comp["quality"]["reason"] == ["minimax:MiniMax-M2.7-highspeed"]


# ---------------------------------------------------------------------------
# Resolución de nombre de modelo (doc 19 §7b.2 — la usa E2b)
# ---------------------------------------------------------------------------
def test_resolve_model_name(monkeypatch):
    fake = [
        ModelRef("anthropic", "claude-opus-4-8", False),
        ModelRef("openai", "gpt-5.1", False),
        ModelRef("ollama", "llama3", True),
    ]
    monkeypatch.setattr(registry, "list_available", lambda: fake)

    # alias coloquial de proveedor
    assert registry.resolve_model_name("usa Claude para esto").provider == "anthropic"
    assert registry.resolve_model_name("el modelo de OpenAI").provider == "openai"
    # subcadena del model id
    assert registry.resolve_model_name("gpt-5").model == "gpt-5.1"
    # id exacto
    assert registry.resolve_model_name("llama3").provider == "ollama"
    # inexistente → None (nunca inventa)
    assert registry.resolve_model_name("gemini ultra") is None
    assert registry.resolve_model_name("") is None
