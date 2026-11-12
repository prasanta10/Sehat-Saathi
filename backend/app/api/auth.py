from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.api.deps import SessionDep, WorkerDep, bearer_token
from app.config import get_settings
from app.services import audit
from app.services import auth as svc

router = APIRouter(tags=["auth"])


class LoginIn(BaseModel):
    phone: str = Field(pattern=r"^\d{10}$")
    pin: str = Field(min_length=4, max_length=8)


class RefreshIn(BaseModel):
    refresh_token: str


class TokensOut(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"  # noqa: S105 - OAuth token type name, not a secret


class MeOut(BaseModel):
    id: str
    name: str
    role: str
    state: str | None
    district: str | None
    language: str


@router.post("/auth/login", response_model=TokensOut)
def login(body: LoginIn, session: SessionDep) -> TokensOut:
    try:
        worker, t = svc.login(session, get_settings(), body.phone, body.pin)
    except svc.AuthError:
        audit.record(session, "login_failed", actor_id=None)
        session.commit()
        raise
    audit.record(session, "login", actor_id=worker.id)
    session.commit()
    return TokensOut(
        access_token=t.access_token, refresh_token=t.refresh_token, expires_in=t.expires_in
    )


@router.post("/auth/refresh", response_model=TokensOut)
def refresh(body: RefreshIn, session: SessionDep) -> TokensOut:
    t = svc.refresh(session, get_settings(), body.refresh_token)
    session.commit()
    return TokensOut(
        access_token=t.access_token, refresh_token=t.refresh_token, expires_in=t.expires_in
    )


@router.post("/auth/logout", status_code=204)
def logout(request: Request, session: SessionDep, worker: WorkerDep) -> None:
    svc.logout(session, bearer_token(request))
    audit.record(session, "logout", actor_id=worker.id)
    session.commit()


@router.get("/me", response_model=MeOut)
def me(worker: WorkerDep) -> MeOut:
    return MeOut(
        id=worker.id,
        name=worker.name,
        role=worker.role,
        state=worker.state,
        district=worker.district,
        language=worker.language,
    )
