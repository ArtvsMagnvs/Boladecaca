# tests/test_briefing_config.py — Briefing 2.0: config + noticias + segmentos
# (PU4b, doc 35). Contratos que blinda:
#   1. Config: defaults completos (los 5 temas del usuario), round-trip
#      guardar/leer, fusión aditiva sobre config vieja, validación con
#      mensajes concretos (horario inválido, tema sin query…).
#   2. arm_prep_jobs: un job por horario a slot − prep_minutes, quita los
#      viejos (idempotente), scheduler INYECTADO (fake — sin APScheduler).
#   3. news.prepare: filtro de fuentes bloqueadas/preferidas determinista,
#      respaldo determinista si el LLM falla, degradación honesta sin
#      proveedor (unavailable=True, jamás noticias inventadas), cache
#      round-trip.
#   4. build_spoken_segments: secciones apagadas NO salen, refs/focus
#      correctos para el show, noticias solo de cache (spoken_per_topic),
#      día vacío honesto.
#   5. Endpoints: GET/PUT config (400 con motivo en inválida), GET /briefing
#      incluye spoken_segments.
import json

import pytest

from app.db.database import Base, Config, SessionLocal, engine
from app.memory import briefing, briefing_config, news


@pytest.fixture(autouse=True)
def _clean_config_rows():
    Base.metadata.create_all(bind=engine)

    def _wipe():
        db = SessionLocal()
        try:
            db.query(Config).filter(
                Config.key.in_(["briefing.config", "briefing.news_cache"])
            ).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

    _wipe()
    yield
    _wipe()


# ---------------------------------------------------------------------------
# 1) Config
# ---------------------------------------------------------------------------
def test_config_defaults_traen_los_5_temas_del_usuario():
    cfg = briefing_config.get_config()
    ids = {t["id"] for t in cfg["news"]["topics"]}
    assert {"geo_global", "geo_es", "ia_general", "ia_claude", "ia_tools"} <= ids
    assert cfg["schedules"] == ["08:00"]
    assert cfg["sections"]["news"] is True
    assert "contrastado" in cfg["news"]["prompt"]


def test_config_round_trip_y_fusion_aditiva():
    saved = briefing_config.save_config({
        "schedules": ["8:00", "14:00", "21:00"],
        "sections": {"news": False},
        "news": {"prompt": "solo IA", "blocked_sources": ["www.Ejemplo.com"]},
    })
    assert saved["schedules"] == ["08:00", "14:00", "21:00"]  # normalizado y ordenado
    assert saved["sections"]["news"] is False
    assert saved["sections"]["email"] is True          # lo no tocado conserva el default
    assert saved["news"]["blocked_sources"] == ["ejemplo.com"]
    assert saved["news"]["topics"], "los temas default sobreviven a un PUT parcial"

    again = briefing_config.get_config()
    assert again["schedules"] == ["08:00", "14:00", "21:00"]
    assert again["news"]["prompt"] == "solo IA"


@pytest.mark.parametrize("bad,frag", [
    ({"schedules": []}, "al menos un horario"),
    ({"schedules": ["25:00"]}, "horario inválido"),
    ({"schedules": ["ocho"]}, "horario inválido"),
    ({"prep_minutes_before": 2}, "entre 5 y 120"),
    ({"news": {"topics": [{"label": "X", "query": ""}]}}, "label"),
])
def test_config_invalida_lanza_con_motivo(bad, frag):
    with pytest.raises(ValueError) as e:
        briefing_config.save_config(bad)
    assert frag in str(e.value)


def test_config_corrupta_en_bd_cae_a_defaults():
    db = SessionLocal()
    try:
        db.add(Config(key="briefing.config", value="{esto no es json"))
        db.commit()
    finally:
        db.close()
    cfg = briefing_config.get_config()
    assert cfg["schedules"] == ["08:00"]


# ---------------------------------------------------------------------------
# 2) arm_prep_jobs (scheduler fake inyectado)
# ---------------------------------------------------------------------------
class _FakeScheduler:
    def __init__(self):
        self.cron: dict[str, tuple[int, int]] = {}

    def jobs(self):
        return list(self.cron)

    def remove_job(self, id):
        self.cron.pop(id, None)

    def add_cron_job(self, func, *, hour, minute, id):
        self.cron[id] = (hour, minute)


