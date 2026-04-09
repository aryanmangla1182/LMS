"""ElevenLabs speech-to-text integration."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, Optional
from urllib import error, request


class ElevenLabsSpeechClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
        self.model_id = os.getenv("ELEVENLABS_SPEECH_MODEL", "scribe_v1")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: str,
        mime_type: str,
        language_code: str = "en",
    ) -> Dict[str, Any]:
        if not audio_bytes:
            raise ValueError("audio_bytes is required")
        if not self.enabled:
            return self._fallback_transcript(audio_bytes, filename)

        boundary = "----LMSPitch{0}".format(uuid.uuid4().hex)
        body = self._build_multipart_body(
            boundary,
            audio_bytes=audio_bytes,
            filename=filename,
            mime_type=mime_type,
            language_code=language_code,
        )
        req = request.Request(
            "https://api.elevenlabs.io/v1/speech-to-text",
            data=body,
            headers={
                "xi-api-key": self.api_key,
                "Content-Type": "multipart/form-data; boundary={0}".format(boundary),
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            message = exc.read().decode("utf-8")
            raise RuntimeError(message) from exc
        except Exception:
            return self._fallback_transcript(audio_bytes, filename)

        text = (
            payload.get("text")
            or payload.get("transcript")
            or payload.get("full_text")
            or ""
        ).strip()
        if not text:
            return self._fallback_transcript(audio_bytes, filename)
        return {
            "text": text,
            "model_id": self.model_id,
            "source": "elevenlabs",
            "raw": payload,
        }

    def _build_multipart_body(
        self,
        boundary: str,
        audio_bytes: bytes,
        filename: str,
        mime_type: str,
        language_code: str,
    ) -> bytes:
        parts = []
        parts.append(
            "--{0}\r\n"
            'Content-Disposition: form-data; name="model_id"\r\n\r\n'
            "{1}\r\n".format(boundary, self.model_id).encode("utf-8")
        )
        parts.append(
            "--{0}\r\n"
            'Content-Disposition: form-data; name="language_code"\r\n\r\n'
            "{1}\r\n".format(boundary, language_code).encode("utf-8")
        )
        parts.append(
            "--{0}\r\n"
            'Content-Disposition: form-data; name="file"; filename="{1}"\r\n'
            "Content-Type: {2}\r\n\r\n".format(boundary, filename, mime_type).encode("utf-8")
        )
        parts.append(audio_bytes)
        parts.append("\r\n--{0}--\r\n".format(boundary).encode("utf-8"))
        return b"".join(parts)

    def _fallback_transcript(self, audio_bytes: bytes, filename: str) -> Dict[str, Any]:
        try:
            decoded = audio_bytes.decode("utf-8").strip()
        except UnicodeDecodeError:
            decoded = ""
        text = decoded if len(decoded.split()) >= 8 else (
            "Hello, welcome to Cultfit. I would like to understand your fitness goal, "
            "recommend the right plan for you, handle any pricing questions, and help you take the next step today."
        )
        return {
            "text": text,
            "model_id": "fallback_transcript",
            "source": "fallback",
            "raw": {"filename": filename},
        }
