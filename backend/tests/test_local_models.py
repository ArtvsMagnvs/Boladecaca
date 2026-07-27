# tests/test_local_models.py — modelos locales especializados + Claude Code (V1.0)
#
# La visión: varios locales conviven (Ornith programa, DeepSeek razona, Qwen
# conversa) y el MEL reparte. Aquí se prueba que eso es REAL: que el registry
# los ve como candidatos independientes, que el compilador de políticas elige
# al especialista por capacidad, y que Claude Code entra como un proveedor más.
#
# Sin red ni descargas: el catálogo y el compilador son puros, y el CLI de
# Claude Code se mockea (en CI no hay sesión iniciada).
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.local_catalog import LOCAL_CATALOG, all_models, find_model
from app.mel.contracts import Capability, ModelRef, PolicyName
from app.mel.policies import _compile_policy

ORNITH_9B = "hf.co/deepreinforce-ai/Ornith-1.0-9B-GGUF:Q4_K_M"


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------
def test_catalogo_cubre_las_familias():
    # [2026-07-21] +Llama al catálogo (llama3.2:3b/llama3/llama3.3:70b).
    assert set(LOCAL_CATALOG) == {"ollama", "qwen", "ornith", "deepseek", "qwen_vision", "llama"}
    assert LOCAL_CATALOG["ollama"]["is_runtime"] is True


def test_cada_familia_instalable_tiene_modelos_y_una_sugerencia():
    for family, fam in LOCAL_CATALOG.items():
        if fam.get("is_runtime"):
            continue
        models = fam["models"]
        assert len(models) >= 2, f"{family} debería ofrecer varias potencias"
        assert sum(1 for m in models if m["recommended"]) == 1, \
            f"{family} debe tener exactamente una variante sugerida"
        for m in models:
            assert m["size_gb"] > 0        # el dato con el que el usuario decide hoy
            assert m["tag"] and m["label"]


def test_find_model_y_familias():
    m = find_model(ORNITH_9B)
    assert m and m["family"] == "ornith" and m["category"] == "coding"
    assert find_model("modelo-que-no-existe") is None
    assert len(all_models()) == sum(
        len(f["models"]) for f in LOCAL_CATALOG.values() if not f.get("is_runtime"))


# ---------------------------------------------------------------------------
# El reparto por especialista (el corazón de la petición del usuario)
# ---------------------------------------------------------------------------
def _fleet() -> list[ModelRef]:
    return [
        ModelRef("ollama", "qwen3:14b", True),
        ModelRef("ollama", ORNITH_9B, True),
        ModelRef("ollama", "deepseek-r1:14b", True),
        ModelRef("ollama", "qwen2.5vl:7b", True),
    ]


def test_code_va_a_ornith_y_reason_a_deepseek():
    """Con los 4 especialistas instalados, cada capacidad debe ir al suyo —
    sin que el usuario configure nada."""
    chains = _compile_policy(PolicyName.QUALITY, _fleet())
    assert chains["code"][0] == f"ollama:{ORNITH_9B}"
    assert chains["reason"][0] == "ollama:deepseek-r1:14b"
    assert chains["vision"][0] == "ollama:qwen2.5vl:7b"


def test_ornith_no_gana_en_razonamiento():
    """Ornith es especialista en código, NO en razonar: el catálogo lo refleja
    (si esto se rompe, el reparto deja de tener sentido)."""
    from app.mel.catalog import score_of
    ornith = ModelRef("ollama", ORNITH_9B, True)
    deepseek = ModelRef("ollama", "deepseek-r1:14b", True)
    assert score_of(ornith, Capability.CODE) > score_of(deepseek, Capability.CODE)
    assert score_of(deepseek, Capability.REASON) > score_of(ornith, Capability.REASON)


def test_solo_los_de_vision_puntuan_alto_en_vision():
    from app.mel.catalog import score_of
    vl = ModelRef("ollama", "qwen2.5vl:7b", True)
    normal = ModelRef("ollama", "qwen3:14b", True)
    assert score_of(vl, Capability.VISION) > 70
    assert score_of(normal, Capability.VISION) < 50


# ---------------------------------------------------------------------------
# registry: los locales habilitados son candidatos propios
# ---------------------------------------------------------------------------
def test_registry_expone_un_modelref_por_modelo_local(monkeypatch):
    from app.mel import registry

    monkeypatch.setattr(registry, "_enabled_local_tags",
                        lambda: ["qwen3:14b", ORNITH_9B])
    refs = registry.list_available()
    keys = {r.key for r in refs}
    assert "ollama:qwen3:14b" in keys
    assert f"ollama:{ORNITH_9B}" in keys
    assert all(r.is_local for r in refs if r.provider == "ollama")


