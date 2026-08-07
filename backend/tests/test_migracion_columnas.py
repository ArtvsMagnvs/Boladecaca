# tests/test_migracion_columnas.py — el desfase modelo/BD, cazado en el arranque
#
# EL FALLO QUE CIERRA (2026-08-02, reportado en vivo por el usuario):
#   ProgrammingError: column "model" of relation "agent_executions" does not exist
#
# La columna se añadió al modelo ORM y NO a una migración. En SQLite no se nota
# (`create_all` la crea), pero el Postgres real del usuario se quedó atrás y
# CUALQUIER endpoint que tocara `agent_executions` devolvía 500 — incluido el
# chat del orquestador y el borrado de un agente (que consulta las ejecuciones
# en curso para cancelarlas). Ese es el motivo de que "eliminar no hiciera
# absolutamente nada": fallaba en el backend.
#
# SEGUNDO ROUND (mismo día): el primer arreglo editó `e2f3a4b5c6d7` para
# añadirle la columna — pero esa revisión YA estaba aplicada en el Postgres
# real (stampeada por ID en `alembic_version`), así que `alembic upgrade head`
# no la reejecutó y el fallo seguía. La columna vive ahora en una migración
# NUEVA y separada (`f7a8b9c0d1e2`), la forma correcta de añadir algo después
# de que la anterior ya se aplicó.
#
# Ya van CUATRO veces que esta clase de desfase rompe la app (documentado en
# CLAUDE.md §27 y en los incidentes de W1/W2c/A1). Los tests de aquí son la
# red que faltaba:
#   1. La migración declara TODAS las columnas nuevas del modelo.
#   2. El arranque detecta el desfase y lo dice en una línea legible.
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.db.database import Base, check_schema_drift, engine as db_engine

_MIGRACIONES = Path(__file__).resolve().parents[1] / "alembic" / "versions"


# ===========================================================================
# 1 — La migración cubre lo que el modelo declara
# ===========================================================================
class TestLaMigracionCubreElModelo:
    def test_la_migracion_de_hoy_declara_la_columna_model(self):
        """Repro EXACTA del fallo: `AgentExecution.model` existe en el ORM, así
        que tiene que estar en SU PROPIA migración — no en `e2f3a4b5c6d7`
        (esa ya estaba aplicada cuando se detectó el hueco; editarla no sirve,
        ver la nota al principio del archivo)."""
        archivo = _MIGRACIONES / "f7a8b9c0d1e2_agent_execution_model.py"
        texto = archivo.read_text(encoding="utf-8")
        assert "agent_executions" in texto, "la migración ni menciona la tabla"
        assert '"model"' in texto, "la columna `model` no está en la migración"
        # Y el CÓDIGO de la revisión ya aplicada no debe tocar esa tabla (el
        # docstring sí puede mencionarla, es la nota histórica del incidente).
        vieja = (_MIGRACIONES / "e2f3a4b5c6d7_agente_autonomia_y_carpetas.py").read_text(encoding="utf-8")
        cuerpo = vieja.split('"""', 2)[-1]  # todo lo que va tras el docstring
        assert "agent_executions" not in cuerpo, (
            "una revisión ya aplicada no debe tocar tablas nuevas en su "
            "código: si hace falta algo más, va en una migración nueva"
        )

    def test_declara_tambien_las_de_agents(self):
        texto = (_MIGRACIONES / "e2f3a4b5c6d7_agente_autonomia_y_carpetas.py").read_text(encoding="utf-8")
        for col in ("autonomy", "extra_paths"):
            assert f'"{col}"' in texto, f"falta {col}"

    def test_la_migracion_nueva_encadena_tras_la_vieja(self):
        """`f7a8b9c0d1e2` tiene que declararse Revises: e2f3a4b5c6d7 — si no,
        Alembic no sabría en qué orden aplicarlas."""
        texto = (_MIGRACIONES / "f7a8b9c0d1e2_agent_execution_model.py").read_text(encoding="utf-8")
        assert 'down_revision: Union[str, None] = "e2f3a4b5c6d7"' in texto

    def test_toda_columna_nueva_del_orm_aparece_en_alguna_migracion(self):
        """Invariante GENERAL, no un caso concreto: cada columna de las tablas
        que este bloque tocó debe poder rastrearse hasta una migración. Sin
        esto, la próxima columna añadida "solo al modelo" volvería a romper el
        Postgres real sin que nada avise."""
        corpus = "\n".join(
            p.read_text(encoding="utf-8") for p in _MIGRACIONES.glob("*.py")
        )
        # Columnas introducidas en las sesiones de este bloque, las que de
        # verdad no existen en el snapshot inicial.
        recientes = {
            "agent_executions": ["progress", "model"],
            "agents": ["autonomy", "extra_paths"],
        }
        huerfanas = []
        for tabla, columnas in recientes.items():
            for col in columnas:
                if not re.search(rf'["\']{re.escape(col)}["\']', corpus):
                    huerfanas.append(f"{tabla}.{col}")
        assert not huerfanas, (
            f"columnas en el ORM sin migración que las cree: {huerfanas}. "
            "En SQLite no se nota; en el Postgres real cada consulta a esa "
            "tabla devolverá 500."
        )


