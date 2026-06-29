# LRC Auto Timestamp

A local-only source project for generating line-level LRC timestamps from an audio file and untimed lyrics. The app runs on the user's own machine: a FastAPI backend handles transcription and alignment, while a Vite + React frontend provides upload, preview, manual adjustment, and export.

## Status

- Local web app scaffold implemented.
- Backend supports lyric parsing, ffmpeg conversion, local `faster-whisper` transcription, optional OpenAI-compatible transcription providers, alignment, adjustment, and LRC export.
- Frontend supports audio upload, lyric paste/file load, job progress, line editing, per-line playback, translation handling, and export.
- Lyrics mode supports `align` and `generate`: align existing lyrics, or generate an editable LRC draft directly from Whisper output.

## Requirements

- Python 3.11 or 3.12 recommended.
- Node.js 22 recommended.
- `ffmpeg` available on `PATH`.
- A local model cache will be created by `faster-whisper` on first use. Models are not committed to this repo.

## Setup

For free local Whisper only:

```powershell
cd project\lrc-auto-timestamp
.\scripts\setup-local-whisper.ps1
```

Full dependency setup:

```powershell
cd project\lrc-auto-timestamp
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
cd frontend
npm install
```

## Run

Open two terminals:

```powershell
cd project\lrc-auto-timestamp
.\scripts\start-backend.ps1
```

```powershell
cd project\lrc-auto-timestamp
.\scripts\start-frontend.ps1
```

Then open `http://127.0.0.1:5173`.

On Windows, `.\scripts\start-dev.ps1` opens both services in separate PowerShell windows.

After importing into CloudStudio, use the top Run button. `.vscode/preview.yml` calls `scripts/cloudstudio-run.sh` to start both backend and frontend; compute unit selection stays in the CloudStudio UI.

## Local Privacy Model

- The default `local` engine does not upload audio or lyrics.
- User audio, temporary WAV files, and generated job data stay under `backend/storage/`, which is ignored by git.
- Whisper/faster-whisper models are downloaded to the user's normal local model cache.
- The `NVIDIA Whisper` engine uses NVIDIA build's Riva gRPC endpoint `grpc.nvcf.nvidia.com:443` with the page's Whisper function ID.
- The `compatible API` engine is optional for providers that really expose `/v1/audio/transcriptions`.
- API keys are entered in the local web UI for the current request and are not written to environment variables or files by this app.
- Selecting a compatible cloud engine sends audio to that provider.

Provider probe without storing credentials:

```powershell
cd project\lrc-auto-timestamp
.\scripts\probe-provider.ps1
```

The probe asks for the API key using hidden input and tests NVIDIA's Riva gRPC endpoint.

## Alignment Behavior

- Existing LRC time tags and common metadata tags are stripped before alignment.
- Empty lines are ignored.
- Obvious translation lines are preserved but not used as alignment anchors.
- Vocal lines are matched against transcript segments in order, with low-confidence and estimated rows marked for review.
- Local `faster-whisper` uses `word_timestamps=True`; when word timing is available, lyric line starts are matched against word-level timing first.
- `generate` mode does not require lyrics input and converts transcript segments into editable LRC rows.
- If a cloud provider only returns a plain transcript without segment or word timing, matching rows are marked `estimated/low_confidence`.

## Common Errors

`[json.exception.parse_error.101]` usually means faster-whisper/CTranslate2 read an empty or corrupted model JSON file, often after an interrupted model download. Delete the cached model directory for that model and run again.
- Export modes:
  - `follow vocal`: translation lines reuse the previous vocal timestamp.
  - `plain`: translation lines are exported without timestamps.
  - `own time`: translation lines use their stored timestamp when available.

## Tests

Core parser and alignment tests do not require Whisper models:

```powershell
cd project\lrc-auto-timestamp\backend
python -m pytest
```

## Important Files

- `backend/app/lrc.py`: lyric parsing and LRC export.
- `backend/app/alignment.py`: monotonic line-to-transcript matching.
- `backend/app/transcription.py`: ffmpeg, faster-whisper, and optional OpenAI-compatible transcription.
- `backend/app/main.py`: FastAPI endpoints.
- `frontend/src/App.tsx`: local web tool UI.
- `scripts/`: Windows startup scripts.
- `hf-space/`: copyable Hugging Face Spaces WhisperX alignment template.
- `notes/local-free-whisper.zh-CN.md`: free local Whisper setup notes.
- `notes/cloudstudio-whisper-large.zh-CN.md`: CloudStudio GPU large-v3 setup notes.
- `notes/huggingface-whisperx-space.zh-CN.md`: Hugging Face Spaces deployment notes.

## Notes

This is a line-level timestamp tool. It is not intended to produce word-level karaoke timing in v1.
