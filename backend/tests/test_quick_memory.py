# tests/test_quick_memory.py — mini-chat de memoria (PU10, doc 35)
#
# Contratos que blinda:
#   1. Parseo determinista (0 LLM): "guarda que...", "que sabes de...",
#      "olvida lo de..." se reconocen sin ancla (mini-chat de Ajustes) y solo
#      con ancla explícita ("...en la memoria...") desde el chat principal.
#   2. "guárdame un resumen..." (NEW-7b, un ARCHIVO) NUNCA se confunde con
#      esto, ni siquiera sin ancla.
#   3. Guardar escribe SIEMPRE en `user_context` — la colección que
#      `chat_service.build_system_prompt()` YA inyecta en cada turno — nunca
#      en `mem_personal` genérica.
#   4. Buscar combina preferencias (`user_context`) + hechos del MOS
#      (`mem_personal`). Olvidar borra por coincidencia única/ambigua/ninguna.
#   5. Lo guardado por el mini-chat se APLICA en el siguiente turno de chat
#      (round-trip completo hasta `chat_service._preferences_block`).
#   6. Enganchado en el chat principal (pipeline + orquestador) con ancla.
import pytest

from app.memory import memory_router
from app.memory.memory_manager import memory_manager

pytestmark_chroma = pytest.mark.skipif(
    not memory_router.healthy, reason="ChromaDB no disponible en el entorno de test"
)


# ---------------------------------------------------------------------------
# 1) Parseo determinista — funciones puras, sin I/O
# ---------------------------------------------------------------------------
from app.memory import quick_memory  # noqa: E402


@pytest.mark.parametrize("msg,expected_payload", [
    ("guarda que me gusta el café solo", "me gusta el café solo"),
    # "Guárdame" normaliza a "guardame" (acentos fuera) — coincide con el
    # prefijo "guardame que " igual que su forma sin tilde.
    ("Guárdame que prefiero respuestas cortas", "prefiero respuestas cortas"),
    ("recuerda que trabajo por las tardes", "trabajo por las tardes"),
    ("anota que mi color favorito es el verde", "mi color favorito es el verde"),
    ("save that I prefer short answers", "I prefer short answers"),
])
def test_parse_save_sin_ancla_minichat(msg, expected_payload):
    cmd = quick_memory.parse(msg, require_anchor=False)
    assert cmd is not None and cmd.action == "save"
    assert cmd.payload == expected_payload


def test_parse_save_sin_ancla_NO_dispara_con_require_anchor():
    """Sin mencionar "memoria" explícitamente, el chat principal NO debe
    interceptar esto — sigue el pipeline normal (clasificador/LLM)."""
    assert quick_memory.parse("guarda que me gusta el café solo", require_anchor=True) is None


@pytest.mark.parametrize("msg", [
    "guarda esto en la memoria: cuando me expliques algo técnico, usa lenguaje coloquial",
    "guarda en la memoria que prefiero respuestas cortas",
    "guarda en tu memoria: mi color favorito es el verde",
    "save this in memory: I prefer short answers",
])
def test_parse_save_con_ancla_funciona_en_ambos_contextos(msg):
    for anchor in (True, False):
        cmd = quick_memory.parse(msg, require_anchor=anchor)
        assert cmd is not None and cmd.action == "save", f"anchor={anchor}"
        assert cmd.payload  # no vacío


def test_parse_no_confunde_guardar_archivo_new7b():
    """'Guárdame un resumen de tres líneas' (NEW-7b) es un ARCHIVO, no una
    preferencia — no debe interceptarse ni sin ancla ni con ancla."""
    for anchor in (True, False):
        assert quick_memory.parse("guárdame un resumen de tres líneas", require_anchor=anchor) is None
        assert quick_memory.parse(
            "investiga qué es FastAPI y guárdame un resumen", require_anchor=anchor
        ) is None


@pytest.mark.parametrize("msg,expected_payload", [
    ("¿qué sabes de mi trabajo?", "mi trabajo"),
    ("que sabes sobre mis preferencias", "mis preferencias"),
    ("what do you know about my job?", "my job"),
])
def test_parse_search_sin_ancla_minichat(msg, expected_payload):
    cmd = quick_memory.parse(msg, require_anchor=False)
    assert cmd is not None and cmd.action == "search"
    assert cmd.payload == expected_payload


def test_parse_search_sin_ancla_no_dispara_desde_chat_principal():
    assert quick_memory.parse("¿qué sabes de mi trabajo?", require_anchor=True) is None