def test_arm_prep_jobs_un_job_por_horario_a_slot_menos_prep():
    briefing_config.save_config({"schedules": ["08:00", "21:15"], "prep_minutes_before": 30})
    sched = _FakeScheduler()
    sched.cron["briefing_prep_9999"] = (9, 9)  # residuo viejo: debe desaparecer
    armed = briefing_config.arm_prep_jobs(sched)
    assert set(armed) == {"briefing_prep_0800", "briefing_prep_2115"}
    assert sched.cron["briefing_prep_0800"] == (7, 30)
    assert sched.cron["briefing_prep_2115"] == (20, 45)
    assert "briefing_prep_9999" not in sched.cron


def test_arm_prep_jobs_cruza_medianoche():
    briefing_config.save_config({"schedules": ["00:10"], "prep_minutes_before": 30})
    sched = _FakeScheduler()
    briefing_config.arm_prep_jobs(sched)
    assert sched.cron["briefing_prep_0010"] == (23, 40)


# ---------------------------------------------------------------------------
# 3) news.prepare
# ---------------------------------------------------------------------------
def _fake_items(prefix, n=6, dom="ejemplo.com"):
    return [
        {
            "title": f"{prefix} noticia {i}",
            "url": f"https://{dom}/{prefix}/{i}",
            "description": f"Descripción {i} de {prefix}",
            "source": dom,
        }
        for i in range(n)
    ]


@pytest.mark.anyio
async def test_news_prepare_filtra_bloqueadas_y_prefiere(monkeypatch):
    cfg = briefing_config.save_config({
        "news": {
            "topics": [{"id": "t1", "label": "Tema 1", "query": "q"}],
            "blocked_sources": ["basura.com"],
            "preferred_sources": ["bueno.org"],
            "per_topic": 3,
        },
    })

    async def _fetch(topic):
        return (
            _fake_items("mala", 2, dom="basura.com")
            + _fake_items("neutra", 2, dom="neutro.net")
            + _fake_items("buena", 2, dom="bueno.org")
        )

    monkeypatch.setattr(news, "_fetch_topic", _fetch)

    async def _no_llm(*a, **k):
        return None
    monkeypatch.setattr(news, "_curate_llm", _no_llm)

    cache = await news.prepare(cfg)
    assert cache["unavailable"] is False
    items = cache["topics"][0]["items"]
    assert len(items) == 3
    assert all("basura.com" not in (it["url"] or "") for it in items)
    assert "bueno.org" in items[0]["url"], "las preferidas van delante"
    assert items[0]["id"] == "t1:0"
    assert items[0]["summary"], "el respaldo determinista pone resumen"

    # Round-trip de cache
    again = news.get_cached()
    assert again and again["topics"][0]["items"][0]["title"] == items[0]["title"]


@pytest.mark.anyio
async def test_fetch_topic_propaga_freshness_a_la_busqueda(monkeypatch):
    # [hotfix 2026-08-01] causa raíz del reporte original ("no me trae la
    # noticia de Ceuta, me trae debates de hace semanas"): sin ventana de
    # actualidad, ambos proveedores ordenan por relevancia, no por fecha.
    seen = {}

    async def _fake_search(vertical, query, count, freshness=None):
        seen["freshness"] = freshness
        return {"success": True, "result": {"items": []}}

    import app.tools.search_tool as search_tool
    monkeypatch.setattr(search_tool, "_search", _fake_search)
    await news._fetch_topic({"id": "t1", "query": "q", "vertical": "news", "freshness": "w"})
    assert seen["freshness"] == "w"

    seen.clear()
    await news._fetch_topic({"id": "t2", "query": "q", "vertical": "news"})  # sin freshness explícito
    assert seen["freshness"] == "d", "por defecto se acota a las últimas 24h"


@pytest.mark.anyio
async def test_news_prepare_sin_proveedor_degrada_honesto(monkeypatch):
    async def _boom(topic):
        raise RuntimeError("no hay ningun proveedor de busqueda configurado")
    monkeypatch.setattr(news, "_fetch_topic", _boom)

    cache = await news.prepare()
    assert cache["unavailable"] is True
    assert "proveedor" in cache["reason"]
    assert cache["topics"] == []


@pytest.mark.anyio
async def test_news_prepare_llm_vacio_explicito_no_se_rellena(monkeypatch):
    # [hotfix 2026-08-01] Si el LLM procesó el tema y decidió que NINGÚN
    # candidato era noticia real (lista vacía explícita), el respaldo
    # determinista NO debe rellenar con los primeros N sin filtrar — eso
    # era justo el bug reportado (debates/análisis viejos coincidiendo con
    # "geopolítica España" mientras la noticia real del día se ignoraba).
    cfg = briefing_config.save_config({
        "news": {"topics": [{"id": "t1", "label": "Tema 1", "query": "q"}], "per_topic": 3},
    })

    async def _fetch(topic):
        return _fake_items("x", 5)
    monkeypatch.setattr(news, "_fetch_topic", _fetch)

    async def _llm(per_topic, prompt, topics_items):
        return {"t1": []}  # el LLM decidió explícitamente: nada real hoy
    monkeypatch.setattr(news, "_curate_llm", _llm)

    cache = await news.prepare(cfg)
    items = cache["topics"][0]["items"]
    assert items == [], "una lista vacía explícita del LLM no se rellena con respaldo"


