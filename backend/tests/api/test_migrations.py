from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext

from app.store import models  # noqa: F401
from app.store.db import Base
from tests.api.conftest import migrated_engine


def test_migrations_match_models(tmp_path: Path) -> None:
    engine = migrated_engine(tmp_path)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == [], diff
