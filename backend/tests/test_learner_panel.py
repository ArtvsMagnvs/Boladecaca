# tests/test_learner_panel.py — V1.1 L4: la cara visible del Learner
#
# El panel no añade lógica: la EXPONE. Así que lo que se prueba aquí no es el
# aprendizaje (eso está en los otros archivos) sino que lo aprendido LLEGA al
# usuario y que los botones que se le ofrecen son los correctos — incluida la
# garantía que impide ofrecer "Aceptar" para algo que nadie puede aplicar.
from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from app.db.database import Base, SessionLocal, engine
from app.learner import proposal_service, skill_library
from app.learner.models import FailureStat, LearnerProposal, ModelStat, Skill, SkillEvent
from app.learner.stats import record_failures

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _limpio():
    Base.metadata.create_all(bind=engine)

    def _borra():
        with SessionLocal() as s:
            for modelo in (SkillEvent, Skill, LearnerProposal, ModelStat, FailureStat):
                s.query(modelo).delete()
            s.commit()
    _borra()
    yield
    _borra()


async def _propuesta(kind="skill_new", estado="candidate", **payload):
    pid = await proposal_service.create(
        kind=kind, risk="medium" if kind == "skill_new" else "low",
        state="observed", title="Resumen semanal",
        summary="Esto se ha hecho 3 veces.",
        payload=payload or {"name": "Resumen", "description": "d",
                            "definition": {"steps": ["a", "b"]}, "tools": ["document"]})
    for i in range(3):
        await proposal_service.add_evidence(pid, {
            "kind": "judged_success", "context_key": f"mision-{i}",
            "payload": {"goal": "resumen"}})
    return pid


class TestBandeja:
    async def test_lo_que_espera_al_usuario_sale_en_lenguaje_llano(self, client):
        await _propuesta()
        data = client.get("/api/learner/proposals").json()

        assert data["waiting_for_you"] == 1
        p = data["proposals"][0]
        assert p["kind_label"] == "Procedimiento nuevo", "el kind técnico no sale a la UI"
        assert p["risk_label"] == "riesgo medio"
        assert p["evidence_count"] == 3
        assert len(p["mission_ids"]) == 3, (
            "la evidencia se enlaza: una propuesta que no se puede comprobar "
            "es una propuesta que hay que creerse")
        assert p["applicable"] is True

    async def test_lo_que_no_se_puede_aplicar_lo_dice(self, client):
        """`config_fix` no tiene applier — configurar es del usuario. El panel
        tiene que ofrecer "Ir a Ajustes", no "Aceptar", y lo sabe por este
        campo: la garantía vive en el backend (L1), aquí solo se refleja."""
        await _propuesta(kind="config_fix", settings_tab="conexiones",
                         component="tool:search")
        p = client.get("/api/learner/proposals").json()["proposals"][0]
        assert p["applicable"] is False
        assert p["settings_tab"] == "conexiones"
        assert p["kind_label"] == "Falta configurar algo"

    async def test_lo_que_aun_acumula_no_le_pide_nada_al_usuario(self, client):
        pid = await proposal_service.create(
            kind="skill_new", risk="medium", state="observed", title="apenas vista",
            payload={"name": "x", "description": "x", "tools": []})
        await proposal_service.add_evidence(pid, {
            "kind": "judged_success", "context_key": "m1", "payload": {}})
        data = client.get("/api/learner/proposals").json()
        assert data["waiting_for_you"] == 0, "una vez no es un patrón: no molesta"
        assert data["proposals"][0]["state"] == "observed"


class TestDecidir:
    async def test_aceptar_es_UN_gesto_y_por_dentro_sigue_la_escalera(self, client):
        pid = await _propuesta()
        r = client.post(f"/api/learner/proposals/{pid}/approve", json={"note": "sí"})
        assert r.status_code == 200 and r.json()["state"] == "consolidated"

        skills = await skill_library.list()
        assert len(skills) == 1
        assert skills[0].status.value == "draft", (
            "ni aceptada nace activa: la escalera sigue mandando por dentro")

    async def test_rechazar_guarda_el_motivo(self, client):
        """El Learner aprende de los noes (doc 15 §8)."""
        pid = await _propuesta()
        assert client.post(f"/api/learner/proposals/{pid}/reject",
                           json={"note": "no me sirve"}).status_code == 200
        decididas = client.get("/api/learner/history").json()["decided"]
        assert decididas[0]["decision_note"] == "no me sirve"
        assert decididas[0]["state"] == "rejected"

    async def test_arrepentirse_funciona_desde_el_panel(self, client):
        pid = await _propuesta()
        client.post(f"/api/learner/proposals/{pid}/approve", json={})
        assert client.post(f"/api/learner/proposals/{pid}/undo").status_code == 200
        skills = await skill_library.list()
        assert skills[0].status.value == "deprecated", "deshacer depreca, no borra"

    async def test_una_propuesta_que_ya_no_existe_no_revienta(self, client):
        assert client.post("/api/learner/proposals/inventada/approve",
                           json={}).status_code == 404
        assert client.post("/api/learner/proposals/inventada/reject",
                           json={}).status_code == 409


