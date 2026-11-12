"""Scheduled job: delete visits older than ENCOUNTER_RETENTION_DAYS (and their audio). The audit
trail keeps only IDs, so it stays. Run daily, e.g. from cron: `python -m app.jobs.purge_records`."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.services import audit
from app.services.speech import delete_audio
from app.store.db import get_session
from app.store.models import Consent, Encounter, utcnow


def purge_old_encounters(session: Session, settings: Settings) -> int:
    cutoff = utcnow() - timedelta(days=settings.encounter_retention_days)
    n = 0
    for enc in list(session.scalars(select(Encounter))):
        created = (
            enc.created_at
            if enc.created_at.tzinfo
            else enc.created_at.replace(tzinfo=cutoff.tzinfo)
        )
        if created >= cutoff:
            continue
        for c in session.scalars(select(Consent).where(Consent.encounter_id == enc.id)):
            session.delete(c)
        session.flush()
        for cap in enc.captures:
            delete_audio(cap)
        audit.record(
            session, "encounter_purged", actor_id=None, encounter_id=enc.id, person_id=enc.person_id
        )
        session.delete(enc)
        n += 1
    session.commit()
    return n


if __name__ == "__main__":
    print(f"purged {purge_old_encounters(next(get_session()), get_settings())} visit(s)")
