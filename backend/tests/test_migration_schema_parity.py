import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

POSTGRES_TEST_URL = os.environ.get("POSTGRES_TEST_URL")

pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="Set POSTGRES_TEST_URL to a fresh, empty Postgres DB to run the migration parity check",
)


def _run_migrations(database_url):
    os.environ["DATABASE_URL"] = database_url
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    command.upgrade(cfg, "head")


def _describe_schema(engine):
    insp = inspect(engine)
    schema = {}
    for table in sorted(insp.get_table_names()):
        if table == "alembic_version":
            continue
        schema[table] = {
            "columns": {c["name"]: c["nullable"] for c in insp.get_columns(table)},
            "primary_key": sorted(insp.get_pk_constraint(table)["constrained_columns"]),
            "foreign_keys": sorted(
                (tuple(sorted(fk["constrained_columns"])), fk["referred_table"])
                for fk in insp.get_foreign_keys(table)
            ),
            "unique_constraints": sorted(
                tuple(sorted(u["column_names"])) for u in insp.get_unique_constraints(table)
            ),
        }
    return schema


def test_migration_chain_produces_equivalent_schema_on_sqlite_and_postgres(tmp_path):
    sqlite_url = f"sqlite:///{tmp_path / 'parity_test.db'}"
    _run_migrations(sqlite_url)
    sqlite_schema = _describe_schema(create_engine(sqlite_url))

    _run_migrations(POSTGRES_TEST_URL)
    postgres_schema = _describe_schema(create_engine(POSTGRES_TEST_URL))

    sqlite_tables, postgres_tables = set(sqlite_schema), set(postgres_schema)
    assert sqlite_tables == postgres_tables, (
        f"Table sets differ. SQLite only: {sqlite_tables - postgres_tables}, "
        f"Postgres only: {postgres_tables - sqlite_tables}"
    )

    mismatches = [
        f"{table}:\n  sqlite=  {sqlite_schema[table]}\n  postgres={postgres_schema[table]}"
        for table in sqlite_schema
        if sqlite_schema[table] != postgres_schema[table]
    ]
    assert not mismatches, "Schema mismatch between SQLite and Postgres after migration:\n" + "\n".join(mismatches)
