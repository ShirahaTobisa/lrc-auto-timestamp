from __future__ import annotations

from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from .jobs import JobStore, export_job_lrc, run_alignment_job, save_upload
from .transcription import CompatibleProviderConfig, NvidiaRivaConfig


BASE_DIR = Path(__file__).resolve().parents[1]
STORE = JobStore(BASE_DIR / "storage")
LOCAL_MODELS = {"base", "small", "medium", "large-v3", "distil-large-v3"}
WHISPER_DEVICES = {"auto", "cpu", "cuda"}
WHISPER_COMPUTE_TYPES = {"auto", "default", "int8", "int8_float16", "float16", "float32"}

app = FastAPI(title="LRC Auto Timestamp", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/jobs")
def create_job(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    lyrics: str = Form(...),
    model_size: str = Form("small"),
    whisper_device: str = Form("auto"),
    whisper_compute_type: str = Form("auto"),
    engine: str = Form("local"),
    provider_base_url: str = Form(""),
    provider_api_key: str = Form(""),
    provider_model: str = Form("openai/whisper-large-v3"),
    nvidia_api_key: str = Form(""),
    nvidia_language_code: str = Form("multi"),
) -> dict[str, str]:
    if engine not in {"local", "nvidia", "compatible"}:
        raise HTTPException(status_code=400, detail="engine must be local, nvidia, or compatible")
    if model_size not in LOCAL_MODELS:
        raise HTTPException(status_code=400, detail=f"model_size must be one of {sorted(LOCAL_MODELS)}")
    if whisper_device not in WHISPER_DEVICES:
        raise HTTPException(status_code=400, detail=f"whisper_device must be one of {sorted(WHISPER_DEVICES)}")
    if whisper_compute_type not in WHISPER_COMPUTE_TYPES:
        raise HTTPException(status_code=400, detail=f"whisper_compute_type must be one of {sorted(WHISPER_COMPUTE_TYPES)}")
    if whisper_compute_type == "default":
        whisper_compute_type = "auto"
    provider_config = None
    nvidia_config = None
    if engine == "compatible":
        provider_config = CompatibleProviderConfig(
            base_url=provider_base_url.strip(),
            api_key=provider_api_key.strip(),
            model=provider_model.strip(),
        )
    if engine == "nvidia":
        nvidia_config = NvidiaRivaConfig(
            api_key=nvidia_api_key.strip(),
            language_code=nvidia_language_code.strip() or "multi",
        )

    job = STORE.create()
    suffix = Path(audio.filename or "audio").suffix or ".audio"
    audio_path = job.work_dir / f"input{suffix}" if job.work_dir else BASE_DIR / "storage" / job.id / f"input{suffix}"
    save_upload(audio.file, audio_path)
    background_tasks.add_task(
        run_alignment_job,
        job,
        audio_path=audio_path,
        lyrics_text=lyrics,
        model_size=model_size,
        whisper_device=whisper_device,
        whisper_compute_type=whisper_compute_type,
        engine=engine,
        provider_config=provider_config,
        nvidia_config=nvidia_config,
    )
    return {"job_id": job.id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = STORE.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return STORE.serialize(job)


@app.get("/api/jobs/{job_id}/result")
def get_result(job_id: str) -> dict:
    job = STORE.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done":
        raise HTTPException(status_code=409, detail="Job is not done")
    return {"lines": STORE.result(job)}


@app.post("/api/jobs/{job_id}/adjust")
def adjust_result(job_id: str, payload: dict) -> dict[str, str]:
    job = STORE.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    lines = payload.get("lines")
    if not isinstance(lines, list):
        raise HTTPException(status_code=400, detail="lines must be a list")
    by_index = {line.get("index"): line for line in lines if isinstance(line, dict)}
    for line in job.result:
        patch = by_index.get(line.index)
        if not patch:
            continue
        if "start_ms" in patch:
            line.start_ms = patch["start_ms"]
        if patch.get("line_type") in {"vocal", "translation"}:
            line.line_type = patch["line_type"]
        if isinstance(patch.get("text"), str):
            line.text = patch["text"]
    return {"status": "ok"}


@app.get("/api/jobs/{job_id}/export.lrc", response_class=PlainTextResponse)
def export_result(job_id: str, translation_mode: str = "follow") -> str:
    job = STORE.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done":
        raise HTTPException(status_code=409, detail="Job is not done")
    if translation_mode not in {"follow", "plain", "timestamped"}:
        raise HTTPException(status_code=400, detail="Invalid translation_mode")
    return export_job_lrc(job, translation_mode=translation_mode)
