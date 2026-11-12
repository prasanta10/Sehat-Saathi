"""Speech capture: consent gate, conversion, transcription, transcript edits, audio retention.

Recording needs the visit's `record_audio` consent. Declining never blocks anything else: the
worker types instead, and the danger-sign check and triage do not depend on consent.
"""

from __future__ import annotations

import logging
import re
from datetime import timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.audio import AudioError, to_wav_16k_mono
from app.ai.interfaces import ASR, ProviderError
from app.config import Settings
from app.domain.state_machine import EncounterState as S
from app.domain.state_machine import can_transition
from app.services.encounters import _move
from app.services.errors import Conflict, DomainError, NotFound
from app.store.models import Capture, Consent, Encounter, Worker, utcnow

log = logging.getLogger("sehat.speech")
CONSENT_KINDS = ("record_audio", "store_record", "share_handoff")


class ConsentRequired(DomainError):
    status = 403


def record_consent(
    session: Session, enc: Encounter, worker: Worker, kind: str, granted: bool
) -> Consent:
    if kind not in CONSENT_KINDS:
        raise DomainError("unknown_consent_kind", kind)
    c = Consent(
        person_id=enc.person_id,
        encounter_id=enc.id,
        kind=kind,
        granted=granted,
        recorded_by=worker.id,
    )
    session.add(c)
    return c


def has_consent(session: Session, enc: Encounter, kind: str) -> bool:
    latest = session.scalars(
        select(Consent)
        .where(Consent.encounter_id == enc.id, Consent.kind == kind)
        .order_by(Consent.recorded_at.desc(), Consent.id.desc())
    ).first()
    return bool(latest and latest.granted)


def _convert(data: bytes, settings: Settings) -> tuple[bytes, float]:
    if len(data) > settings.max_audio_bytes:
        raise DomainError("audio_too_large")
    try:
        return to_wav_16k_mono(data)
    except AudioError as e:
        raise DomainError("unreadable_audio") from e


def _retention_keeps_audio(settings: Settings) -> bool:
    return settings.audio_retention == "delete_on_confirm" or settings.audio_retention.startswith(
        "keep_days:"
    )


async def capture_audio(
    session: Session, enc: Encounter, settings: Settings, asr: ASR, data: bytes
) -> tuple[Capture | None, str | None]:
    """Returns (capture, degraded_reason). On ASR failure nothing is stored except nothing:
    the client tells the worker to type instead."""
    if not has_consent(session, enc, "record_audio"):
        raise ConsentRequired("consent_required", "record_audio consent is needed for this visit")
    if not can_transition(S(enc.status), S.captured):
        raise Conflict("invalid_transition", f"cannot capture in state {enc.status}")
    wav, duration = _convert(data, settings)
    try:
        t = await asr.transcribe(wav, settings.asr_language)
    except ProviderError:
        log.warning("asr provider failed", extra={"provider": getattr(asr, "name", "?")})
        return None, "asr_unavailable"
    capture = Capture(
        encounter_id=enc.id,
        kind="audio",
        transcript=t.text,
        transcript_original=t.text,
        asr_provider=t.provider,
        asr_model_rev=t.model_rev,
        duration_s=duration,
    )
    enc.captures.append(capture)
    session.flush()
    if _retention_keeps_audio(settings) and settings.audio_encryption_key:
        # Audio at rest is always encrypted; without a key it is never written to disk.
        from cryptography.fernet import Fernet

        path = settings.audio_dir / enc.id / f"{capture.id}.wav.enc"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(Fernet(settings.audio_encryption_key.encode()).encrypt(wav))
        capture.audio_path = str(path)
    _move(enc, S.captured)
    return capture, None


async def transcribe_answer(
    session: Session, enc: Encounter, settings: Settings, asr: ASR, data: bytes
) -> str | None:
    """Transcribe a short spoken answer. The audio is never stored."""
    if not has_consent(session, enc, "record_audio"):
        raise ConsentRequired("consent_required", "record_audio consent is needed for this visit")
    wav, _ = _convert(data, settings)
    try:
        return (await asr.transcribe(wav, settings.asr_language)).text
    except ProviderError:
        return None


def edit_transcript(enc: Encounter, capture_id: str, text: str) -> Capture:
    capture = next((c for c in enc.captures if c.id == capture_id), None)
    if capture is None:
        raise NotFound("capture_not_found")
    if S(enc.status) not in (S.captured, S.extracted):
        raise Conflict(
            "invalid_transition", "the transcript can only be edited before questions start"
        )
    if capture.transcript_original is None:
        capture.transcript_original = capture.transcript
    capture.transcript = text.strip()
    if S(enc.status) is S.extracted:
        _move(enc, S.clarifying)  # suggestions came from the old text; worker continues by hand
    return capture


def delete_audio(capture: Capture) -> None:
    if capture.audio_path:
        Path(capture.audio_path).unlink(missing_ok=True)
        capture.audio_path = None


def apply_retention_on_confirm(enc: Encounter, settings: Settings) -> None:
    if settings.audio_retention == "delete_on_confirm":
        for c in enc.captures:
            delete_audio(c)


def purge_expired_audio(session: Session, settings: Settings) -> int:
    """Delete audio older than keep_days:N. Returns the number of files deleted."""
    m = re.fullmatch(r"keep_days:(\d+)", settings.audio_retention)
    if not m:
        return 0
    cutoff = utcnow() - timedelta(days=int(m.group(1)))
    n = 0
    for c in session.scalars(select(Capture).where(Capture.audio_path.is_not(None))):
        created = (
            c.created_at if c.created_at.tzinfo else c.created_at.replace(tzinfo=cutoff.tzinfo)
        )
        if created < cutoff:
            delete_audio(c)
            n += 1
    session.commit()
    return n
