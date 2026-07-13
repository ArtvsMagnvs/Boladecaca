# tests/conftest.py
#
# Sprint 1 (PLAN_MAESTRO_2026, B2): fixtures compartidas para la suite.
#
# CRITICO: DATABASE_URL se fija a un SQLite temporal ANTES de importar
# app.main, porque app/db/database.py crea el engine al importarse.
# Asi los tests jamas tocan la BD real (%APPDATA%/Aithera/aithera.db
# o PostgreSQL).

import os
import tempfile

# --- Entorno de test: debe ejecutarse antes de cualquier import de app.* ---
_TEST_DB_DIR = tempfile.mkdtemp(prefix="aithera_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_TEST_DB_DIR, 'test_aithera.db')}"
# V0.85 (MOS M1): aisla ChromaDB a un dir temporal para que los tests de memoria
# NO toquen la BD vectorial real del usuario (%APPDATA%/Aithera/chroma). El
# modelo de sentence-transformers sigue cacheado aparte, no se re-descarga.
os.environ["AITHERA_CHROMA_PATH"] = os.path.join(_TEST_DB_DIR, "chroma")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db.database import Base, engine, SessionLocal  # noqa: E402
from app.memory.memory_manager import memory_manager  # noqa: E402

# V0.85 (MOS M5, doc 12 A1): desde M5, MemoryManager.__init__() es instantaneo
# y NO inicializa chromadb — is_healthy() es False hasta que algo llama a
# initialize_async()/initialize_sync(). Varios tests de memoria usan
# `pytestmark = pytest.mark.skipif(not memory_router.healthy, ...)` a nivel de
# MODULO, que pytest evalua en COLLECTION TIME (al importar el fichero de test),
# antes de que corra NINGUN fixture (incluido `client`, que dispara el lifespan
# en background). Sin esto, esos skipif verian is_healthy()==False siempre y
# se saltarian TODOS esos tests. Se inicializa aqui, sincrono, a nivel de
# modulo de conftest.py — que pytest carga antes de coleccionar ningun test.
memory_manager.initialize_sync()


@pytest.fixture(scope="session")
def client():
    """TestClient con lifespan (crea las tablas via Base.metadata.create_all).

    El memory system degradara gracefully si ChromaDB no esta disponible
    en el entorno de test — eso es comportamiento esperado y no un fallo.
    Ya esta inicializado (sincrono, arriba) antes de que este fixture corra;
    el lifespan.initialize_async() del propio TestClient sera un no-op.
    """
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture()
def db_session():
    """Sesion de BD de test con limpieza garantizada."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(autouse=True)
def _clean_email_tables():
    """Limpia las tablas del dominio email entre tests (BD temporal)."""
    yield
    from app.db.models import EmailActivityLog, MeetingProposal, EmailAutoReplyRule, EmailTriage, CalendarEvent
    session = SessionLocal()
    try:
        for model in (EmailActivityLog, MeetingProposal, EmailAutoReplyRule, EmailTriage, CalendarEvent):
            try:
                session.query(model).delete()
            except Exception:
                session.rollback()
        session.commit()
    finally:
        session.close()


@pytest.fixture
def anyio_backend():
    """Backend para tests async con @pytest.mark.anyio (solo asyncio)."""
    return "asyncio"
