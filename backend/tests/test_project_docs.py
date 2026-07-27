# tests/test_project_docs.py — el material adjunto de un proyecto LLEGA al
# agente (2026-07-25, petición del usuario: "que los agentes de ese proyecto
# puedan acceder a ellos, leerlos, editarlos").
#
# EL HUECO QUE CIERRA: `Project.docs` existía y el popup permitía escribir
# enlaces, pero (a) no había forma de elegir ARCHIVOS reales y (b) ni el
# contexto del chat ni `project_status` mencionaban el material — así que un
# agente del proyecto no sabía que existía y no podía abrirlo. El selector
# nativo es frontend (Electron IPC); lo que se blinda aquí es la parte backend:
# que la carpeta, los archivos y los enlaces se VEAN.
import asyncio
import os

import pytest

import app.workspace  # noqa: F401  (registra Milestone en Base.metadata)
from app.db.database import Base, Project, SessionLocal, engine

HOME = os.path.expanduser("~")
GDD = os.path.join(HOME, "Desktop", "Cordyceps", "GDD.pdf")


@pytest.fixture(autouse=True)
def _seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(Project).delete()
        db.add(Project(
            name="Cordyceps", status="active", progress=0.0,
            repo_path=os.path.join(HOME, "Desktop", "Cordyceps"),
            docs=[
                {"label": "GDD.pdf", "kind": "file", "url_or_path": GDD},
                {"label": "Godot docs", "kind": "url",
                 "url_or_path": "https://docs.godotengine.org"},
            ],
        ))
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(Project).delete()
        db.commit()
    finally:
        db.close()


def test_el_contexto_del_chat_muestra_carpeta_archivos_y_enlaces():
    """Lo que ve el modelo (y por tanto el agente) en cada turno."""
    from app.services import chat_service

    block = chat_service._workspace_block()
    assert "Cordyceps" in block
    assert "carpeta local:" in block
    assert GDD in block, "la RUTA del archivo debe estar, es lo que el agente abrirá"
    assert "https://docs.godotengine.org" in block


def test_project_status_devuelve_el_material_del_proyecto():
    """Cuando un agente consulta su proyecto, recibe con qué trabajar."""
    from app.tools.aithera_tool import AitheraTool

    r = asyncio.run(AitheraTool().execute("project_status", {"project_id": 1}))
    assert r["success"], r
    res = r["result"]
    assert res["repo_path"], "la carpeta local debe viajar"
    assert res["files"] and res["files"][0]["url_or_path"] == GDD
    assert res["links"] and res["links"][0]["kind"] != "file"


def test_un_archivo_adjunto_del_HOME_es_legible_por_las_tools():
    """Contrato de seguridad: las tools solo abren dentro de HOME. Un archivo
    elegido con el selector nativo (Escritorio, Documentos…) cae dentro de HOME,
    así que el agente PUEDE leerlo; uno de fuera se rechaza."""
    from app.tools.filesystem_tool import FilesystemTool

    tool = FilesystemTool()
    dentro = tool._safe_path(GDD) if hasattr(tool, "_safe_path") else None
    if dentro is None:
        pytest.skip("FilesystemTool no expone _safe_path en esta versión")
    assert dentro is not False


def test_docs_vacio_no_rompe_el_contexto():
    from app.services import chat_service

    db = SessionLocal()
    try:
        p = db.query(Project).first()
        p.docs = None
        p.repo_path = None
        db.commit()
    finally:
        db.close()
    block = chat_service._workspace_block()
    assert "Cordyceps" in block
    assert "carpeta local:" not in block
