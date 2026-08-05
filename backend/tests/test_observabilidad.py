# tests/test_observabilidad.py — Sesión C, doc 40: observabilidad que sobrevive.
#
# Los tres fallos que cierra (diagnóstico 2026-08-04):
#   1. LOG-2 (doc 34, campaña 00): la suite de tests escribía miles de líneas
#      fake en logs/system.log de PRODUCCIÓN. Cerrado con AITHERA_LOG_DIR
#      (mismo patrón que AITHERA_CHROMA_PATH/AITHERA_VAULT_PATH).
#   2. WindowsSafeRotatingFileHandler TRUNCABA en vez de rotar cuando Windows
#      tiene el archivo bloqueado — destruía el forense de cada reinicio
#      forzado. Ahora desvía a un hermano con timestamp; el bloqueado se deja
#      intacto.
#   3. No había UN comando que respondiera "¿qué falló y por qué?" con el
#      backend apagado — nace scripts/aithera_doctor.py.
from __future__ import annotations

import logging
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
# `scripts/` no tiene __init__.py (paquete de namespace, PEP 420) — basta con
# que backend/ esté en sys.path. `python -m pytest` desde backend/ ya lo
# garantiza, pero se asegura aquí por si la suite se invoca de otra forma.
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ===========================================================================
# 1 — AITHERA_LOG_DIR se respeta (subproceso: el proceso de pytest ya importó
# logging_config con la env del propio conftest)
# ===========================================================================
def test_aithera_log_dir_se_respeta(tmp_path):
    import app.core.logging_config as lc

    repo_log = Path(lc.__file__).resolve().parent.parent.parent / "logs" / "system.log"
    tamano_antes = repo_log.stat().st_size if repo_log.exists() else None

    destino = tmp_path / "logdir"
    code = (
        "import os\n"
        f"os.environ['AITHERA_LOG_DIR'] = r'{destino}'\n"
        "import app.core.logging_config as lc\n"
        "logger = lc.get_system_logger('test_c1')\n"
        "logger.info('linea de prueba AITHERA_LOG_DIR')\n"
        "print('LOG_DIR=' + str(lc.LOGS_DIR))\n"
        "print('SYSTEM_LOG=' + str(lc.SYSTEM_LOG))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(BACKEND_DIR), capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"

    log_dir_line = next(l for l in result.stdout.splitlines() if l.startswith("LOG_DIR="))
    system_log_line = next(l for l in result.stdout.splitlines() if l.startswith("SYSTEM_LOG="))
    assert log_dir_line.split("=", 1)[1] == str(destino)
    system_log_path = Path(system_log_line.split("=", 1)[1])
    assert system_log_path.parent == destino
    assert system_log_path.exists()
    assert "linea de prueba AITHERA_LOG_DIR" in system_log_path.read_text(encoding="utf-8")

    # El log de PRODUCCIÓN del repo no se tocó.
    tamano_despues = repo_log.stat().st_size if repo_log.exists() else None
    assert tamano_despues == tamano_antes


def test_conftest_fija_aithera_log_dir_en_el_propio_proceso():
    """Dentro del proceso de tests, SYSTEM_LOG ya vive bajo AITHERA_LOG_DIR —
    confirma que conftest.py lo fijó ANTES de que nada importara
    logging_config en cascada (si el orden se rompe, este test lo cazaría:
    SYSTEM_LOG apuntaría a backend/logs, no al tmp del conftest)."""
    import os

    import app.core.logging_config as lc

    log_dir_env = os.environ.get("AITHERA_LOG_DIR")
    assert log_dir_env, "conftest.py debería haber fijado AITHERA_LOG_DIR"
    assert str(lc.LOGS_DIR) == log_dir_env
    assert lc.SYSTEM_LOG.parent == Path(log_dir_env)


# ===========================================================================
# 2 — Rollover bloqueado: rota a un hermano, JAMÁS trunca
# ===========================================================================
def test_rollover_bloqueado_no_trunca(tmp_path, monkeypatch):
    from app.core.logging_config import WindowsSafeRotatingFileHandler

    base = tmp_path / "system.log"
    handler = WindowsSafeRotatingFileHandler(
        str(base), maxBytes=10**6, backupCount=3, encoding="utf-8")
    try:
        handler.emit(logging.LogRecord(
            "x", logging.INFO, __file__, 1, "linea original que NO debe perderse",
            None, None))
        handler.stream.flush()
        contenido_original = base.read_text(encoding="utf-8")
        assert "linea original que NO debe perderse" in contenido_original

        def _bloqueado(self):
            raise PermissionError("archivo bloqueado por el proceso anterior")

        monkeypatch.setattr(RotatingFileHandler, "doRollover", _bloqueado)
        handler.doRollover()

        # El archivo original queda INTACTO — antes se truncaba aquí.
        assert base.read_text(encoding="utf-8") == contenido_original
        # baseFilename se desvió a un hermano con timestamp, en el MISMO dir.
        assert handler.baseFilename != str(base)
        hermano = Path(handler.baseFilename)
        assert hermano.parent == tmp_path
        assert hermano.name.startswith("system.") and hermano.name.endswith(".log")

        # Y lo que se escribe DESPUÉS va al hermano, no al bloqueado.
        handler.emit(logging.LogRecord(
            "x", logging.INFO, __file__, 1, "linea tras el rollover", None, None))
        handler.stream.flush()
        assert "linea tras el rollover" in hermano.read_text(encoding="utf-8")
        assert "linea tras el rollover" not in contenido_original
    finally:
        handler.close()


# ===========================================================================
# 3 — Prune acotado de hermanos
# ===========================================================================
def test_prune_sibling_logs_acotado(tmp_path):
    from app.core.logging_config import _prune_sibling_logs

    base = tmp_path / "system.log"
    base.write_text("contenido base", encoding="utf-8")
    hermanos = []
    for i in range(15):
        p = tmp_path / f"system.202608{i:02d}-000000.log"
        p.write_text(f"hermano {i}", encoding="utf-8")
        hermanos.append(p)
    ajeno = tmp_path / "otro_archivo.log"
    ajeno.write_text("no me toques", encoding="utf-8")

    _prune_sibling_logs(base, keep=10)

    quedan = sorted(p.name for p in tmp_path.glob("system.*.log"))
    assert len(quedan) == 10
    assert base.exists() and base.read_text(encoding="utf-8") == "contenido base"
    assert ajeno.exists() and ajeno.read_text(encoding="utf-8") == "no me toques"


def test_prune_sibling_logs_nunca_lanza_con_directorio_roto(tmp_path):
    from app.core.logging_config import _prune_sibling_logs

    # base cuyo padre no existe: la implementación tiene que ser best-effort.
    _prune_sibling_logs(tmp_path / "no_existe" / "system.log", keep=5)  # no debe lanzar


# ===========================================================================
# 4/5 — aithera_doctor.collect() sobre una BD sembrada, read-only
# ===========================================================================
@pytest.fixture
def _doctor_seed():
    """Siembra 1 traza done+outcome, 1 waiting con gate pendiente, y 2 eventos
    de telemetría (tool_call fallida + stalled). Limpieza total al salir
    (patrón LOG-1, igual que test_audit_s7s8_missions)."""
    from app.automation import Approval
    from app.db.database import Base, OrchestratorTrace, SessionLocal, engine as db_engine
    from app.telemetry.models import MissionEvent

    Base.metadata.create_all(bind=db_engine)

    mission_done = "doctor-mission-done"
    mission_waiting = "doctor-mission-waiting"

    def _purge():
        s = SessionLocal()
        try:
            s.query(OrchestratorTrace).filter(
                OrchestratorTrace.mission_id.in_([mission_done, mission_waiting])).delete(
                synchronize_session=False)
            s.query(Approval).filter(Approval.kind == "doctor.test").delete(
                synchronize_session=False)
            s.query(MissionEvent).filter(
                MissionEvent.mission_id.in_([mission_done, mission_waiting])).delete(
                synchronize_session=False)
            s.commit()
        except Exception:
            s.rollback()
        finally:
            s.close()

    _purge()

    db = SessionLocal()
    try:
        db.add(OrchestratorTrace(
            id="trace-done-1", mission_id=mission_done, channel="hub",
            state="done", outcome="he terminado la tarea de prueba"))
        db.add(OrchestratorTrace(
            id="trace-waiting-1", mission_id=mission_waiting, channel="hub",
            state="waiting", outcome="pipeline.waiting_confirmation"))
        db.commit()

        db.add(Approval(
            id="approval-doctor-1", kind="doctor.test", title="permiso de prueba",
            action_type="tie_tool_permission", status="pending",
            action_payload={"tool_id": "shell", "action": "run", "mission_id": mission_waiting},
        ))
        db.commit()

        db.add(MissionEvent(mission_id=mission_waiting, stage="tool_call", name="shell",
                            ok=False, detail={"error": "comando no permitido"}))
        db.add(MissionEvent(mission_id=mission_waiting, stage="toolloop", name="stalled",
                            ok=False, detail={"motivo": "sin progreso"}))
        db.commit()
    finally:
        db.close()

    yield {"done": mission_done, "waiting": mission_waiting}
    _purge()


def test_doctor_collect_ve_las_misiones_sembradas(_doctor_seed):
    from scripts.aithera_doctor import collect

    data = collect(hours=24)
    ids = {m["mission_id"] for m in data["missions"]}
    assert _doctor_seed["done"] in ids
    assert _doctor_seed["waiting"] in ids

    waiting = next(m for m in data["missions"] if m["mission_id"] == _doctor_seed["waiting"])
    assert waiting["waiting_with_gate"] is True
    done = next(m for m in data["missions"] if m["mission_id"] == _doctor_seed["done"])
    assert done["waiting_with_gate"] is False
    assert "he terminado" in done["outcome_preview"]


def test_doctor_collect_cuenta_el_atasco_y_el_fallo_de_tool(_doctor_seed):
    from scripts.aithera_doctor import collect

    data = collect(hours=24)
    tel = data["telemetry"]["por_mision"].get(_doctor_seed["waiting"])
    assert tel is not None
    assert tel["loop_problems"].get("stalled") == 1
    assert "shell" in data["telemetry"]["top_tool_failures"]
    assert data["telemetry"]["top_tool_failures"]["shell"]["count"] == 1


def test_doctor_collect_approvals_pending_trae_el_mission_id(_doctor_seed):
    from scripts.aithera_doctor import collect

    data = collect(hours=24)
    fila = next(a for a in data["approvals_pending"] if a["id"] == "approval-doctor-1")
    assert fila["mission_id"] == _doctor_seed["waiting"]
    assert fila["kind"] == "doctor.test"
    assert fila["age_hours"] is not None


def test_doctor_collect_config_health_no_revienta_sin_keys(_doctor_seed):
    from scripts.aithera_doctor import collect

    data = collect(hours=24)
    ch = data["config_health"]
    assert isinstance(ch["ai_providers"], list)
    assert isinstance(ch["search"], dict)
    assert ch["telegram_token_present"] in (True, False)
    assert ch["google_credentials_present"] in (True, False)


def test_doctor_collect_schema_no_revienta():
    from scripts.aithera_doctor import collect

    data = collect(hours=24)
    assert isinstance(data["schema"], dict)


def test_doctor_jamas_escribe(_doctor_seed):
    """READ-ONLY absoluto: ni un INSERT/UPDATE/DELETE de más. Se cuentan filas
    de las 3 tablas que toca ANTES y DESPUÉS de collect()."""
    from app.automation import Approval
    from app.db.database import OrchestratorTrace, SessionLocal
    from app.telemetry.models import MissionEvent
    from scripts.aithera_doctor import collect

    db = SessionLocal()
    try:
        antes = (db.query(OrchestratorTrace).count(),
                 db.query(Approval).count(),
                 db.query(MissionEvent).count())
    finally:
        db.close()

    collect(hours=24)

    db = SessionLocal()
    try:
        despues = (db.query(OrchestratorTrace).count(),
                   db.query(Approval).count(),
                   db.query(MissionEvent).count())
    finally:
        db.close()

    assert antes == despues
