# tests/test_startup_time.py — V0.85 M5 (doc 07 §10, doc 12 §6 y A1)
#
# "arranque < 2 s, import de main sin ChromaDB bloqueante".
#
# Dos pruebas complementarias:
#   1. MemoryManager() (una instancia NUEVA, no el singleton global — que
#      conftest.py ya inicializo para el resto de la suite) no hace I/O en el
#      constructor: prueba directa y barata de la propiedad exacta que arregla
#      doc 12 A1.
#   2. "import app.main" en un proceso Python AISLADO (subprocess) no dispara
#      la carga de chromadb/sentence-transformers — la prueba mas fiel al
#      enunciado literal de doc 12 §6, e inmune a que el resto de la suite ya
#      haya inicializado el singleton compartido.
from pathlib import Path

import time

from app.memory.memory_manager import MemoryManager

BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_memory_manager_constructor_es_instantaneo():
    """[doc 12 A1] Antes de M5 el constructor cargaba chromadb + sentence-
    transformers de forma sincrona (3-5s siempre, minutos la 1a vez que
    descarga el modelo). Ahora debe ser practicamente instantaneo."""
    t0 = time.monotonic()
    mgr = MemoryManager()
    elapsed = time.monotonic() - t0

    assert elapsed < 0.1, f"MemoryManager() tardo {elapsed:.3f}s — deberia ser instantaneo (sin I/O)"
    assert mgr.is_healthy() is False  # nada se ha inicializado todavia
    assert mgr.get_init_error() is None  # no es un fallo, es "aun no arrancado"


def test_import_app_main_no_bloquea_en_memoria():
    """[doc 12 §6, literal] "import de main sin ChromaDB bloqueante" — se
    verifica en un proceso Python aislado (no el de la suite, cuyo conftest.py
    ya inicializo el singleton global a proposito para los demas tests)."""
    import subprocess
    import sys

    code = (
        "import time, os, tempfile\n"
        "os.environ['DATABASE_URL'] = 'sqlite:///' + tempfile.mktemp(suffix='.db')\n"
        "os.environ['AITHERA_CHROMA_PATH'] = tempfile.mkdtemp()\n"
        "t0 = time.monotonic()\n"
        "import app.main\n"
        "elapsed = time.monotonic() - t0\n"
        "from app.memory.memory_manager import memory_manager\n"
        "assert memory_manager.is_healthy() is False, 'memoria inicializada durante el import (regresion doc12 A1)'\n"
        "print(f'IMPORT_TIME={elapsed}')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"

    line = next(l for l in result.stdout.splitlines() if l.startswith("IMPORT_TIME="))
    import_time = float(line.split("=", 1)[1])
    # Presupuesto doc 07 §10 / doc 12 §4: arranque < 2s (target), 4s (maximo).
    assert import_time < 2.0, f"import app.main tardo {import_time:.2f}s (>2s, doc07 §10 M5)"
