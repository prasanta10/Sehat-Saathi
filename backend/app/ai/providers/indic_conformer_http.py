"""ASR over HTTP: the `services/asr` wrapper around ai4bharat/indic-conformer-600m-multilingual,
running on the GPU host. Sends 16 kHz mono WAV; receives the transcript and model revision."""

from __future__ import annotations

import httpx

from app.ai.interfaces import ProviderError, Transcript


class IndicConformerHTTP:
    name = "indic_conformer_http"

    def __init__(
        self,
        base_url: str,
        timeout_s: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("ASR_BASE_URL must be set for the indic_conformer_http provider")
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout_s
        self._transport = transport

    async def transcribe(self, audio: bytes, language: str) -> Transcript:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                r = await client.post(
                    f"{self.base_url}/transcribe",
                    files={"audio": ("audio.wav", audio, "audio/wav")},
                    data={"language": language},
                )
                r.raise_for_status()
                body = r.json()
            return Transcript(
                text=str(body["text"]),
                language=language,
                provider=self.name,
                model_rev=body.get("model_rev"),
                duration_s=body.get("duration_s"),
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as e:
            raise ProviderError(type(e).__name__) from e
