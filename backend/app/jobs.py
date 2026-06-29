from __future__ import annotations

import shutil
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from .alignment import align_lyrics
from .lrc import export_lrc, parse_lyrics
from .models import AlignedLine
from .transcription import CompatibleProviderConfig, NvidiaRivaConfig, convert_to_wav, transcribe_compatible, transcribe_local, transcribe_nvidia_riva


JobStatus = Literal["queued", "processing", "done", "error"]


@dataclass
class Job:
    id: str
    status: JobStatus = "queued"
    progress: float = 0.0
    message: str = "Queued"
    error: str | None = None
    result: list[AlignedLine] = field(default_factory=list)
    work_dir: Path | None = None


class JobStore:
    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, Job] = {}

    def create(self) -> Job:
        job_id = uuid.uuid4().hex
        job = Job(id=job_id, work_dir=self.storage_dir / job_id)
        job.work_dir.mkdir(parents=True, exist_ok=True)
        self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def serialize(self, job: Job) -> dict:
        return {
            "id": job.id,
            "status": job.status,
            "progress": job.progress,
            "message": job.message,
            "error": job.error,
        }

    def result(self, job: Job) -> list[dict]:
        return [asdict(line) for line in job.result]


def transcript_to_aligned_lines(transcript) -> list[AlignedLine]:
    return [
        AlignedLine(
            index=index,
            text=segment.text,
            line_type="vocal",
            start_ms=segment.start_ms,
            confidence=0.75 if segment.end_ms > segment.start_ms else 0.25,
            warnings=[] if segment.end_ms > segment.start_ms else ["estimated", "low_confidence"],
        )
        for index, segment in enumerate(transcript)
        if segment.text.strip()
    ]


def run_alignment_job(
    job: Job,
    *,
    audio_path: Path,
    lyrics_text: str,
    model_size: str,
    whisper_device: str,
    whisper_compute_type: str,
    engine: str,
    provider_config: CompatibleProviderConfig | None = None,
    nvidia_config: NvidiaRivaConfig | None = None,
) -> None:
    try:
        if job.work_dir is None:
            raise RuntimeError("Job has no working directory.")

        job.status = "processing"
        job.progress = 0.1
        job.message = "Preparing lyrics"
        lyrics = parse_lyrics(lyrics_text) if lyrics_text.strip() else []

        wav_path = job.work_dir / "audio.wav"
        job.progress = 0.25
        job.message = "Converting audio with ffmpeg"
        convert_to_wav(audio_path, wav_path)

        job.progress = 0.45
        job.message = "Transcribing audio"
        if engine == "nvidia":
            if nvidia_config is None:
                raise RuntimeError("NVIDIA Riva config is required.")
            transcript = transcribe_nvidia_riva(wav_path, nvidia_config)
        elif engine == "compatible":
            if provider_config is None:
                raise RuntimeError("Compatible provider config is required.")
            transcript = transcribe_compatible(wav_path, provider_config)
        else:
            transcript = transcribe_local(wav_path, model_size=model_size, device=whisper_device, compute_type=whisper_compute_type)

        job.progress = 0.8
        if lyrics:
            job.message = "Aligning lyrics"
            job.result = align_lyrics(lyrics, transcript)
        else:
            job.message = "Generating lyrics"
            job.result = transcript_to_aligned_lines(transcript)
            if not job.result:
                raise RuntimeError("No transcript lines were generated.")
        job.progress = 1.0
        job.status = "done"
        job.message = "Done"
    except Exception as exc:  # noqa: BLE001 - surfaced to local UI.
        job.status = "error"
        job.error = str(exc)
        job.message = "Failed"


def save_upload(source, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as target:
        shutil.copyfileobj(source, target)


def export_job_lrc(job: Job, translation_mode: str = "follow") -> str:
    return export_lrc(job.result, translation_mode=translation_mode)
