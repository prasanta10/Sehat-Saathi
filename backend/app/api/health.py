"""Liveness and readiness endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__
from app.config import get_settings

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str
    version: str


class ProviderStatus(BaseModel):
    name: str
    provider: str
    ready: bool


class Readiness(BaseModel):
    status: str
    providers: list[ProviderStatus]


@router.get("/healthz", response_model=Health)
def healthz() -> Health:
    return Health(status="ok", version=__version__)


@router.get("/readyz", response_model=Readiness)
def readyz() -> Readiness:
    s = get_settings()
    # Mock providers are always ready. Real providers get a probe in the phase that adds them.
    providers = [
        ProviderStatus(name="asr", provider=s.asr_provider, ready=s.asr_provider == "mock"),
        ProviderStatus(name="llm", provider=s.llm_provider, ready=s.llm_provider == "mock"),
    ]
    status = "ok" if all(p.ready for p in providers) else "degraded"
    return Readiness(status=status, providers=providers)