@pytest.mark.anyio
async def test_news_prepare_llm_ignora_tema_si_usa_respaldo(monkeypatch):
    # Contraste con el test anterior: si el LLM ni siquiera menciona el
    # tema (JSON incompleto, no "decidió vacío"), el respaldo SÍ debe
    # cubrirlo — la distinción es "decisión explícita" vs "fallo/omisión".
    cfg = briefing_config.save_config({
        "news": {"topics": [{"id": "t1", "label": "Tema 1", "query": "q"}], "per_topic": 3},
    })

    async def _fetch(topic):
        return _fake_items("x", 5)
    monkeypatch.setattr(news, "_fetch_topic", _fetch)

    async def _llm(per_topic, prompt, topics_items):
        return {}  # el tema ni aparece en la respuesta del LLM
    monkeypatch.setattr(news, "_curate_llm", _llm)

    cache = await news.prepare(cfg)
    items = cache["topics"][0]["items"]
    assert len(items) == 3, "tema ausente de la respuesta del LLM sí usa respaldo"


@pytest.mark.anyio
async def test_news_prepare_curador_llm_elige_y_resume(monkeypatch):
    cfg = briefing_config.save_config({
        "news": {"topics": [{"id": "t1", "label": "Tema 1", "query": "q"}], "per_topic": 2},
    })

    async def _fetch(topic):
        return _fake_items("x", 5)
    monkeypatch.setattr(news, "_fetch_topic", _fetch)

    async def _llm(per_topic, prompt, topics_items):
        return {"t1": [{"i": 4, "summary": "El resumen curado."}]}
    monkeypatch.setattr(news, "_curate_llm", _llm)

    cache = await news.prepare(cfg)
    items = cache["topics"][0]["items"]
    assert len(items) == 1
    assert items[0]["title"] == "x noticia 4"
    assert items[0]["summary"] == "El resumen curado."


# ---------------------------------------------------------------------------
# [hotfix 2026-08-02] "count" por tema — el usuario pidió elegir cuántas
# noticias quiere de CADA tema, no un número global uniforme para los 5.
# ---------------------------------------------------------------------------
def test_config_topic_count_opcional_se_valida_y_persiste():
    cfg = briefing_config.save_config({
        "news": {
            "topics": [
                {"id": "t1", "label": "Tema con count", "query": "q", "count": 6},
                {"id": "t2", "label": "Tema sin count", "query": "q"},
            ],
            "per_topic": 4,
        },
    })
    topics = {t["id"]: t for t in cfg["news"]["topics"]}
    assert topics["t1"]["count"] == 6
    assert "count" not in topics["t2"], "sin count explícito, no se guarda nada (usa el default global)"


def test_config_topic_count_se_acota_a_1_8():
    cfg = briefing_config.save_config({
        "news": {"topics": [{"id": "t1", "label": "T", "query": "q", "count": 99}]},
    })
    assert cfg["news"]["topics"][0]["count"] == 8

    cfg2 = briefing_config.save_config({
        "news": {"topics": [{"id": "t1", "label": "T", "query": "q", "count": 0}]},
    })
    assert cfg2["news"]["topics"][0]["count"] == 1


def test_config_topic_count_invalido_lanza():
    with pytest.raises(ValueError, match="número de noticias"):
        briefing_config.save_config({
            "news": {"topics": [{"id": "t1", "label": "T", "query": "q", "count": "muchas"}]},
        })


@pytest.mark.anyio
async def test_news_prepare_respeta_count_distinto_por_tema(monkeypatch):
    # Dos temas, cada uno con su propio "count" — el respaldo determinista
    # (sin LLM) debe recortar cada uno al SUYO, no al global.
    cfg = briefing_config.save_config({
        "news": {
            "topics": [
                {"id": "mucho", "label": "Mucho", "query": "q", "count": 5},
                {"id": "poco", "label": "Poco", "query": "q", "count": 1},
            ],
            "per_topic": 3,  # default, ninguno de los dos temas lo usa
        },
    })

    async def _fetch(topic):
        return _fake_items(topic["id"], 6)
    monkeypatch.setattr(news, "_fetch_topic", _fetch)

    async def _no_llm(*a, **k):
        return None
    monkeypatch.setattr(news, "_curate_llm", _no_llm)

    cache = await news.prepare(cfg)
    by_id = {t["id"]: t["items"] for t in cache["topics"]}
    assert len(by_id["mucho"]) == 5
    assert len(by_id["poco"]) == 1