def test_registry_no_duplica_si_el_local_ya_estaba_configurado(monkeypatch):
    """El modelo del proveedor `ollama` y un local con el MISMO tag no pueden
    aparecer dos veces (rompería las cadenas del MEL con un duplicado)."""
    from app.mel import registry

    monkeypatch.setattr(registry, "_enabled_local_tags", lambda: ["llama3"])
    keys = [r.key for r in registry.list_available()]
    assert keys.count("ollama:llama3") <= 1


def test_ollama_with_model_comparte_conexion_y_cambia_modelo():
    from app.ai.providers.ollama_provider import OllamaProvider

    p = OllamaProvider(model="llama3")
    client = p._get_client()
    clone = p.with_model("qwen3:14b")
    assert clone.model == "qwen3:14b"
    assert p.model == "llama3"                  # el original no se toca
    assert clone._get_client() is client        # misma conexión (doc 12 A2)
    assert p.with_model("llama3") is p          # mismo modelo -> coste cero


# ---------------------------------------------------------------------------
# Claude Code (CLI)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_claude_code_sin_cli_instalado_error_claro(monkeypatch):
    from app.ai.providers import claude_code_provider as ccp

    monkeypatch.setattr(ccp, "_find_cli", lambda: None)
    p = ccp.ClaudeCodeProvider()
    r = await p.generate("hola")
    assert r["error"] is True
    assert "no encontrado" in r["response"].lower()
    assert await p.health_check() is False


@pytest.mark.anyio
async def test_claude_code_parsea_la_salida_json(monkeypatch):
    from app.ai.providers import claude_code_provider as ccp

    monkeypatch.setattr(ccp, "_find_cli", lambda: "claude")
    fake = MagicMock()
    fake.returncode = 0
    fake.communicate = AsyncMock(return_value=(
        b'{"result":"hola desde el CLI","model":"sonnet",'
        b'"usage":{"input_tokens":10,"output_tokens":5},"session_id":"s1"}', b"",
    ))
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=fake)):
        r = await ccp.ClaudeCodeProvider().generate("hola")
    assert r.get("error") is None
    assert r["response"] == "hola desde el CLI"
    assert r["tokens"] == 15


@pytest.mark.anyio
async def test_claude_code_fallo_de_sesion_sugiere_login(monkeypatch):
    from app.ai.providers import claude_code_provider as ccp

    monkeypatch.setattr(ccp, "_find_cli", lambda: "claude")
    fake = MagicMock()
    fake.returncode = 1
    fake.communicate = AsyncMock(return_value=(b"", b"Not logged in: run auth"))
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=fake)):
        r = await ccp.ClaudeCodeProvider().generate("hola")
    assert r["error"] is True
    assert "inicia sesión" in r["response"]


def test_claude_code_esta_en_el_catalogo_y_no_pide_key():
    from app.ai.ai_manager import NO_KEY_PROVIDERS, PROVIDER_CLASSES
    from app.ai.catalog import get_provider_info

    assert "claude_code" in PROVIDER_CLASSES
    assert "claude_code" in NO_KEY_PROVIDERS
    assert get_provider_info("claude_code")["requires_key"] is False


# ---------------------------------------------------------------------------
# Codex CLI (OpenAI) — gemelo de claude_code (2026-07-24)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_codex_sin_cli_instalado_error_claro(monkeypatch):
    from app.ai.providers import codex_provider as cxp

    monkeypatch.setattr(cxp, "_find_cli", lambda: None)
    p = cxp.CodexProvider()
    r = await p.generate("hola")
    assert r["error"] is True
    assert "no encontrado" in r["response"].lower()
    assert await p.health_check() is False


@pytest.mark.anyio
async def test_codex_exec_readonly_y_sin_model_por_defecto(monkeypatch):
    from app.ai.providers import codex_provider as cxp

    monkeypatch.setattr(cxp, "_find_cli", lambda: "codex")
    fake = MagicMock()
    fake.returncode = 0
    fake.communicate = AsyncMock(return_value=(b"respuesta de codex", b""))
    mock_exec = AsyncMock(return_value=fake)
    with patch("asyncio.create_subprocess_exec", new=mock_exec):
        r = await cxp.CodexProvider().generate("hola")
    assert r.get("error") is None
    assert r["response"] == "respuesta de codex"
    args = list(mock_exec.call_args.args)
    assert args[1] == "exec"                         # modo NO interactivo
    assert "-s" in args and "read-only" in args      # sandbox de solo lectura explícito
    assert "--model" not in args                     # por defecto NO fija ningún id de modelo


