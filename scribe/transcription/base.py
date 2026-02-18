"""Transcription provider protocol."""

from typing import Protocol

from ..models import Transcript


class TranscriptionProvider(Protocol):
    """Abstract transcription provider for easy swapping."""

    async def transcribe(
        self,
        file_path: str,
        *,
        diarize: bool = True,
        model: str = "nova-2",
        language: str = "en",
    ) -> Transcript: ...
