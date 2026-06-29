---
title: LRC WhisperX Aligner
emoji: 🎵
colorFrom: blue
colorTo: gray
sdk: gradio
python_version: 3.10
suggested_hardware: t4-small
models:
  - openai/whisper-large-v3
tags:
  - whisperx
  - automatic-speech-recognition
  - forced-alignment
  - lyrics
---

# LRC WhisperX Aligner

Upload an audio file and untimed lyrics. The Space returns word-level WhisperX alignment data and a rough LRC draft.

For serious use, upgrade the Space to GPU hardware. CPU works only for short tests.

