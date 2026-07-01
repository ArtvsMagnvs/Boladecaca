"""
Script de migracion SQLite -> PostgreSQL.

Se ejecuta UNA SOLA VEZ para copiar los datos del archivo SQLite
historico (%APPDATA%/Aithera/aithera.db o backend/aithera.db) a la
base de datos PostgreSQL definida en DATABASE_URL (.env).

Uso:
    cd backend
    python scripts/migrate_sqlite_to_postgres.py
    python scripts/migrate_sqlite_to_postgres.py --dry-run   # solo contar, no escribir

V0.4 (Fase 1b PostgreSQL Migration):
- Esquema NO se migra: ya esta definido en app.db.database.Base.metadata
  (idempotente, ejecuta create_all al inicio de la migracion).
- Datos se copian en orden: primero las tablas sin FK, luego las que
  dependen. Si una tabla no existe en SQLite (porque nunca se uso), se
  salta sin error.
- ON CONFLICT DO NOTHING: si la fila ya existe (ej. si ejecutas el
  script dos veces), no falla. Pero los IDs seguiran siendo los de
  SQLite, lo cual es deseable: las APIs siguen funcionando.
- Tras una migracion exitosa, el SQLite original SE CONSERVA como
  backup. El usuario puede borrarlo a mano si quiere.

Requisitos:
- psycopg2-binary instalado (pip install psycopg2-binary).
- DATABASE_URL apuntando a PostgreSQL.
- Permisos de lectura sobre el archivo SQLite origen.
- El usuario de BD destino debe tener CREATE/INSERT sobre el esquema.
"""
import argparse
import os
import sqlite3
import sys
from pathlib import Path

# Anadimos el directorio padre (backend/) al path para poder importar
# app.* sin necesidad de instalar nada.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

# Carga .env desde el directorio backend/
load_dotenv(BACKEND_DIR / ".env")

from sqlalchemy import create_engine, inspect, text  # noqa: E402


SQLITE_CANDIDATES = [
    Path(os.environ.get("APPDATA", ".")) / "Aithera" / "aithera.db",  # %APPDATA%/Aithera
    BACKEND_DIR / "aithera.db",                                        # backend/aithera.db
]


def find_sqlite_db() -> Path:
    """Devuelve la primera ruta SQLite que exista de entre las candidatas."""
    for cand in SQLITE_CANDIDATES:
        if cand.exists():
            return cand
    raise FileNotFoundError(
        "No se encontro ninguna base de datos SQLite. Esperaba alguna de:\n"
        + "\n".join(f"  - {c}" for c in SQLITE_CANDIDATES)
    )


# Orden importa: padres antes que hijos para no violar FKs.
# Las tablas de Aithera (config, projects, etc.) no tienen FKs fuertes
# entre si, pero respetamos un orden logico para que los AUTOINCREMENT
# no se desfasen al copiar.
TABLES_IN_ORDER = [
    "config",
    "ai_provider_configs",
    "projects",
    "tasks",
    "calendar_events",
    "agents",
    "conversations",
    "chat_messages",
]


def parse_args():
    p = argparse.ArgumentParser(description="Migrar datos SQLite -> PostgreSQL.")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo cuenta registros por tabla, no escribe nada en PostgreSQL.",
    )
    p.add_argument(
        "--sqlite-path",
        type=str,
        default=None,
        help="Ruta explicita al archivo SQLite. Si no se da, busca %APPDATA%/Aithera primero.",
    )
    return p.parse_args()


def discover_sqlite_tables(sqlite_path: Path) -> list[str]:
    """Devuelve las tablas que existen realmente en SQLite, en el orden declarado."""
    conn = sqlite3.connect(str(sqlite_path))
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    actual = {r[0] for r in cur.fetchall()}
    conn.close()
    # Filtramos TABLES_IN_ORDER por las que existan realmente.
    return [t for t in TABLES_IN_ORDER if t in actual]


