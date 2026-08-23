import ast
from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, inspect
from alembic.migration import MigrationContext
from alembic.operations import Operations

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations" / "versions"
UNSAFE_METHODS = {"alter_column", "drop_column"}


class _BatchAwareVisitor(ast.NodeVisitor):
    def __init__(self):
        self.batch_depth = 0
        self.violations = []

    def visit_With(self, node):
        is_batch = any(self._is_batch_call(item.context_expr) for item in node.items)
        if is_batch:
            self.batch_depth += 1
        self.generic_visit(node)
        if is_batch:
            self.batch_depth -= 1

    @staticmethod
    def _is_batch_call(expr):
        return (
            isinstance(expr, ast.Call)
            and isinstance(expr.func, ast.Attribute)
            and expr.func.attr == "batch_alter_table"
        )

    def visit_Call(self, node):
        if (
            self.batch_depth == 0
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in UNSAFE_METHODS
        ):
            self.violations.append(node.lineno)
        self.generic_visit(node)


def _scan_migration_file(path):
    tree = ast.parse(path.read_text(), filename=str(path))
    results = {"upgrade": [], "downgrade": []}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in results:
            visitor = _BatchAwareVisitor()
            visitor.visit(node)
            results[node.name] = visitor.violations
    return results


def test_upgrade_path_has_no_unbatched_alter_or_drop():
    offenders = []
    for path in sorted(MIGRATIONS_DIR.glob("*.py")):
        violations = _scan_migration_file(path)["upgrade"]
        offenders.extend(f"{path.name}:{lineno}" for lineno in violations)

    assert not offenders, (
        "op.alter_column/op.drop_column found in upgrade() outside batch_alter_table - "
        "this breaks on SQLite (no native ALTER/DROP COLUMN): " + ", ".join(offenders)
    )


@pytest.mark.xfail(
    reason=(
        "Several migrations' downgrade() paths use bare op.drop_column, which breaks "
        "on SQLite. Not exercised in production (only `upgrade head` runs there), but "
        "`alembic downgrade` would fail on SQLite today. Known gap, not fixed here."
    ),
    strict=True,
)
def test_downgrade_path_has_no_unbatched_alter_or_drop():
    offenders = []
    for path in sorted(MIGRATIONS_DIR.glob("*.py")):
        violations = _scan_migration_file(path)["downgrade"]
        offenders.extend(f"{path.name}:{lineno}" for lineno in violations)

    assert not offenders, (
        "op.alter_column/op.drop_column found in downgrade() outside batch_alter_table - "
        "this breaks on SQLite (no native ALTER/DROP COLUMN): " + ", ".join(offenders)
    )


def _make_dummy_table(engine):
    metadata = MetaData()
    Table(
        "dummy_migration_demo",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(50), nullable=True),
    )
    metadata.create_all(engine)


def test_alter_column_without_batch_mode_fails_on_sqlite(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'demo.db'}")
    _make_dummy_table(engine)

    with engine.connect() as conn:
        op = Operations(MigrationContext.configure(conn))
        with pytest.raises(Exception):
            op.alter_column("dummy_migration_demo", "name", nullable=False)


def test_alter_column_with_batch_mode_succeeds_on_sqlite(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'demo.db'}")
    _make_dummy_table(engine)

    with engine.connect() as conn:
        op = Operations(MigrationContext.configure(conn))
        with op.batch_alter_table("dummy_migration_demo") as batch_op:
            batch_op.alter_column("name", nullable=False)
        conn.commit()

    columns = {c["name"]: c["nullable"] for c in inspect(engine).get_columns("dummy_migration_demo")}
    assert columns["name"] is False
