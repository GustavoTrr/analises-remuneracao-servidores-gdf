import csv
import os
import sys
from datetime import date
from pathlib import Path

import psycopg

from .common import (
    CURATED_DIR,
    MONEY_COLUMNS,
    SOURCE_COLUMNS,
    competencia_inicial,
    competencia_permitida,
    competence_from_name,
    identity_secret,
    servidor_key,
)


FACT_COLUMNS = tuple(column for column in SOURCE_COLUMNS if column not in ("nome", "cpf"))

STAGING_DDL = f"""
    CREATE TEMP TABLE staging_remuneracao ON COMMIT DROP AS
    SELECT
        ''::text AS servidor_key,
        ''::text AS nome,
        ''::text AS cpf,
        {", ".join(FACT_COLUMNS)}
    FROM fato_remuneracao
    WITH NO DATA
"""

UPSERT_DIM_SQL = """
    INSERT INTO dim_servidor (servidor_key, nome, cpf)
    SELECT DISTINCT ON (servidor_key) servidor_key, nome, cpf
    FROM staging_remuneracao
    ORDER BY servidor_key
    ON CONFLICT (servidor_key) DO NOTHING
"""

INSERT_FACT_SQL = f"""
    INSERT INTO fato_remuneracao (competencia, servidor_id, source_file, {", ".join(FACT_COLUMNS)})
    SELECT %s, dim.id, %s, {", ".join(f"staging.{column}" for column in FACT_COLUMNS)}
    FROM staging_remuneracao AS staging
    JOIN dim_servidor AS dim ON dim.servidor_key = staging.servidor_key
"""


def connect() -> psycopg.Connection:
    # autocommit evita transação implícita: cada bloco transaction() confirma por competência.
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "transparencia"),
        user=os.getenv("POSTGRES_USER", "transparencia"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        autocommit=True,
    )


def database_value(column: str, value: str):
    if value == "":
        return None if column in MONEY_COLUMNS or column in ("mes", "ano") else ""
    if column in ("mes", "ano"):
        return int(value)
    return value


def competencia_carregada(connection: psycopg.Connection, competencia: date) -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM fato_remuneracao WHERE competencia = %s LIMIT 1", (competencia,))
        return cursor.fetchone() is not None


def load_file(connection: psycopg.Connection, path: Path, secret: bytes) -> int:
    year, month = competence_from_name(path.name)
    competencia = date(year, month, 1)
    staging_columns = ", ".join(("servidor_key", "nome", "cpf", *FACT_COLUMNS))
    row_count = 0

    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS staging_remuneracao")
            cursor.execute(STAGING_DDL)
            with cursor.copy(f"COPY staging_remuneracao ({staging_columns}) FROM STDIN") as copy:
                with path.open(encoding="utf-8-sig", newline="") as source:
                    reader = csv.DictReader(source)
                    if tuple(reader.fieldnames or ()) != SOURCE_COLUMNS:
                        raise ValueError(f"schema curado inesperado em {path.name}")
                    for row in reader:
                        values = [servidor_key(row["nome"], row["cpf"], secret), row["nome"], row["cpf"]]
                        values.extend(database_value(column, row[column]) for column in FACT_COLUMNS)
                        copy.write_row(values)
                        row_count += 1
            cursor.execute(UPSERT_DIM_SQL)
            cursor.execute("DELETE FROM fato_remuneracao WHERE competencia = %s", (competencia,))
            cursor.execute(INSERT_FACT_SQL, (competencia, path.name))
    return row_count


def main() -> None:
    force = "--force" in sys.argv[1:]
    secret = identity_secret()
    curated_files = sorted(CURATED_DIR.glob("remuneracao_*.csv"))
    if not curated_files:
        raise RuntimeError(f"nenhum CSV curado encontrado em {CURATED_DIR}")

    with connect() as connection:
        inicio = competencia_inicial()
        for path in curated_files:
            year, month = competence_from_name(path.name)
            if not competencia_permitida(year, month, inicio):
                continue
            competencia = date(year, month, 1)
            if not force and competencia_carregada(connection, competencia):
                print(f"[skip] {path.name} já carregado")
                continue
            count = load_file(connection, path, secret)
            print(f"[loaded] {path.name}: {count} registro(s)")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"[falha] {error}", file=sys.stderr)
        raise SystemExit(1) from None