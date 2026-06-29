from __future__ import annotations

import re
from difflib import SequenceMatcher

from .models import AlignedLine, LyricLine, TranscriptSegment, TranscriptWord


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
    word_cursor = 0
    last_vocal_time: int | None = None
    transcript_has_real_timing = any(segment.end_ms > segment.start_ms for segment in transcript)
    words = _flatten_words(transcript)

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

        word_match = _best_word_match(lyric.text, words, word_cursor)
        if word_match is not None:
            start_word, end_word, confidence = word_match
            word = words[start_word]
            word_cursor = max(word_cursor, end_word + 1)
            start_ms = max(word.start_ms, last_vocal_time or word.start_ms)
            warnings = []
            if confidence < LOW_CONFIDENCE:
                warnings.append("low_confidence")
            last_vocal_time = start_ms
            aligned.append(
                AlignedLine(
                    index=lyric.index,
                    text=lyric.text,
                    line_type="vocal",
                    start_ms=start_ms,
                    confidence=round(confidence, 3),
                    warnings=warnings,
                )
            )
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


def _flatten_words(transcript: list[TranscriptSegment]) -> list[TranscriptWord]:
    words: list[TranscriptWord] = []
    for segment in transcript:
        words.extend(segment.words)
    return words


def _best_word_match(
    lyric: str,
    words: list[TranscriptWord],
    cursor: int,
    *,
    lookahead_words: int = 80,
    max_words_per_line: int = 18,
) -> tuple[int, int, float] | None:
    if cursor >= len(words):
        return None
    normalized_lyric = normalize_text(lyric)
    if not normalized_lyric:
        return None

    lyric_len = max(1, len(normalized_lyric))
    estimated_words = max(1, min(max_words_per_line, round(lyric_len / 5)))
    best: tuple[int, int, float] | None = None
    search_end = min(len(words), cursor + lookahead_words)

    for start in range(cursor, search_end):
        joined = ""
        for end in range(start, min(len(words), start + max_words_per_line)):
            joined += normalize_text(words[end].word)
            if not joined:
                continue
            score = similarity(normalized_lyric, joined)
            length_ratio = min(len(joined), lyric_len) / max(len(joined), lyric_len)
            distance_penalty = max(0, start - cursor) * 0.01
            word_count = end - start + 1
            word_penalty = abs(word_count - estimated_words) * 0.01
            adjusted = max(0.0, score * 0.82 + length_ratio * 0.18 - distance_penalty - word_penalty)
            if best is None or adjusted > best[2]:
                best = (start, end, adjusted)

    if best is None or best[2] < 0.28:
        return None
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
