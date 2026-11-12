"""Audio conversion: browser recordings (WebM/Opus, WAV, MP4/AAC) -> 16 kHz mono 16-bit WAV."""

from __future__ import annotations

import io
import shutil
import subprocess
import wave


class AudioError(ValueError):
    pass


def to_wav_16k_mono(data: bytes, timeout_s: float = 60.0) -> tuple[bytes, float]:
    """Convert with ffmpeg. Returns (wav bytes, duration in seconds)."""
    if not data:
        raise AudioError("empty audio")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise AudioError("ffmpeg is not installed")
    try:
        proc = subprocess.run(  # noqa: S603 - fixed arguments; audio goes in via stdin
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                "pipe:0",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-sample_fmt",
                "s16",
                "-f",
                "wav",
                "pipe:1",
            ],
            input=data,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise AudioError("conversion failed") from e
    if proc.returncode != 0 or not proc.stdout:
        raise AudioError("unreadable audio")
    with wave.open(io.BytesIO(proc.stdout)) as w:
        # ffmpeg writing to a pipe cannot fill in the header's frame count; count the data instead.
        frames = len(w.readframes(2**31 - 1)) // (w.getsampwidth() * w.getnchannels())
        duration = frames / float(w.getframerate())
    return proc.stdout, duration
