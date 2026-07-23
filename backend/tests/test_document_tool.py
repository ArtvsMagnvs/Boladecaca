# tests/test_document_tool.py — DocumentTool (#218)
#
# Documentos de oficina REALES: leer PDF, leer/escribir DOCX y XLSX. Todo el
# ciclo se ejercita de verdad (escribir un archivo y volver a leerlo, extraer
# texto de un PDF hecho a mano) — sin red, sin mocks de las librerias: pypdf/
# python-docx/openpyxl son deterministas y baratas, se prueban tal cual.
#
# Aislamiento: cada test escribe en un tmp_path propio y le pasa la RUTA
# ABSOLUTA a la tool (que la valida contra HOME). tmp_path de pytest en Windows
# vive bajo el perfil del usuario, asi que pasa la whitelist de FilesystemTool.
from __future__ import annotations

import pytest

from app.tools.document_tool import DocumentTool, _parse_page_range
from app.tools.tool_manager import tool_manager


# PDF minimo VALIDO con texto extraible (una pagina, Helvetica). pypdf recupera
# el texto del content stream aunque el xref sea imperfecto (lo comprobamos en
# vivo). Evita depender de un binario de terceros o de un fichero del usuario.
_MINIMAL_PDF = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 58>>stream
BT /F1 24 Tf 72 700 Td (Hola PDF Aithera) Tj ET
endstream endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f
trailer<</Root 1 0 R/Size 6>>
startxref
0
%%EOF"""


@pytest.fixture
def tool():
    return DocumentTool()


def test_document_tool_registrada():
    ids = {t["tool_id"] for t in tool_manager.list_tools()}
    assert "document" in ids


# ---------------------------------------------------------------------------
# XLSX: escribir → leer
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_xlsx_ciclo_completo(tool, tmp_path):
    dest = tmp_path / "ventas.xlsx"
    r = await tool.execute("write_xlsx", {
        "path": str(dest), "header": True,
        "sheets": [
            {"name": "Ventas", "rows": [["Mes", "Total"], ["Enero", 100], ["Febrero", 200]]},
            {"name": "Notas", "rows": [["a", "b"]]},
        ],
    })
    assert r["success"], r["error"]
    assert dest.exists() and r["result"]["sheets"] == 2

    r = await tool.execute("read_xlsx", {"path": str(dest)})
    assert r["success"]
    assert r["result"]["sheet_names"] == ["Ventas", "Notas"]
    ventas = r["result"]["sheets"][0]
    assert ventas["name"] == "Ventas"
    assert ventas["rows"] == [["Mes", "Total"], ["Enero", 100], ["Febrero", 200]]


@pytest.mark.anyio
async def test_xlsx_una_hoja_simple_con_rows(tool, tmp_path):
    dest = tmp_path / "simple.xlsx"
    r = await tool.execute("write_xlsx", {"path": str(dest), "rows": [["x", 1], ["y", 2]]})
    assert r["success"] and r["result"]["sheets"] == 1
    r = await tool.execute("read_xlsx", {"path": str(dest), "sheet": "Hoja1"})
    assert r["success"] and r["result"]["sheets"][0]["rows"] == [["x", 1], ["y", 2]]


@pytest.mark.anyio
async def test_read_xlsx_hoja_inexistente_error(tool, tmp_path):
    dest = tmp_path / "s.xlsx"
    await tool.execute("write_xlsx", {"path": str(dest), "rows": [["a"]]})
    r = await tool.execute("read_xlsx", {"path": str(dest), "sheet": "NoExiste"})
    assert not r["success"] and "no existe" in r["error"].lower()


@pytest.mark.anyio
async def test_write_xlsx_sin_contenido_error(tool, tmp_path):
    r = await tool.execute("write_xlsx", {"path": str(tmp_path / "x.xlsx")})
    assert not r["success"] and "falta contenido" in r["error"]


# ---------------------------------------------------------------------------
# DOCX: escribir → leer (bloques y contenido simple)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_docx_ciclo_completo_con_bloques(tool, tmp_path):
    dest = tmp_path / "informe.docx"
    r = await tool.execute("write_docx", {
        "path": str(dest), "title": "Informe",
        "blocks": [
            {"type": "heading", "text": "Resumen", "level": 1},
            {"type": "paragraph", "text": "Parrafo en negrita", "bold": True},
            {"type": "table", "header": True, "rows": [["Col1", "Col2"], ["x", "y"]]},
        ],
    })
    assert r["success"], r["error"]
    assert dest.exists()

    r = await tool.execute("read_docx", {"path": str(dest)})
    assert r["success"]
    res = r["result"]
    assert res["paragraph_count"] == 3   # titulo + heading + paragraph
    assert "Informe" in res["text"] and "Resumen" in res["text"]
    assert res["table_count"] == 1
    assert res["tables"][0] == [["Col1", "Col2"], ["x", "y"]]


@pytest.mark.anyio
async def test_docx_contenido_simple_por_parrafos(tool, tmp_path):
    dest = tmp_path / "nota.docx"
    r = await tool.execute("write_docx", {
        "path": str(dest), "content": "Primer parrafo.\n\nSegundo parrafo.",
    })
    assert r["success"]
    r = await tool.execute("read_docx", {"path": str(dest)})
    assert r["success"]
    assert r["result"]["paragraphs"] == ["Primer parrafo.", "Segundo parrafo."]


@pytest.mark.anyio
async def test_write_docx_sin_contenido_error(tool, tmp_path):
    r = await tool.execute("write_docx", {"path": str(tmp_path / "vacio.docx")})
    assert not r["success"] and "falta contenido" in r["error"]


# ---------------------------------------------------------------------------
# PDF: lectura de texto real + aviso honesto
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_read_pdf_extrae_texto(tool, tmp_path):
    dest = tmp_path / "doc.pdf"
    dest.write_bytes(_MINIMAL_PDF)
    r = await tool.execute("read_pdf", {"path": str(dest)})
    assert r["success"], r["error"]
    assert r["result"]["total_pages"] == 1
    assert "Hola PDF Aithera" in r["result"]["text"]
    assert r["result"]["note"] is None   # SI habia texto → sin aviso


@pytest.mark.anyio
async def test_read_pdf_sin_texto_avisa_honestamente(tool, tmp_path):
    # PDF valido de una pagina con content stream SIN texto (simula un
    # escaneado/solo-imagen) → el aviso debe sugerir OCR.
    empty_pdf = (b"%PDF-1.4\n"
                 b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                 b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
                 b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj\n"
                 b"4 0 obj<</Length 3>>stream\n   \nendstream endobj\n"
                 b"trailer<</Root 1 0 R/Size 5>>\nstartxref\n0\n%%EOF")
    dest = tmp_path / "escaneado.pdf"
    dest.write_bytes(empty_pdf)
    r = await tool.execute("read_pdf", {"path": str(dest)})
    assert r["success"]
    assert not r["result"]["text"].strip()
    assert r["result"]["note"] and "OCR" in r["result"]["note"]


# ---------------------------------------------------------------------------
# Seguridad + errores comunes
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_path_fuera_de_home_rechazado(tool):
    r = await tool.execute("read_pdf", {"path": "C:\\Windows\\win.ini"})
    assert not r["success"] and "zonas permitidas" in r["error"]


@pytest.mark.anyio
async def test_read_de_archivo_inexistente(tool, tmp_path):
    r = await tool.execute("read_docx", {"path": str(tmp_path / "nada.docx")})
    assert not r["success"] and "no existe" in r["error"]


@pytest.mark.anyio
async def test_accion_desconocida(tool):
    r = await tool.execute("write_pdf", {"path": "x.pdf"})
    assert not r["success"] and "Accion desconocida" in r["error"]


@pytest.mark.anyio
async def test_escritura_pide_confirmacion_lectura_no(tool):
    """Contrato de seguridad: escribir crea un archivo → confirmacion; leer no.
    Es lo que el toolloop usa para decidir si pasa por el ApprovalGate."""
    by_id = {a["id"]: a for a in tool.list_actions()}
    assert by_id["write_docx"]["requires_confirmation"] is True
    assert by_id["write_xlsx"]["requires_confirmation"] is True
    assert by_id["read_pdf"]["requires_confirmation"] is False
    assert by_id["read_docx"]["requires_confirmation"] is False
    assert by_id["read_xlsx"]["requires_confirmation"] is False


# ---------------------------------------------------------------------------
# Helper puro
# ---------------------------------------------------------------------------
def test_parse_page_range():
    assert _parse_page_range("1-3", 10) == [0, 1, 2]
    assert _parse_page_range("3", 10) == [2]
    assert _parse_page_range(None, 3) == [0, 1, 2]
    assert _parse_page_range("5-2", 10) == []        # invertido → vacio
    assert _parse_page_range("abc", 4) == [0, 1, 2, 3]  # basura → todo
    assert _parse_page_range("20-30", 5) == []       # fuera de rango → vacio
    assert _parse_page_range("2-100", 5) == [1, 2, 3, 4]  # recorta al total


# ---------------------------------------------------------------------------
# Permiso: document.write_* cae bajo filesystem.write
# ---------------------------------------------------------------------------
def test_document_write_bajo_filesystem_write():
    from app.automation.permissions import permission_for_tool_action
    assert permission_for_tool_action("document", "write_docx") == "filesystem.write"
    assert permission_for_tool_action("document", "write_xlsx") == "filesystem.write"
