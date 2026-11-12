"""Invariant 4: Nothing delays urgent care.

At engine level: the evaluator has no dependency on schemes, storage, consent or models, so none
of them can block an EMERGENCY or HIGH result. API-level checks are added with those features.
"""

import ast
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "app" / "rules" / "engine.py"


def test_engine_depends_only_on_facts_and_content() -> None:
    tree = ast.parse(ENGINE.read_text())
    modules = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module} | {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    allowed = {
        "__future__",
        "collections.abc",
        "enum",
        "typing",
        "pydantic",
        "app.domain.facts",
        "app.rules",
        "app.rules.schema",
    }
    assert modules <= allowed, modules - allowed


def test_engine_is_synchronous() -> None:
    tree = ast.parse(ENGINE.read_text())
    assert not any(isinstance(n, ast.AsyncFunctionDef | ast.Await) for n in ast.walk(tree))
