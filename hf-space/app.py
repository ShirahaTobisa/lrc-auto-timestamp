from __future__ import annotations

import json
import math
import re
from pathlib import Path

import gradio as gr
import torch
import whisperx


MODEL_NAME = "large-v3"
BATCH_SIZE = 8


def align_to_lrc(audio_file: str, lyrics_text: str, language: str) -> tuple[str, str]:
    if not audio_file:
        raise gr.Error("Upload an audio file first.")
    lyric_lines = parse_lyrics(lyrics_text)
    if not lyric_lines:
        raise gr.Error("Paste untimed lyrics first.")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    model = whisperx.load_model(MODEL_NAME, device, compute_type=compute_type)
    audio = whisperx.load_audio(audio_file)
    result = model.transcribe(audio, batch_size=BATCH_SIZE, language=None if language == "auto" else language)

    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
    aligned = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

    word_items = []
    for segment in aligned.get("segments", []):
        for word in segment.get("words", []):
            if "start" in word and "word" in word:
                word_items.append({"start": float(word["start"]), "word": str(word["word"])})

    lrc = build_lrc(lyric_lines, word_items)
    payload = {
        "language": result.get("language"),
        "segments": aligned.get("segments", []),
        "word_count": len(word_items),
    }
    return lrc, json.dumps(payload, ensure_ascii=False, indent=2)


def parse_lyrics(text: str) -> list[str]:
    lines = []
    for raw in text.splitlines():
        line = re.sub(r"\[\d{1,3}:\d{2}(?:[.:]\d{1,3})?\]", "", raw).strip()
        if not line or re.match(r"^\[(ar|ti|al|by|offset|length):", line, re.I):
            continue
        lines.append(line)
    return lines


def build_lrc(lyric_lines: list[str], words: list[dict]) -> str:
    if not words:
        return "\n".join(f"[00:00.00]{line}" for line in lyric_lines)

    normalized_words = [normalize(item["word"]) for item in words]
    cursor = 0
    output = []
    fallback_step = max(1, math.floor(len(words) / max(len(lyric_lines), 1)))

    for index, line in enumerate(lyric_lines):
        target = normalize(line)
        best_pos = cursor
        best_score = -1
        window_end = min(len(words), cursor + 80)
        for pos in range(cursor, window_end):
            joined = ""
            for end in range(pos, min(len(words), pos + 20)):
                joined += normalized_words[end]
                score = similarity(target, joined)
                if score > best_score:
                    best_score = score
                    best_pos = pos
        if best_score < 0.25:
            best_pos = min(len(words) - 1, index * fallback_step)
        cursor = min(len(words) - 1, best_pos + 1)
        output.append(f"{format_lrc_time(words[best_pos]['start'])}{line}")

    return "\n".join(output)


def normalize(text: str) -> str:
    return re.sub(r"[\W_]+", "", text.lower(), flags=re.UNICODE)


def similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    common = len(set(left) & set(right))
    return common / max(len(set(left)), 1)


def format_lrc_time(seconds: float) -> str:
    total_ms = max(0, int(seconds * 1000))
    minutes, rest = divmod(total_ms, 60_000)
    sec, ms = divmod(rest, 1_000)
    return f"[{minutes:02d}:{sec:02d}.{ms // 10:02d}]"


with gr.Blocks(title="LRC WhisperX Aligner") as demo:
    gr.Markdown("# LRC WhisperX Aligner")
    with gr.Row():
        audio = gr.Audio(type="filepath", label="Audio")
        language = gr.Textbox(value="auto", label="Language code")
    lyrics = gr.Textbox(lines=14, label="Untimed lyrics")
    run = gr.Button("Align")
    lrc = gr.Textbox(lines=14, label="LRC draft")
    raw = gr.Code(language="json", label="WhisperX raw alignment")
    run.click(align_to_lrc, inputs=[audio, lyrics, language], outputs=[lrc, raw])


if __name__ == "__main__":
    demo.queue().launch()