@pytest.mark.anyio
async def test_news_prepare_usa_default_global_si_tema_no_fija_count(monkeypatch):
    cfg = briefing_config.save_config({
        "news": {"topics": [{"id": "t1", "label": "T", "query": "q"}], "per_topic": 2},
    })

    async def _fetch(topic):
        return _fake_items("x", 6)
    monkeypatch.setattr(news, "_fetch_topic", _fetch)

    async def _no_llm(*a, **k):
        return None
    monkeypatch.setattr(news, "_curate_llm", _no_llm)

    cache = await news.prepare(cfg)
    assert len(cache["topics"][0]["items"]) == 2


@pytest.mark.anyio
async def test_news_prepare_curador_recibe_el_count_de_cada_tema(monkeypatch):
    # El curador LLM debe recibir, POR TEMA, su propio tope — no un único
    # número global — para que pueda elegir hasta ese número en cada uno.
    cfg = briefing_config.save_config({
        "news": {
            "topics": [
                {"id": "t1", "label": "T1", "query": "q", "count": 5},
                {"id": "t2", "label": "T2", "query": "q", "count": 1},
            ],
        },
    })

    async def _fetch(topic):
        return _fake_items(topic["id"], 6)
    monkeypatch.setattr(news, "_fetch_topic", _fetch)

    seen = {}

    async def _llm(counts, prompt, topics_items):
        seen.update(counts)
        return None
    monkeypatch.setattr(news, "_curate_llm", _llm)

    await news.prepare(cfg)
    assert seen == {"t1": 5, "t2": 1}


# ---------------------------------------------------------------------------
# [hotfix 2026-08-02] no dejar frases a medias en el resumen (afecta a la
# locución del briefing: una frase cortada suena literalmente cortada).
# ---------------------------------------------------------------------------
def test_complete_sentences_no_corta_si_ya_cabe():
    text = "Una frase corta."
    assert news._complete_sentences(text, 220, 420) == text


def test_complete_sentences_corta_en_el_punto_mas_cercano():
    text = (
        "Primera frase completa aquí. Segunda frase completa aquí también. "
        "Tercera frase que sobra y no debería aparecer nunca en el resultado final."
    )
    out = news._complete_sentences(text, 60, 200)
    assert out.endswith("."), "termina en un fin de frase real, no a medias"
    assert "Primera frase" in out
    assert "Tercera frase" not in out


def test_complete_sentences_nunca_deja_media_frase_sin_punto():
    # Objetivo de recorte cae A MITAD de una frase larga sin otro punto
    # cercano por delante — antes: `desc[:217] + "…"` cortaba ahí mismo.
    # Ahora: sigue hasta el punto siguiente en vez de partir la frase.
    text = "Esta es una frase deliberadamente muy larga que sigue y sigue y sigue sin ningún punto hasta el final, donde por fin termina."
    out = news._complete_sentences(text, 40, 200)
    assert out == text, "sin fin de frase cercano al objetivo, sigue hasta el final real"
    assert out.endswith(".")


def test_complete_sentences_sin_puntuacion_devuelve_completo():
    text = "x" * 500  # nunca hay fin de frase, ni siquiera en el hard_cap
    out = news._complete_sentences(text, 100, 200)
    assert out == text, "mejor un texto largo entero que uno cortado sin honestidad"


def test_det_summary_no_deja_frase_a_medias():
    it = {"description": "Frase uno completa aquí. " * 20}  # muy larga, muchas frases cortas
    out = news._det_summary(it)
    assert out.endswith("."), "el respaldo determinista también termina en frase completa"
    assert len(out) <= 420  # no se dispara sin control


# ---------------------------------------------------------------------------
# 4) build_spoken_segments
# ---------------------------------------------------------------------------
_DATA = {
    "date": "2026-08-01",
    "triage_counts": {}, "triaged_total": 0,
    "urgent_pending": {
        "count": 2,
        "items": [
            {"email_id": "e1", "sender": "Jefe <jefe@x.com>", "subject": "Servidor caído"},
            {"email_id": "e2", "sender": "cliente@x.com", "subject": None},
        ],
    },
    "agenda": [{"title": "Reunión M3", "start": "2026-08-01T10:00:00"}],
    "conversations_count": 0,
    "workspace": {
        "active_milestones": [
            {"project_id": 7, "project_name": "Cordyceps", "name": "v0.2", "ratio": 0.42, "done": 5, "total": 12},
        ],
        "upcoming_deadlines": [{"task_id": 1, "title": "Entregar GDD", "due_date": "2026-08-03", "project_id": 7}],
        "blocked": [],
    },
}

