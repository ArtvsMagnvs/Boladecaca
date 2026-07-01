# tests/test_smoke.py
#
# Sprint 1 (PLAN_MAESTRO_2026, B2): smoke tests de arranque.
#
# Garantizan que la app monta, que los 11 routers estan registrados y que
# la version esta sincronizada entre main.py y core/config.py.

from app.main import app
from app.core.config import settings


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}


def test_root_version_sincronizada(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Aithera"
    assert data["status"] == "running"
    # Regla CLAUDE.md: version consistente entre main.py y config.py
    assert data["version"] == settings.VERSION
    assert app.version == settings.VERSION


def test_routers_montados():
    """Los 11 prefijos de routers de CLAUDE.md (seccion 6) deben estar montados.

    Se usa app.openapi() en vez de app.routes porque en versiones nuevas
    de FastAPI include_router es lazy (_IncludedRouter)."""
    paths = set(app.openapi().get("paths", {}).keys())

    def mounted(prefix: str) -> bool:
        return any(p.startswith(prefix) for p in paths)

    for prefix in (
        "/api/config",
        "/api/projects",
        "/api/tasks",
        "/api/calendar",
        "/api/ai",
        "/api/chat",
        "/api/agents",
        "/api/email",
        "/api/voice",
        "/api/tools",
        "/api/memory",
    ):
        assert mounted(prefix), f"router no montado: {prefix}"