def get_boolean_columns(pg_engine, table: str) -> set[str]:
    """Devuelve los nombres de columnas de tipo BOOLEAN en la tabla destino."""
    insp = inspect(pg_engine)
    try:
        cols = insp.get_columns(table)
    except Exception:
        return set()
    return {c["name"] for c in cols if str(c["type"]).lower() == "boolean"}


def get_text_columns(pg_engine, table: str) -> set[str]:
    """Devuelve los nombres de columnas TEXT/VARCHAR de la tabla destino.
    SQLite es dynamic-typing: a veces almacena enteros (e.g. timestamps
    formateados) en columnas que en el modelo son TEXT; aqui normalizamos
    cualquier valor que no sea str/None a str para evitar el error
    'expected string but got integer' de psycopg2 al copiar a PG."""
    insp = inspect(pg_engine)
    try:
        cols = insp.get_columns(table)
    except Exception:
        return set()
    text_types = {"text", "varchar", "character varying", "char", "string"}
    return {c["name"] for c in cols if str(c["type"]).lower() in text_types}


def _cast_row(row_dict: dict, bool_cols: set[str], text_cols: set[str]) -> dict:
    """Adapta los valores de una fila SQLite al esquema PostgreSQL destino."""
    out = {}
    for k, v in row_dict.items():
        if k in bool_cols and v is not None:
            # SQLite -> boolean: 0/1, 't'/'f', 'true'/'false', etc.
            if isinstance(v, bool):
                out[k] = v
            elif isinstance(v, (int, float)):
                out[k] = bool(v)
            elif isinstance(v, str):
                out[k] = v.strip().lower() in ("1", "t", "true", "y", "yes")
            else:
                out[k] = bool(v)
        elif k in text_cols and v is not None and not isinstance(v, (str, bytes)):
            # Asegurar que cualquier entero/fecha/etc que SQLite guardo en una
            # columna TEXT se convierta a str para que psycopg2 no proteste.
            out[k] = str(v)
        else:
            out[k] = v
    return out


def migrate_table(sqlite_path: Path, pg_engine, table: str, dry_run: bool) -> int:
    """Copia los datos de `table` desde SQLite a PostgreSQL. Devuelve el numero de filas."""
    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row
    cursor = sqlite_conn.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    columns = [d[0] for d in cursor.description] if cursor.description else []

    if dry_run:
        sqlite_conn.close()
        return len(rows)

    if not rows:
        sqlite_conn.close()
        return 0

    # Detectar columnas que requieren conversion de tipo (boolean, text).
    bool_cols = get_boolean_columns(pg_engine, table)
    text_cols = get_text_columns(pg_engine, table)

    placeholders = ", ".join(f":{c}" for c in columns)
    col_list = ", ".join(f'"{c}"' for c in columns)
    insert_sql = (
        f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) '
        f"ON CONFLICT DO NOTHING"
    )

    pg_conn = pg_engine.connect()
    try:
        count = 0
        for row in rows:
            raw = {c: row[c] for c in columns}
            payload = _cast_row(raw, bool_cols, text_cols)
            pg_conn.execute(text(insert_sql), payload)
            count += 1
        pg_conn.commit()
    finally:
        pg_conn.close()
        sqlite_conn.close()
    return count


def sync_sequences(pg_engine, tables: list[str]) -> int:
    """Sincroniza las secuencias PostgreSQL (autoincrement) de cada tabla con
    el MAX(id) de los datos recien migrados.

    Sin esto, INSERTs nuevos fallarian con 'duplicate key value violates
    unique constraint' porque la secuencia seguiria en 1 y los IDs migrados
    ya usan 1, 2, 3, etc.

    Devuelve el numero de secuencias sincronizadas.
    """
    synced = 0
    pg_conn = pg_engine.connect()
    try:
        for table in tables:
            # Comprobamos que la tabla tiene una PK integer (sequence-backed).
            insp = inspect(pg_engine)
            pk = insp.get_pk_constraint(table)
            pk_cols = pk.get("constrained_columns") or []
            if not pk_cols or pk_cols[0] != "id":
                continue
            # Obtenemos MAX(id) de la tabla migrada.
            result = pg_conn.execute(text(f'SELECT MAX(id) FROM "{table}"')).fetchone()
            max_id = result[0] if result else None
            if not max_id or max_id < 1:
                continue
            # La secuencia por convencion se llama <tabla>_id_seq.
            seq_name = f"{table}_id_seq"
            # Ajustamos la secuencia a max_id (el proximo NEXTVAL sera max_id+1).
            pg_conn.execute(
                text(f"SELECT setval('{seq_name}', :max_id)"),
                {"max_id": max_id},
            )
            synced += 1
        pg_conn.commit()
    finally:
        pg_conn.close()
    return synced


