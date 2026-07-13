# tests/test_chromadb_search_perf.py — V0.85 M5 (doc 07 §10, doc 12 §4/§6)
#
# "búsqueda < 200 ms con 10k items" (target 150ms / máximo 500ms en doc 12 §4
# para 'search top-10'; 200ms es el umbral explícito del propio nombre de este
# test en doc 12 §6 — se usa ese literal).
#
# Los 10k documentos del corpus se insertan con EMBEDDINGS PRE-CALCULADOS
# (vectores sintéticos, sin pasar por el modelo) para que preparar el test sea
# rápido — lo que se mide es el coste real del que depende `context()`/`search()`
# en producción: la búsqueda vectorial sobre 10k items, NO el coste de calcular
# 10k embeddings (eso ya lo paga la ingesta en background, fuera del critical
# path). La QUERY sí usa el embedding function real (igual que en producción).
import random
import time

import pytest

from app.memory.memory_manager import memory_manager

pytestmark = pytest.mark.skipif(
    not memory_manager.is_healthy(), reason="ChromaDB no disponible en el entorno de test"
)

N_ITEMS = 10_000
SEARCH_BUDGET_S = 0.2  # doc 12 §6: "10k items < 200 ms"
_COLLECTION_NAME = "perf_test_10k_search"


@pytest.fixture(scope="module")
def seeded_collection():
    """Coleccion propia (no una de las del MOS) con 10k items de vectores
    sinteticos. Se limpia al terminar el modulo."""
    col = memory_manager.get_or_create_collection(_COLLECTION_NAME)
    if col is None:
        pytest.skip("no se pudo crear la coleccion de perf")

    # Dimension real del modelo activo (all-MiniLM-L6-v2 = 384), leida del
    # propio embedding function en vez de hardcodearla — a prueba de cambio
    # de modelo.
    dim = len(memory_manager._ef(["sonda de dimension"])[0])

    rng = random.Random(42)
    batch = 1000
    for start in range(0, N_ITEMS, batch):
        n = min(batch, N_ITEMS - start)
        ids = [f"perf_{start + i}" for i in range(n)]
        docs = [f"documento sintetico numero {start + i} sobre temas variados" for i in range(n)]
        embeddings = [[rng.uniform(-1, 1) for _ in range(dim)] for _ in range(n)]
        metadatas = [{"date": "2026-07-13", "source": "perf_test"} for _ in range(n)]
        col.add(ids=ids, documents=docs, embeddings=embeddings, metadatas=metadatas)

    assert col.count() >= N_ITEMS
    yield col

    try:
        memory_manager._client.delete_collection(_COLLECTION_NAME)
    except Exception:
        pass


def test_busqueda_bajo_200ms_con_10k_items(seeded_collection):
    """La query SI usa el embedding function real (mismo camino que
    LocalMemoryStore.search() en produccion) — solo el CORPUS es sintetico."""
    t0 = time.monotonic()
    result = seeded_collection.query(query_texts=["documento sobre temas variados"], n_results=10)
    elapsed = time.monotonic() - t0

    assert len(result.get("ids", [[]])[0]) == 10
    assert elapsed < SEARCH_BUDGET_S, f"busqueda tardo {elapsed * 1000:.1f}ms (>200ms, doc12 §6) con {N_ITEMS} items"


def test_busqueda_repetida_se_mantiene_bajo_presupuesto(seeded_collection):
    """5 queries seguidas (cache/estado interno de Chroma no debe degradar)."""
    times = []
    for i in range(5):
        t0 = time.monotonic()
        seeded_collection.query(query_texts=[f"consulta numero {i}"], n_results=10)
        times.append(time.monotonic() - t0)

    worst = max(times)
    assert worst < SEARCH_BUDGET_S, f"peor caso {worst * 1000:.1f}ms (>200ms) en 5 queries sobre {N_ITEMS} items"
