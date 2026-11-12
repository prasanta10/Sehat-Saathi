"""Phone + PIN login with Argon2 hashes, short-lived access tokens, rotating refresh tokens and
lockout after repeated failures. Tokens are random; only their SHA-256 hashes are stored."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.services.errors import DomainError
from app.store.models import AuthSession, Worker, utcnow

_hasher = PasswordHasher()
ROLES = ("worker", "supervisor", "admin", "clinical_reviewer")


class AuthError(DomainError):
    status = 401


class Forbidden(DomainError):
    status = 403


class Locked(DomainError):
    status = 429


def hash_pin(pin: str) -> str:
    if not (pin.isdigit() and 4 <= len(pin) <= 8):
        raise DomainError("weak_pin", "PIN must be 4 to 8 digits")
    return _hasher.hash(pin)


def _h(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _aware(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=UTC) if dt is not None and dt.tzinfo is None else dt


@dataclass
class Tokens:
    access_token: str
    refresh_token: str
    expires_in: int


def _issue(session: Session, worker: Worker, settings: Settings) -> Tokens:
    access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    now = utcnow()
    session.add(
        AuthSession(
            worker_id=worker.id,
            access_hash=_h(access),
            refresh_hash=_h(refresh),
            access_expires=now + timedelta(minutes=settings.access_token_minutes),
            refresh_expires=now + timedelta(days=settings.refresh_token_days),
        )
    )
    return Tokens(access, refresh, settings.access_token_minutes * 60)


def login(session: Session, settings: Settings, phone: str, pin: str) -> tuple[Worker, Tokens]:
    worker = session.scalar(select(Worker).where(Worker.phone == phone))
    now = utcnow()
    if worker is None or not worker.active or not worker.pin_hash:
        _hasher.hash("0000")  # similar timing whether or not the phone exists
        raise AuthError("invalid_credentials")
    locked = _aware(worker.locked_until)
    if locked and locked > now:
        raise Locked("locked", "too many attempts; try again later")
    try:
        _hasher.verify(worker.pin_hash, pin)
    except (VerificationError, InvalidHashError):
        worker.failed_logins += 1
        if worker.failed_logins >= settings.max_failed_logins:
            worker.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            worker.failed_logins = 0
        session.commit()
        raise AuthError("invalid_credentials") from None
    worker.failed_logins = 0
    worker.locked_until = None
    if _hasher.check_needs_rehash(worker.pin_hash):
        worker.pin_hash = _hasher.hash(pin)
    return worker, _issue(session, worker, settings)


def authenticate(session: Session, access_token: str) -> Worker:
    s = session.scalar(select(AuthSession).where(AuthSession.access_hash == _h(access_token)))
    exp = _aware(s.access_expires) if s else None
    if s is None or s.revoked or exp is None or exp < utcnow():
        raise AuthError("unauthenticated")
    worker = session.get(Worker, s.worker_id)
    if worker is None or not worker.active:
        raise AuthError("unauthenticated")
    return worker


def refresh(session: Session, settings: Settings, refresh_token: str) -> Tokens:
    s = session.scalar(select(AuthSession).where(AuthSession.refresh_hash == _h(refresh_token)))
    exp = _aware(s.refresh_expires) if s else None
    if s is None or s.revoked or exp is None or exp < utcnow():
        raise AuthError("unauthenticated")
    s.revoked = True  # rotate: each refresh token works once
    worker = session.get(Worker, s.worker_id)
    if worker is None or not worker.active:
        raise AuthError("unauthenticated")
    return _issue(session, worker, settings)


def logout(session: Session, access_token: str) -> None:
    s = session.scalar(select(AuthSession).where(AuthSession.access_hash == _h(access_token)))
    if s is not None:
        s.revoked = True


def require_role(worker: Worker, *roles: str) -> None:
    if worker.role not in roles:
        raise Forbidden("forbidden")
