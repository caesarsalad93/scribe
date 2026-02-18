"""Deepgram transcription implementation (SDK v5)."""

import asyncio
from pathlib import Path

from deepgram import DeepgramClient

from ..config import get_deepgram_api_key
from ..models import Transcript, Utterance


class DeepgramProvider:
    """Deepgram transcription provider."""

    def __init__(self) -> None:
        self._client: DeepgramClient | None = None

    @property
    def client(self) -> DeepgramClient:
        if self._client is None:
            self._client = DeepgramClient(api_key=get_deepgram_api_key())
        return self._client

    async def transcribe(
        self,
        file_path: str,
        *,
        diarize: bool = True,
        model: str = "nova-2",
        language: str = "en",
    ) -> Transcript:
        path = Path(file_path)
        with open(path, "rb") as f:
            buffer_data = f.read()

        response = await asyncio.to_thread(
            self._transcribe_sync,
            buffer_data,
            diarize=diarize,
            model=model,
            language=language,
        )

        return self._parse_response(response, str(path))

    def _transcribe_sync(
        self,
        data: bytes,
        *,
        diarize: bool,
        model: str,
        language: str,
    ) -> object:
        return self.client.listen.v1.media.transcribe_file(
            request=data,
            model=model,
            language=language,
            smart_format=True,
            diarize=diarize,
            utterances=True,
            punctuate=True,
        )

    def _parse_response(self, response: object, source_file: str) -> Transcript:
        # SDK v5 returns a ListenV1Response with .results.channels etc.
        results = response.results  # type: ignore[attr-defined]
        channel = results.channels[0]
        alt = channel.alternatives[0]

        raw_text = alt.transcript or ""

        # Duration from metadata
        duration = 0.0
        metadata = getattr(response, "metadata", None)
        if metadata and hasattr(metadata, "duration"):
            duration = float(metadata.duration)

        # Parse utterances
        utterances: list[Utterance] = []
        speaker_set: set[int] = set()

        resp_utterances = getattr(results, "utterances", None)
        if resp_utterances:
            for utt in resp_utterances:
                speaker_idx = getattr(utt, "speaker", 0)
                speaker_set.add(speaker_idx)
                utterances.append(
                    Utterance(
                        speaker=speaker_idx,
                        start=utt.start,
                        end=utt.end,
                        text=utt.transcript,
                    )
                )

        speakers = [f"Speaker {i}" for i in sorted(speaker_set)]

        return Transcript(
            source_file=source_file,
            duration=duration,
            speakers=speakers,
            utterances=utterances,
            raw_text=raw_text,
        )
