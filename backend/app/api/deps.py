"""Shared API dependencies."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.ai.interfaces import ASR, Extractor, Writer
from app.rules.loader import RuleSet, get_ruleset
from app.services.auth import AuthError, authenticate
from app.store.db import get_session
from app.store.models import Worker


def session_dep() -> Iterator[Session]:
    yield from get_session()


SessionDep = Annotated[Session, Depends(session_dep)]


def rules_dep() -> RuleSet:
    return get_ruleset()


RulesDep = Annotated[RuleSet, Depends(rules_dep)]


def bearer_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthError("unauthenticated")
    return token


def current_worker(request: Request, session: SessionDep) -> Worker:
    """The logged-in worker. Every data query is scoped to this worker's id."""
    return authenticate(session, bearer_token(request))


WorkerDep = Annotated[Worker, Depends(current_worker)]


def extractor_dep() -> Extractor | None:
    """None = choose from configuration. Tests override this to inject a fake extractor."""
    return None


ExtractorDep = Annotated[Extractor | None, Depends(extractor_dep)]


def asr_dep() -> ASR | None:
    """None = choose from configuration. Tests override this."""
    return None


AsrDep = Annotated[ASR | None, Depends(asr_dep)]


def writer_dep() -> Writer | None:
    return None


WriterDep = Annotated[Writer | None, Depends(writer_dep)]