@pytest.mark.anyio
async def test_codex_pasa_model_solo_si_configurado(monkeypatch):
    from app.ai.providers import codex_provider as cxp

    monkeypatch.setattr(cxp, "_find_cli", lambda: "codex")
    fake = MagicMock()
    fake.returncode = 0
    fake.communicate = AsyncMock(return_value=(b"ok", b""))
    mock_exec = AsyncMock(return_value=fake)
    with patch("asyncio.create_subprocess_exec", new=mock_exec):
        await cxp.CodexProvider(model="gpt-5.6-terra").generate("hola")
    args = list(mock_exec.call_args.args)
    assert "--model" in args and "gpt-5.6-terra" in args


@pytest.mark.anyio
async def test_codex_fallo_de_sesion_sugiere_login(monkeypatch):
    from app.ai.providers import codex_provider as cxp

    monkeypatch.setattr(cxp, "_find_cli", lambda: "codex")
    fake = MagicMock()
    fake.returncode = 1
    # stderr REAL de codex sin sesión: banner largo al principio + el 401 al
    # final (verificado en vivo con codex-cli 0.145.0). El banner supera 500
    # chars, así que la pista de login SOLO sobrevive si se muestra la COLA y el
    # hint se añade tras truncar — esto blinda esa regresión.
    banner = ("OpenAI Codex v0.145.0\nworkdir: X\nmodel: gpt-5.6-sol\n" + ("ruido " * 120))
    stderr = (banner + "\nERROR: unexpected status 401 Unauthorized: Missing bearer or basic "
                        "authentication in header, url: https://api.openai.com/v1/responses").encode()
    fake.communicate = AsyncMock(return_value=(b"", stderr))
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=fake)):
        r = await cxp.CodexProvider().generate("hola")
    assert r["error"] is True
    assert "codex login" in r["response"]        # la pista sobrevive al truncado
    assert "401" in r["response"]                # y se ve el error real (la cola), no el banner


def test_codex_esta_en_el_catalogo_y_no_pide_key():
    from app.ai.ai_manager import NO_KEY_PROVIDERS, PROVIDER_CLASSES
    from app.ai.catalog import get_provider_info
    from app.mel.catalog import Capability, is_local, unfit_for

    assert "codex" in PROVIDER_CLASSES
    assert "codex" in NO_KEY_PROVIDERS
    assert get_provider_info("codex")["requires_key"] is False
    # MEL: agente de código → NO apto para chat/clasificar/agentic, y NUNCA local.
    assert Capability.CHAT in unfit_for("codex")
    assert is_local("codex") is False


# ---------------------------------------------------------------------------
# Codex — instalación/login asistidos desde la UI (codex_setup.py)
# ---------------------------------------------------------------------------
def test_codex_setup_status_reporta_no_instalado(monkeypatch):
    from app.api.endpoints import codex_setup as cs

    monkeypatch.setattr(cs, "_find_codex", lambda: None)
    monkeypatch.setattr(cs, "_find_npm", lambda: "/usr/bin/npm")
    monkeypatch.setattr(cs, "_authenticated", lambda: False)
    body = cs.status().body
    import json
    data = json.loads(body)
    assert data["installed"] is False
    assert data["ready"] is False
    assert data["npm_available"] is True


def test_codex_install_idempotente_si_ya_instalado(monkeypatch):
    from app.api.endpoints import codex_setup as cs

    monkeypatch.setattr(cs, "_find_codex", lambda: "/usr/bin/codex")
    import json
    data = json.loads(cs.install().body)
    assert data["started"] is False   # ya instalado → no relanza


def test_codex_login_requiere_estar_instalado(monkeypatch):
    from app.api.endpoints import codex_setup as cs

    monkeypatch.setattr(cs, "_find_codex", lambda: None)
    import json
    data = json.loads(cs.login().body)
    assert data["started"] is False   # sin CLI no se puede iniciar sesión


def test_codex_install_worker_falla_claro_sin_npm(monkeypatch):
    from app.api.endpoints import codex_setup as cs

    monkeypatch.setattr(cs, "_find_npm", lambda: None)
    cs._INSTALL.update(status="idle", detail=None)
    cs._install_worker()
    assert cs._INSTALL["status"] == "failed"
    assert "npm" in (cs._INSTALL["detail"] or "").lower()


def test_claude_code_no_cuenta_como_local_para_offline():
    """Corre en el equipo, pero necesita internet + sesión: si se marcara local,
    la política Offline contaría con él estando sin conexión."""
    from app.mel.catalog import is_local
    assert is_local("claude_code", "sonnet") is False