# ===========================================================================
# 1b — El GRAFO de migraciones está sano (V1.1 LC1, 2026-08-07)
# ===========================================================================
class TestElGrafoDeMigraciones:
    """Un incidente distinto del desfase modelo/BD, y de la misma familia:
    Alembic identifica cada revisión por su ID, así que dos archivos con el
    mismo id rompen el grafo entero ("Multiple revisions with id") y `upgrade
    head` deja de funcionar — no una tabla, TODO.

    Pasó de verdad al escribir LC1: se eligieron ids "bonitos" (`d1e2f3a4b5c6`,
    `f1a2b3c4d5e6`) que ya estaban cogidos. Con 36 migraciones ese espacio de
    nombres se agota, y a ojo no se ve. Estos dos tests lo ven."""

    def _revisiones(self):
        revs, downs = {}, {}
        for p in _MIGRACIONES.glob("*.py"):
            texto = p.read_text(encoding="utf-8")
            r = re.search(r'^revision(?::\s*str)?\s*=\s*["\']([0-9a-zA-Z_]+)["\']',
                          texto, re.M)
            d = re.search(r'^down_revision[^=\n]*=\s*(["\']([0-9a-zA-Z_]+)["\']|None)',
                          texto, re.M)
            if not r:
                continue
            revs.setdefault(r.group(1), []).append(p.name)
            downs[r.group(1)] = d.group(2) if (d and d.group(2)) else None
        return revs, downs

    def test_ningun_id_de_revision_esta_repetido(self):
        revs, _ = self._revisiones()
        repetidas = {k: v for k, v in revs.items() if len(v) > 1}
        assert not repetidas, (
            f"ids de revisión duplicados: {repetidas}. Alembic falla al arrancar "
            "con 'Multiple revisions with id' y NINGUNA migración se aplica.")

    def test_hay_exactamente_un_head_y_la_cadena_no_deja_a_nadie_fuera(self):
        """Dos heads = una rama; una migración fuera de la cadena = nunca se
        aplica. Las dos cosas se ven igual desde fuera: 'no pasó nada'."""
        revs, downs = self._revisiones()
        hijos = {v for v in downs.values() if v}
        heads = [k for k in revs if k not in hijos]
        assert len(heads) == 1, f"se esperaba UN head, hay {len(heads)}: {heads}"

        h, cadena, vistos = heads[0], 0, set()
        while h and h not in vistos:
            vistos.add(h)
            cadena += 1
            h = downs.get(h)
        assert cadena == len(revs), (
            f"la cadena recorre {cadena} de {len(revs)} migraciones: hay alguna "
            f"colgando fuera del camino desde el head.")


# ===========================================================================
# 2 — El arranque DETECTA el desfase (para que el síntoma sea legible)
# ===========================================================================
class TestDeteccionDeDesfase:
    def test_sin_desfase_no_reporta_nada(self):
        """Con la BD de tests al día (`create_all`), no debe inventarse
        problemas: un detector que grita siempre se ignora siempre."""
        Base.metadata.create_all(bind=db_engine)
        assert check_schema_drift() == {}

    def test_una_columna_ausente_se_detecta_y_se_nombra(self, monkeypatch):
        """La repro del incidente: la BD no tiene una columna que el ORM sí
        declara. Se simula recortando lo que ve el inspector."""
        from sqlalchemy import inspect as sa_inspect

        import app.db.database as dbmod

        real = sa_inspect(db_engine)

        class InspectorRecortado:
            def get_table_names(self):
                return real.get_table_names()

            def get_columns(self, tabla):
                cols = real.get_columns(tabla)
                if tabla == "agent_executions":
                    return [c for c in cols if c["name"] != "model"]
                return cols

        monkeypatch.setattr(dbmod, "inspect", lambda _e: InspectorRecortado(),
                            raising=False)
        # `check_schema_drift` importa `inspect` dentro de la función; se
        # sustituye en el módulo de sqlalchemy que resuelve en ese momento.
        import sqlalchemy

        monkeypatch.setattr(sqlalchemy, "inspect", lambda _e: InspectorRecortado())

        desfase = check_schema_drift()
        assert "agent_executions" in desfase
        assert "model" in desfase["agent_executions"]

    def test_nunca_lanza_aunque_la_introspeccion_falle(self, monkeypatch):
        """Diagnóstico best-effort: un detector que tumba el arranque sería
        peor que el problema que detecta."""
        import sqlalchemy

        def explota(_e):
            raise RuntimeError("BD inaccesible")

        monkeypatch.setattr(sqlalchemy, "inspect", explota)
        assert check_schema_drift() == {}