def main():
    args = parse_args()

    print("=" * 70)
    print(" MIGRACION SQLite -> PostgreSQL  (Aithera V0.4)")
    print("=" * 70)
    print()

    # 1) Validar que DATABASE_URL apunta a PostgreSQL
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print("[ERROR] DATABASE_URL no esta definida en .env")
        sys.exit(1)
    if not db_url.startswith("postgresql"):
        print(f"[ERROR] DATABASE_URL no apunta a PostgreSQL: {db_url}")
        sys.exit(1)

    # 2) Encontrar SQLite origen
    if args.sqlite_path:
        sqlite_path = Path(args.sqlite_path)
        if not sqlite_path.exists():
            print(f"[ERROR] SQLite no encontrado en: {sqlite_path}")
            sys.exit(1)
    else:
        try:
            sqlite_path = find_sqlite_db()
        except FileNotFoundError as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

    print(f"[INFO] Fuente:  {sqlite_path}")
    print(f"[INFO] Destino: {db_url}")
    print(f"[INFO] Modo:    {'DRY-RUN (no escribe)' if args.dry_run else 'ESCRITURA REAL'}")
    print()

    # 3) Crear el esquema en PostgreSQL (idempotente: create_all solo crea
    #    tablas/columnas que faltan, nunca borra datos existentes).
    print("[STEP 1] Creando esquema en PostgreSQL (Base.metadata.create_all)...")
    pg_engine = create_engine(db_url)
    from app.db.database import Base
    Base.metadata.create_all(bind=pg_engine)
    print("   OK")
    print()

    # 4) Descubrir tablas presentes en SQLite y migrar una a una
    sqlite_tables = discover_sqlite_tables(sqlite_path)
    if not sqlite_tables:
        print("[INFO] No hay tablas para migrar.")
        sys.exit(0)
    print(f"[STEP 2] Tablas detectadas en SQLite ({len(sqlite_tables)}): {', '.join(sqlite_tables)}")
    print()

    print("[STEP 3] Copia de datos (en orden):")
    grand_total = 0
    for table in sqlite_tables:
        try:
            count = migrate_table(sqlite_path, pg_engine, table, dry_run=args.dry_run)
            status = "(vacia)" if count == 0 else f"{count} filas"
            print(f"   - {table:<22} {status}")
            grand_total += count
        except Exception as e:
            print(f"   - {table:<22} ERROR: {type(e).__name__}: {e}")
    print()

    # 5) Sincronizar secuencias autoincrement con MAX(id) real
    if not args.dry_run:
        print("[STEP 4] Sincronizando secuencias autoincrement (setval)...")
        synced = sync_sequences(pg_engine, sqlite_tables)
        print(f"   {synced} secuencias ajustadas al MAX(id) migrado")
        print()

    print("=" * 70)
    if args.dry_run:
        print(f" DRY-RUN completado: {grand_total} filas se migrarian")
        print(" (no se escribio nada en PostgreSQL)")
    else:
        print(f" {grand_total} filas migradas a PostgreSQL")
        print(f" El archivo SQLite original se conserva como backup en:")
        print(f"   {sqlite_path}")
        print()
        print(" Siguiente paso: arrancar el backend con la nueva DATABASE_URL")
        print(" y verificar con: GET /api/projects/ , /api/tasks/ , /api/ai/status")
    print("=" * 70)


if __name__ == "__main__":
    main()