class TestSalud:
    async def test_los_fallos_se_explican_sin_jerga(self, client):
        record_failures("m1", [{"kind": "connection", "blame": "external",
                                "component": "model:x:y", "model_key": "x:y",
                                "tool": None, "event_key": None, "detail": "red"}] * 4)
        record_failures("m2", [{"kind": "model_reasoning", "blame": "model",
                                "component": "model:x:y", "model_key": "x:y",
                                "tool": None, "event_key": None, "detail": "atasco"}])
        data = client.get("/api/learner/health").json()

        assert data["total_failures"] == 5
        etiquetas = {b["blame"]: b for b in data["by_blame"]}
        assert etiquetas["external"]["count"] == 4
        assert "no es culpa de Aithera" in etiquetas["external"]["explanation"], (
            "lo ajeno se dice que es ajeno: si no, parece que Aithera falla más "
            "de lo que falla")
        assert etiquetas["external"]["label"] == "Servicios externos"

    async def test_lo_no_atribuido_se_ve(self, client):
        record_failures("m1", [{"kind": "unknown", "blame": "unknown",
                                "component": "?", "model_key": None, "tool": None,
                                "event_key": None, "detail": ""}])
        data = client.get("/api/learner/health").json()
        sin = [b for b in data["by_blame"] if b["blame"] == "unknown"][0]
        assert sin["count"] == 1
        assert "esconderse" in sin["explanation"]

    async def test_un_modelo_con_una_sola_mision_no_encabeza_el_ranking(self, client):
        """Una racha no es evidencia — la misma disciplina de la escalera,
        aplicada a lo que se le enseña al usuario."""
        with SessionLocal() as s:
            s.add(ModelStat(capability="mission", provider="p", model="afortunado",
                            missions=1, missions_ok=1, calls=1, updated_at=datetime.utcnow()))
            s.commit()
        assert client.get("/api/learner/health").json()["models"] == []

    async def test_sin_nada_todavia_responde_vacio_y_no_rompe(self, client):
        data = client.get("/api/learner/health").json()
        assert data["total_failures"] == 0 and data["by_blame"] == []
        assert client.get("/api/learner/proposals").json()["proposals"] == []


class TestHistorial:
    async def test_distingue_lo_que_ensenaste_de_lo_que_aprendio_mirando(self, client):
        """No es adorno: en el panel, "lo pediste tú" y "lo aprendí observando"
        son dos cosas distintas, y el usuario tiene derecho a saber cuál es
        cuál antes de fiarse."""
        from app.memory import LocalSkill, SkillStatus

        for creador in ("user_taught", "local_learning_loop"):
            await skill_library.create(LocalSkill(
                id=str(uuid.uuid4()), name=f"skill de {creador}", version="1.0.0",
                description="d", definition={}, input_schema={}, output_schema={},
                runtime_agnostic=True, created_by=creador,
                created_at=datetime.utcnow(), status=SkillStatus.DRAFT))

        skills = {s["created_by"]: s for s in
                  client.get("/api/learner/history").json()["skills"]}
        assert skills["user_taught"]["taught_by_user"] is True
        assert skills["local_learning_loop"]["taught_by_user"] is False


class TestAnalizarAhora:
    async def test_el_boton_de_analizar_corre_la_pasada_real(self, client, monkeypatch):
        """Esperar a mañana para ver si el Learner funciona es mala
        experiencia. El botón corre EXACTAMENTE el mismo análisis nocturno."""
        async def _sin_modelo(*a, **k):
            raise RuntimeError("sin proveedor")
        monkeypatch.setattr("app.mel.complete", _sin_modelo)

        r = client.post("/api/learner/analyze")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True and "report" in data