@pytest.mark.parametrize("msg", [
    "busca en la memoria mi trabajo",
    "search your memory for my job",
])
def test_parse_search_con_ancla_funciona_en_ambos_contextos(msg):
    for anchor in (True, False):
        cmd = quick_memory.parse(msg, require_anchor=anchor)
        assert cmd is not None and cmd.action == "search"


@pytest.mark.parametrize("msg,expected_payload", [
    ("olvida que me gusta el café", "me gusta el café"),
    ("olvida lo de las tardes", "las tardes"),
    ("forget that I like coffee", "I like coffee"),
])
def test_parse_forget_sin_ancla_minichat(msg, expected_payload):
    cmd = quick_memory.parse(msg, require_anchor=False)
    assert cmd is not None and cmd.action == "forget"
    assert cmd.payload == expected_payload


def test_parse_forget_sin_ancla_no_dispara_desde_chat_principal():
    """'Olvídalo, no importa' es una muletilla de conversación normal, no un
    comando de memoria — solo dispara desde el chat principal con ancla."""
    assert quick_memory.parse("olvida que dije eso antes", require_anchor=True) is None


@pytest.mark.parametrize("msg", [
    "borra de la memoria lo del café",
    "elimina de tu memoria mis preferencias",
    "forget this from memory: I like coffee",
])
def test_parse_forget_con_ancla_funciona_en_ambos_contextos(msg):
    for anchor in (True, False):
        cmd = quick_memory.parse(msg, require_anchor=anchor)
        assert cmd is not None and cmd.action == "forget"


@pytest.mark.parametrize("msg", [
    "",
    "hola, ¿cómo estás?",
    "crea un proyecto llamado Foo",
    "guarda " * 90,  # demasiado largo
])
def test_parse_no_dispara_con_charla_normal(msg):
    assert quick_memory.parse(msg, require_anchor=False) is None
    assert quick_memory.parse(msg, require_anchor=True) is None


# ---------------------------------------------------------------------------
# 2) Ejecución real contra ChromaDB — save/search/forget
# ---------------------------------------------------------------------------
@pytestmark_chroma
class TestExecuteContraChromaReal:
    @pytest.fixture(autouse=True)
    def _cleanup(self):
        creados: list[str] = []
        self._creados = creados
        yield
        for key in creados:
            try:
                memory_manager.delete_user_context(key)
            except Exception:
                pass

    async def _save(self, content: str) -> dict:
        cmd = quick_memory.MemoryCommand(action="save", payload=content)
        res = await quick_memory.execute(cmd)
        if res.get("key"):
            self._creados.append(res["key"])
        return res

    @pytest.mark.anyio
    async def test_save_escribe_en_user_context(self):
        marker = "PU10-test-marker-el usuario prefiere que le hable de tú"
        res = await self._save(marker)
        assert res["ok"] is True
        assert res["action"] == "save"

        items = memory_manager.list_user_context()
        contenidos = [it["content"] for it in items]
        assert marker in contenidos

    @pytest.mark.anyio
    async def test_save_dos_veces_actualiza_no_duplica(self):
        marker = "PU10-test-marker-dedup: le gusta el café solo"
        r1 = await self._save(marker)
        r2 = await self._save(marker)
        assert r1["key"] == r2["key"]

        items = memory_manager.list_user_context()
        coincidencias = [it for it in items if it["content"] == marker]
        assert len(coincidencias) == 1

    @pytest.mark.anyio
    async def test_search_encuentra_lo_guardado(self):
        marker = "PU10-test-marker-busqueda: usa lenguaje muy coloquial en explicaciones técnicas"
        await self._save(marker)

        cmd = quick_memory.MemoryCommand(action="search", payload="lenguaje coloquial explicaciones técnicas")
        res = await quick_memory.execute(cmd)
        assert res["ok"] is True
        assert any(marker in r for r in res.get("results", []))

    @pytest.mark.anyio
    async def test_search_sin_resultados_no_inventa(self):
        cmd = quick_memory.MemoryCommand(
            action="search", payload="xyzzy-inexistente-jamás-guardado-qwerty123"
        )
        res = await quick_memory.execute(cmd)
        assert res["ok"] is True
        assert res.get("results") == []

    @pytest.mark.anyio
    async def test_forget_borra_coincidencia_unica(self):
        marker = "PU10-test-marker-forget-unico: le gusta el senderismo los domingos"
        saved = await self._save(marker)

        cmd = quick_memory.MemoryCommand(action="forget", payload="senderismo los domingos")
        res = await quick_memory.execute(cmd)
        assert res["ok"] is True
        assert res.get("content") == marker

        items = memory_manager.list_user_context()
        assert marker not in [it["content"] for it in items]
        self._creados.remove(saved["key"])  # ya no existe, no reintentar borrarlo en teardown

    @pytest.mark.anyio
    async def test_forget_ninguna_coincidencia(self):
        cmd = quick_memory.MemoryCommand(
            action="forget", payload="algo-que-nunca-se-guardo-abc999"
        )
        res = await quick_memory.execute(cmd)
        assert res["ok"] is True
        assert "ambiguous" not in res

    @pytest.mark.anyio
    async def test_forget_ambiguo_lista_sin_borrar(self):
        m1 = "PU10-test-marker-ambiguo: prefiere reuniones por la mañana temprano"
        m2 = "PU10-test-marker-ambiguo: prefiere reuniones cortas y directas"
        await self._save(m1)
        await self._save(m2)

        cmd = quick_memory.MemoryCommand(action="forget", payload="ambiguo: prefiere reuniones")
        res = await quick_memory.execute(cmd)
        assert res["ok"] is True
        assert res.get("ambiguous") is True

        items = memory_manager.list_user_context()
        contenidos = [it["content"] for it in items]
        assert m1 in contenidos and m2 in contenidos  # nada se borró


