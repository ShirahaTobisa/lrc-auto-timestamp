from __future__ import annotations

import re
from difflib import SequenceMatcher

from .models import AlignedLine, LyricLine, TranscriptSegment


LOW_CONFIDENCE = 0.46


def align_lyrics(
    lyrics: list[LyricLine],
    transcript: list[TranscriptSegment],
    *,
    lookahead: int = 10,
    max_segments_per_line: int = 3,
) -> list[AlignedLine]:
    aligned: list[AlignedLine] = []
    cursor = 0
    last_vocal_time: int | None = None
    transcript_has_real_timing = any(segment.end_ms > segment.start_ms for segment in transcript)

    for lyric in lyrics:
        if lyric.line_type == "translation":
            aligned.append(
                AlignedLine(
                    index=lyric.index,
                    text=lyric.text,
                    line_type="translation",
                    start_ms=last_vocal_time,
                    confidence=1.0 if last_vocal_time is not None else 0.0,
                    warnings=["translation"],
                )
            )
            continue

        if not transcript:
            estimated = _estimate_next_time(last_vocal_time)
            aligned.append(_estimated_line(lyric, estimated))
            last_vocal_time = estimated
            continue

        match = _best_match(lyric.text, transcript, cursor, lookahead, max_segments_per_line)
        if match is None:
            estimated = _estimate_next_time(last_vocal_time)
            aligned.append(_estimated_line(lyric, estimated))
            last_vocal_time = estimated
            continue

        start, end, confidence = match
        segment = transcript[start]
        cursor = max(cursor, end + 1)
        warnings = []
        if confidence < LOW_CONFIDENCE:
            warnings.append("low_confidence")
        if not transcript_has_real_timing:
            warnings.extend(["estimated", "low_confidence"])
        if last_vocal_time is not None and segment.start_ms < last_vocal_time:
            warnings.append("unmatched")

        last_vocal_time = max(segment.start_ms, last_vocal_time or segment.start_ms)
        aligned.append(
            AlignedLine(
                index=lyric.index,
                text=lyric.text,
                line_type="vocal",
                start_ms=last_vocal_time,
                confidence=round(confidence if transcript_has_real_timing else min(confidence, 0.25), 3),
                warnings=list(dict.fromkeys(warnings)),
            )
        )

    return aligned


def _best_match(
    lyric: str,
    transcript: list[TranscriptSegment],
    cursor: int,
    lookahead: int,
    max_segments_per_line: int,
) -> tuple[int, int, float] | None:
    if cursor >= len(transcript):
        return None

    normalized_lyric = normalize_text(lyric)
    if not normalized_lyric:
        return None

    best: tuple[int, int, float] | None = None
    search_end = min(len(transcript), cursor + lookahead)
    for start in range(cursor, search_end):
        combined = ""
        for end in range(start, min(len(transcript), start + max_segments_per_line)):
            combined = f"{combined} {transcript[end].text}".strip()
            score = similarity(normalized_lyric, normalize_text(combined))
            distance_penalty = max(0, start - cursor) * 0.025
            length_penalty = abs(len(normalized_lyric) - len(normalize_text(combined))) / max(len(normalized_lyric), 1) * 0.05
            adjusted = max(0.0, score - distance_penalty - length_penalty)
            if best is None or adjusted > best[2]:
                best = (start, end, adjusted)

    return best


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\[[^\]]+\]", "", text)
    text = re.sub(r"[\s'’`~!！?？,，.。:：;；\"“”()（）\-_/\\]+", "", text)
    return text


def similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left in right or right in left:
        return min(len(left), len(right)) / max(len(left), len(right))
    return SequenceMatcher(None, left, right).ratio()


def _estimate_next_time(last_vocal_time: int | None) -> int:
    return 0 if last_vocal_time is None else last_vocal_time + 2_500


def _estimated_line(lyric: LyricLine, start_ms: int) -> AlignedLine:
    return AlignedLine(
        index=lyric.index,
        text=lyric.text,
        line_type="vocal",
        start_ms=start_ms,
        confidence=0.0,
        warnings=["estimated", "unmatched"],
    )
