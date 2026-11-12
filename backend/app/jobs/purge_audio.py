"""Scheduled job: delete stored audio past its retention period (AUDIO_RETENTION=keep_days:N)."""

from app.config import get_settings
from app.services.speech import purge_expired_audio
from app.store.db import get_session

if __name__ == "__main__":
    session = next(get_session())
    print(f"purged {purge_expired_audio(session, get_settings())} audio file(s)")