# ---------------------------------------------------------------------------
# 3) Aplicado de verdad: lo guardado se inyecta en el SIGUIENTE turno de chat
# ---------------------------------------------------------------------------
@pytestmark_chroma
class TestAplicadoEnElChat:
    @pytest.fixture(autouse=True)
    def _cleanup(self):
        creados: list[str] = []
        self._creados = creados
        yield
        for key in creados:
            try:
                memory_manager.delete_user_context(key)
            except Exception:
                pass

    @pytest.mark.anyio
    async def test_preferencia_guardada_aparece_en_build_system_prompt(self):
        from app.services import chat_service

        marker = "PU10-test-marker-aplicado: cuando explique algo técnico, usar lenguaje muy coloquial"
        cmd = quick_memory.MemoryCommand(action="save", payload=marker)
        res = await quick_memory.execute(cmd)
        self._creados.append(res["key"])

        # Misma query que activaría la búsqueda semántica real de un turno
        # nuevo sobre el mismo tema — sin pasar por ningún LLM.
        prompt = await chat_service.build_system_prompt(
            "explícame cómo funciona un servidor web", history=None,
        )
        assert marker in prompt


# ---------------------------------------------------------------------------
# 4) handle()/try_answer_async — el punto único usado por el endpoint y por
#    el chat principal.
# ---------------------------------------------------------------------------
@pytestmark_chroma
class TestHandleYTryAnswerAsync:
    @pytest.fixture(autouse=True)
    def _cleanup(self):
        creados: list[str] = []
        self._creados = creados
        yield
        for key in creados:
            try:
                memory_manager.delete_user_context(key)
            except Exception:
                pass

    @pytest.mark.anyio
    async def test_handle_minichat_sin_ancla_guarda_y_confirma(self):
        contenido = "PU10-test-marker-handle le gusta trabajar de noche"
        res = await quick_memory.handle(f"guarda que {contenido}", require_anchor=False)
        assert res is not None and res["ok"] is True
        if res.get("key"):
            self._creados.append(res["key"])

    @pytest.mark.anyio
    async def test_handle_texto_no_reconocido_devuelve_none(self):
        assert await quick_memory.handle("hola, ¿qué tal el día?", require_anchor=False) is None

    @pytest.mark.anyio
    async def test_try_answer_async_exige_ancla(self):
        # Sin ancla: no debe responder desde el chat principal.
        assert await quick_memory.try_answer_async("guarda que me gusta el café") is None

    @pytest.mark.anyio
    async def test_try_answer_async_con_ancla_guarda_de_verdad(self):
        marker = "PU10-test-marker-tryanswer: prueba de guardado con ancla"
        reply = await quick_memory.try_answer_async(f"guarda esto en la memoria: {marker}")
        assert reply is not None and marker in reply

        items = memory_manager.list_user_context()
        match = next((it for it in items if it["content"] == marker), None)
        assert match is not None
        self._creados.append(match["key"])


