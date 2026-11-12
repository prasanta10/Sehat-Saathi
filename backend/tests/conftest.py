from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import rules_dep, session_dep
from app.config import REPO_ROOT
from app.main import create_app
from app.rules.loader import RuleSet, load_ruleset
from app.seed import seed
from app.store.db import make_engine

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "content"
BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def fixture_rules() -> RuleSet:
    return load_ruleset(FIXTURE_ROOT)


def migrated_engine(tmp_path: Path):  # type: ignore[no-untyped-def]
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
    return engine


def _client(tmp_path: Path, rules: RuleSet) -> TestClient:
    engine = migrated_engine(tmp_path)
    maker = sessionmaker(bind=engine, expire_on_commit=False)

    def session_override() -> Iterator[Session]:
        with maker() as s:
            yield s

    with maker() as s:
        seed(s)
    app = create_app()
    app.dependency_overrides[session_dep] = session_override
    app.dependency_overrides[rules_dep] = lambda: rules
    client = TestClient(app)
    login(client, "9000000001", "1234")
    return client


def login(client: TestClient, phone: str, pin: str) -> None:
    r = client.post("/api/v1/auth/login", json={"phone": phone, "pin": pin})
    assert r.status_code == 200, r.text
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"


@pytest.fixture(scope="session")
def repo_rules() -> RuleSet:
    return load_ruleset(REPO_ROOT)


@pytest.fixture
def client(tmp_path: Path, repo_rules: RuleSet) -> TestClient:
    return _client(tmp_path, repo_rules)


@pytest.fixture
def fixture_client(tmp_path: Path) -> TestClient:
    return _client(tmp_path, load_ruleset(FIXTURE_ROOT))
