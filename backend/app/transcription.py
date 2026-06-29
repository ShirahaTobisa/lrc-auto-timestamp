from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .models import TranscriptSegment


@dataclass(slots=True)
class CompatibleProviderConfig:
    base_url: str
    api_key: str
    model: str


@dataclass(slots=True)
class NvidiaRivaConfig:
    api_key: str
    server: str = "grpc.nvcf.nvidia.com:443"
    function_id: str = "b702f636-f60c-4a3d-a6f4-f3568c13bd7d"
    language_code: str = "multi"


def convert_to_wav(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(output_path),
    ]
    subprocess.run(command, check=True, capture_output=True)


def transcribe_local(audio_path: Path, model_size: str = "small", device: str | None = None, compute_type: str | None = None) -> list[TranscriptSegment]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("faster-whisper is not installed. Run pip install -r backend/requirements.txt.") from exc

    model = WhisperModel(model_size, device=device or os.getenv("WHISPER_DEVICE", "auto"), compute_type=compute_type or os.getenv("WHISPER_COMPUTE_TYPE", "auto"))
    segments, _info = model.transcribe(str(audio_path), vad_filter=True, word_timestamps=False)
    return [
        TranscriptSegment(
            start_ms=int(segment.start * 1000),
            end_ms=int(segment.end * 1000),
            text=segment.text.strip(),
        )
        for segment in segments
        if segment.text.strip()
    ]


def transcribe_compatible(audio_path: Path, config: CompatibleProviderConfig) -> list[TranscriptSegment]:
    if not config.api_key:
        raise RuntimeError("Provider API key is required for compatible transcription.")
    if not config.base_url:
        raise RuntimeError("Provider base URL is required for compatible transcription.")
    if not config.model:
        raise RuntimeError("Provider transcription model is required.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai is not installed. Run pip install -r backend/requirements.txt.") from exc

    client = OpenAI(api_key=config.api_key, base_url=config.base_url.rstrip("/") + "/")
    with audio_path.open("rb") as audio_file:
        try:
            response = client.audio.transcriptions.create(
                model=config.model,
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
        except TypeError:
            audio_file.seek(0)
            response = client.audio.transcriptions.create(
                model=config.model,
                file=audio_file,
                response_format="verbose_json",
            )
        except Exception:
            audio_file.seek(0)
            response = client.audio.transcriptions.create(
                model=config.model,
                file=audio_file,
            )

    segments = getattr(response, "segments", None)
    if segments is None and isinstance(response, dict):
        segments = response.get("segments")

    if segments:
        parsed: list[TranscriptSegment] = []
        for segment in segments:
            start = getattr(segment, "start", None) if not isinstance(segment, dict) else segment.get("start")
            end = getattr(segment, "end", None) if not isinstance(segment, dict) else segment.get("end")
            text = getattr(segment, "text", None) if not isinstance(segment, dict) else segment.get("text")
            if text:
                parsed.append(TranscriptSegment(start_ms=int(float(start or 0) * 1000), end_ms=int(float(end or 0) * 1000), text=str(text).strip()))
        return parsed

    text = getattr(response, "text", None) if not isinstance(response, dict) else response.get("text")
    if text:
        return [TranscriptSegment(start_ms=0, end_ms=0, text=str(text).strip())]
    return []


def transcribe_nvidia_riva(audio_path: Path, config: NvidiaRivaConfig) -> list[TranscriptSegment]:
    if not config.api_key:
        raise RuntimeError("NVIDIA API key is required.")

    try:
        import riva.client
    except ImportError as exc:
        raise RuntimeError("nvidia-riva-client is not installed. Run pip install -r backend/requirements.txt.") from exc

    auth = riva.client.Auth(
        use_ssl=True,
        uri=config.server,
        metadata_args=[
            ["function-id", config.function_id],
            ["authorization", f"Bearer {config.api_key}"],
        ],
    )
    asr_service = riva.client.ASRService(auth)
    recognition_config = riva.client.RecognitionConfig(
        language_code=config.language_code,
        max_alternatives=1,
        enable_automatic_punctuation=True,
        verbatim_transcripts=True,
        enable_word_time_offsets=True,
    )

    with audio_path.open("rb") as audio_file:
        response = asr_service.offline_recognize(audio_file.read(), recognition_config)

    return _parse_riva_response(response)


def _parse_riva_response(response) -> list[TranscriptSegment]:
    segments: list[TranscriptSegment] = []
    running_start = 0

    for result in getattr(response, "results", []):
        alternatives = getattr(result, "alternatives", [])
        if not alternatives:
            continue
        alternative = alternatives[0]
        words = list(getattr(alternative, "words", []))
        if words:
            current_words: list[str] = []
            start_ms: int | None = None
            end_ms: int | None = None
            for word in words:
                token = getattr(word, "word", "").strip()
                if not token:
                    continue
                if start_ms is None:
                    start_ms = _protobuf_duration_ms(getattr(word, "start_time", None))
                end_ms = _protobuf_duration_ms(getattr(word, "end_time", None))
                current_words.append(token)
                if token.endswith((".", "?", "!", "。", "？", "！")) and current_words:
                    segments.append(TranscriptSegment(start_ms=start_ms or running_start, end_ms=end_ms or start_ms or running_start, text=" ".join(current_words)))
                    running_start = end_ms or running_start
                    current_words = []
                    start_ms = None
            if current_words:
                segments.append(TranscriptSegment(start_ms=start_ms or running_start, end_ms=end_ms or start_ms or running_start, text=" ".join(current_words)))
            continue

        transcript = getattr(alternative, "transcript", "").strip()
        if transcript:
            segments.append(TranscriptSegment(start_ms=running_start, end_ms=running_start, text=transcript))

    return segments


def _protobuf_duration_ms(value) -> int:
    if value is None:
        return 0
    seconds = int(getattr(value, "seconds", 0))
    nanos = int(getattr(value, "nanos", 0))
    return seconds * 1000 + nanos // 1_000_000