# ---------------------------------------------------------------------------
# 5) Enganchado en el chat principal (pipeline + orquestador) — mismo patrón
#    que test_quick_answers.py (sin clasificador, sin misión).
# ---------------------------------------------------------------------------
@pytestmark_chroma
class TestEngancheEnElChatPrincipal:
    @pytest.fixture(autouse=True)
    def _cleanup(self):
        creados: list[str] = []
        self._creados = creados
        yield
        for key in creados:
            try:
                memory_manager.delete_user_context(key)
            except Exception:
                pass

    @pytest.mark.anyio
    async def test_orquestador_guarda_sin_llm(self, monkeypatch):
        import app.orchestrator as orch
        import app.tie as tie

        async def _boom(text, channel=None):
            raise AssertionError("guardar en memoria NO debe llamar al clasificador LLM")
        monkeypatch.setattr(tie, "classify", _boom)

        marker = "PU10-test-marker-orq: prueba end-to-end del orquestador"
        evs = [ev async for ev in orch.handle_stream(f"guarda esto en la memoria: {marker}")]
        texto = "".join(p for k, p in evs if k == "text")
        assert marker in texto
        assert not any(k == "status" for k, _ in evs)
        assert not any(k == "mission" for k, _ in evs)

        items = memory_manager.list_user_context()
        match = next((it for it in items if it["content"] == marker), None)
        assert match is not None
        self._creados.append(match["key"])

    @pytest.mark.anyio
    async def test_pipeline_handle_stream_guarda_sin_clasificar(self, monkeypatch):
        from app.tie import handle_stream
        from app.tie import pipeline as pl

        async def _boom(text, channel=None):
            raise AssertionError("guardar en memoria NO debe llamar al clasificador LLM")
        monkeypatch.setattr(pl.intents, "classify", _boom)

        marker = "PU10-test-marker-pipeline: prueba end-to-end del pipeline"
        evs = [ev async for ev in handle_stream(f"guarda esto en la memoria: {marker}")]
        texto = "".join(p for k, p in evs if k == "text")
        assert marker in texto

        items = memory_manager.list_user_context()
        match = next((it for it in items if it["content"] == marker), None)
        assert match is not None
        self._creados.append(match["key"])


# ---------------------------------------------------------------------------
# 6) Fix 2026-08-02 (reportado en vivo por el usuario): "¿qué sabes de mí?"
#    devolvía ruido crudo de la ingesta de email (M2) — asuntos/snippets del
#    inbox con `kind="inbox_item"` conviven en `mem_personal` con los hechos
#    curados de R6.5c (`kind=FACT_KIND`). `_do_search` debe restringir SIEMPRE
#    la búsqueda semántica a `kind=FACT_KIND`, nunca a la colección entera.
#    Con un `memory_router` fake (sin I/O real): corre en CUALQUIER entorno,
#    no depende de ChromaDB instalado.
# ---------------------------------------------------------------------------
class _FakeRouterCapturaFiltros:
    """Doble mínimo de `memory_router`: solo implementa `.search()` (lo único
    que `_do_search` usa de él) y registra con qué argumentos se le llamó."""

    def __init__(self):
        self.calls: list[dict] = []

    async def search(self, query, memory_types=None, top_k=5, filters=None):
        self.calls.append(
            {"query": query, "memory_types": memory_types, "top_k": top_k, "filters": filters}
        )
        return []


class TestDoSearchFiltraPorHechosDePerfil:
    @pytest.mark.anyio
    async def test_busca_solo_hechos_de_perfil_no_mem_personal_cruda(self, monkeypatch):
        import app.memory as mem
        from app.memory import profile as _profile
        from app.memory import quick_memory

        fake_router = _FakeRouterCapturaFiltros()
        monkeypatch.setattr(mem, "memory_router", fake_router)

        cmd = quick_memory.MemoryCommand(action="search", payload="qué sabes de mí")
        await quick_memory.execute(cmd)

        assert len(fake_router.calls) == 1, "debe llamar a memory_router.search exactamente una vez"
        call = fake_router.calls[0]
        assert call["memory_types"] == [mem.MemoryType.PERSONAL]
        # EL contrato que este test blinda: sin este filtro, la búsqueda
        # devuelve inbox_item/calendar_event junto a profile_fact — ruido de
        # emails de marketing presentado como "cosas que Aithera sabe de ti".
        assert call["filters"] == {"kind": _profile.FACT_KIND}