_NEWS = {
    "prepared_at": "2026-08-01T07:30:00", "slot": "08:00", "unavailable": False,
    "topics": [{
        "id": "ia_claude", "label": "Claude / Anthropic",
        "items": [
            {"id": "ia_claude:0", "title": "Anthropic publica X", "summary": "Resumen corto.", "url": "https://a", "source": "anthropic.com", "image": None, "published": None},
            {"id": "ia_claude:1", "title": "Otra más", "summary": "Otro resumen.", "url": "https://b", "source": "b.com", "image": None, "published": None},
            {"id": "ia_claude:2", "title": "Tercera", "summary": "S3.", "url": "https://c", "source": "c.com", "image": None, "published": None},
        ],
    }],
}


def test_segments_estructura_completa_con_focus():
    cfg = briefing_config.get_config()
    segs = briefing.build_spoken_segments(_DATA, "Ayer cerraste 3 tareas.", _NEWS, cfg, hour=8)
    kinds = [s["kind"] for s in segs]
    assert kinds == ["greeting", "email", "calendar", "projects", "tasks", "news", "yesterday"]

    email = segs[kinds.index("email")]
    assert email["refs"]["items"][0]["email_id"] == "e1"
    assert email["steps"][1]["focus"] == "e1"
    assert "Jefe" in email["steps"][1]["text"] and "Servidor caído" in email["steps"][1]["text"]

    proj = segs[kinds.index("projects")]
    assert proj["steps"][0]["focus"] == "proj:7"
    assert "42 por ciento" in proj["steps"][0]["text"]

    news_seg = segs[kinds.index("news")]
    focos = [st["focus"] for st in news_seg["steps"] if st["focus"]]
    assert focos == ["ia_claude:0", "ia_claude:1"], "spoken_per_topic=2 locuta 2 de 3"
    assert len(news_seg["refs"]["topics"][0]["items"]) == 3, "la pantalla recibe TODOS"

    assert segs[0]["steps"][0]["text"].startswith("Buenos días")
    tarde = briefing.build_spoken_segments(_DATA, "x", None, cfg, hour=15)
    assert tarde[0]["steps"][0]["text"].startswith("Buenas tardes")


def test_segments_respeta_secciones_apagadas_y_dia_vacio():
    cfg = briefing_config.save_config({"sections": {"news": False, "projects": False}})
    segs = briefing.build_spoken_segments(_DATA, "resumen", _NEWS, cfg, hour=8)
    kinds = {s["kind"] for s in segs}
    assert "news" not in kinds and "projects" not in kinds
    assert "email" in kinds

    vacio = briefing.build_spoken_segments(
        {"urgent_pending": {"count": 0, "items": []}, "agenda": [], "workspace": {}},
        "", None, briefing_config.get_config(), hour=8,
    )
    assert len(vacio) == 1
    assert "nada urgente" in vacio[0]["steps"][-1]["text"]


def test_segments_news_unavailable_no_sale():
    cfg = briefing_config.get_config()
    segs = briefing.build_spoken_segments(
        _DATA, "resumen", {"unavailable": True, "reason": "sin proveedor", "topics": []}, cfg, hour=8
    )
    assert "news" not in {s["kind"] for s in segs}


# ---------------------------------------------------------------------------
# 5) Endpoints
# ---------------------------------------------------------------------------
def test_endpoint_config_get_put_y_400(client):
    r = client.get("/api/memory/briefing/config")
    assert r.status_code == 200
    assert r.json()["schedules"] == ["08:00"]

    r = client.put("/api/memory/briefing/config", json={"schedules": ["09:30", "20:00"]})
    assert r.status_code == 200
    assert r.json()["schedules"] == ["09:30", "20:00"]
    assert client.get("/api/memory/briefing/config").json()["schedules"] == ["09:30", "20:00"]

    r = client.put("/api/memory/briefing/config", json={"schedules": ["mediodía"]})
    assert r.status_code == 400
    assert "horario inválido" in r.json()["detail"]


def test_endpoint_briefing_incluye_spoken_segments(client, monkeypatch):
    from app.memory import summarizer

    monkeypatch.setattr(summarizer, "gather_day_data", lambda d: dict(_DATA))
    r = client.get("/api/memory/briefing")
    assert r.status_code == 200
    segs = r.json()["spoken_segments"]
    assert isinstance(segs, list) and segs[0]["kind"] == "greeting"
    assert any(s["kind"] == "email" for s in segs)
