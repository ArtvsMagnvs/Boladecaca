# tests/test_vault.py — Vault: espejo Markdown (V0.85, doc 07 §9)
#
# Solo escritura en V0.85. Cubre: creacion de archivo, sobreescritura idempotente
# en re-ejecucion, fail-soft ante errores de disco, e integracion con
# summarizer.run_summarizer() y decision_service.store_decision()/link_outcome().
#
# AITHERA_VAULT_PATH ya aisla el vault a un dir temporal (conftest.py) — estos
# tests nunca tocan %APPDATA%/Aithera/vault del usuario real.
from datetime import date

import pytest

from app.memory import memory_router, vault_write_daily_summary, vault_write_decision
from app.memory.vault import VAULT_PATH


# ======================================================================
# write_daily_summary
# ======================================================================

def test_write_daily_summary_crea_archivo_en_YYYY_MM():
    target = date(2026, 7, 13)
    path = vault_write_daily_summary(target, "3 emails triados. 1 urgente pendiente.")

    assert path is not None
    assert path.exists()
    assert path.parent == VAULT_PATH / "2026" / "07"
    assert path.name == "2026-07-13-resumen.md"

    text = path.read_text(encoding="utf-8")
    assert "# Resumen del 2026-07-13" in text
    assert "3 emails triados" in text


def test_write_daily_summary_reejecutar_mismo_dia_sobreescribe():
    target = date(2026, 7, 14)
    path1 = vault_write_daily_summary(target, "Version 1 del resumen.")
    path2 = vault_write_daily_summary(target, "Version 2, mas completa.")

    assert path1 == path2
    text = path2.read_text(encoding="utf-8")
    assert "Version 2" in text
    assert "Version 1" not in text  # sobreescrito, no duplicado


def test_write_daily_summary_fail_soft_ante_error_de_disco(monkeypatch, tmp_path):
    """Si Path.write_text lanza (disco lleno, permisos...), no propaga: solo
    devuelve None. El vault nunca puede romper el job del summarizer."""
    import app.memory.vault as vault_module

    def _boom(*a, **kw):
        raise OSError("disco simulado lleno")

    monkeypatch.setattr(vault_module.Path, "write_text", _boom)
    result = vault_write_daily_summary(date(2026, 7, 15), "contenido")
    assert result is None


# ======================================================================
# write_decision
# ======================================================================

class _FakeDecision:
    """Duck-type minimo de app.db.models.Decision — evita depender de una
    fila SQL real solo para probar el formato del espejo Markdown."""

    def __init__(self, **kw):
        self.id = kw.get("id", "dec-test-1")
        self.title = kw.get("title", "Elegir Opcion B")
        self.body = kw.get("body", "")
        self.reason = kw.get("reason", "")
        self.project = kw.get("project")
        self.impact = kw.get("impact", "med")
        self.status = kw.get("status", "active")
        self.outcome = kw.get("outcome")
        self.mission_id = kw.get("mission_id")
        self.created_at = kw.get("created_at")


def test_write_decision_crea_archivo_con_campos_clave():
    from datetime import datetime

    decision = _FakeDecision(
        id="dec-abc-123",
        title="Elegir Opcion B para el MOS",
        body="Arquitectura definitiva.",
        reason="Contratos de 10 años.",
        project="aithera",
        impact="high",
        status="active",
        created_at=datetime(2026, 7, 13, 10, 0, 0),
    )
    path = vault_write_decision(decision)

    assert path is not None
    assert path.parent == VAULT_PATH / "2026" / "07"
    assert path.name == "dec-abc-123-decision.md"

    text = path.read_text(encoding="utf-8")
    assert "# Elegir Opcion B para el MOS" in text
    assert "Arquitectura definitiva." in text
    assert "**Motivo**: Contratos de 10 años." in text
    assert "**Proyecto**: aithera" in text
    assert "**Impacto**: high" in text


def test_write_decision_sin_created_at_usa_hoy():
    """created_at es nullable en el modelo real solo hasta el commit (default
    en Python); el fallback a 'hoy' evita un crash si llega None."""
    decision = _FakeDecision(id="dec-sin-fecha", created_at=None)
    path = vault_write_decision(decision)
    assert path is not None
    assert path.exists()


def test_write_decision_mismo_id_sobreescribe_no_duplica():
    from datetime import datetime

    created = datetime(2026, 7, 16, 9, 0, 0)
    d1 = _FakeDecision(id="dec-reescribe", status="active", created_at=created)
    d2 = _FakeDecision(id="dec-reescribe", status="superseded", outcome="reemplazada por C", created_at=created)

    path1 = vault_write_decision(d1)
    path2 = vault_write_decision(d2)

    assert path1 == path2
    text = path2.read_text(encoding="utf-8")
    assert "**Estado**: superseded" in text
    assert "**Resultado**: reemplazada por C" in text


# ======================================================================
# Integracion — decision_service escribe tambien el vault
# ======================================================================

@pytest.mark.anyio
async def test_store_decision_escribe_espejo_en_vault():
    from app.services import decision_service
    from app.db.database import SessionLocal
    from app.db.models import Decision

    decision = await decision_service.store_decision(
        title="Decision con espejo en vault",
        body="Cuerpo de prueba",
        project="aithera",
        impact="med",
    )
    expected = VAULT_PATH / str(decision.created_at.year) / f"{decision.created_at.month:02d}" / f"{decision.id}-decision.md"
    assert expected.exists()
    assert "Decision con espejo en vault" in expected.read_text(encoding="utf-8")

    session = SessionLocal()
    try:
        row = session.get(Decision, decision.id)
        if row is not None:
            session.delete(row)
            session.commit()
    finally:
        session.close()


@pytest.mark.anyio
async def test_link_outcome_re_espeja_vault_con_resultado():
    from app.services import decision_service
    from app.db.database import SessionLocal
    from app.db.models import Decision

    decision = await decision_service.store_decision(title="Decision a completar despues")
    await decision_service.link_outcome(decision.id, "Funciono segun lo esperado")

    expected = VAULT_PATH / str(decision.created_at.year) / f"{decision.created_at.month:02d}" / f"{decision.id}-decision.md"
    text = expected.read_text(encoding="utf-8")
    assert "**Resultado**: Funciono segun lo esperado" in text

    session = SessionLocal()
    try:
        row = session.get(Decision, decision.id)
        if row is not None:
            session.delete(row)
            session.commit()
    finally:
        session.close()


# ======================================================================
# Integracion — summarizer escribe tambien el vault
# ======================================================================

@pytest.mark.anyio
@pytest.mark.skipif(
    not memory_router.healthy, reason="ChromaDB no disponible en el entorno de test"
)
async def test_run_summarizer_escribe_espejo_en_vault():
    from app.memory import summarizer

    target = date(2026, 7, 17)
    result = await summarizer.run_summarizer(target)
    assert result["status"] == "ok"

    expected = VAULT_PATH / "2026" / "07" / "2026-07-17-resumen.md"
    assert expected.exists()
    text = expected.read_text(encoding="utf-8")
    assert "# Resumen del 2026-07-17" in text
