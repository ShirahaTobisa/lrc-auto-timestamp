from __future__ import annotations

import re

from .models import AlignedLine, LyricLine


TIME_TAG_RE = re.compile(r"\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]")
META_TAG_RE = re.compile(r"^\[(ar|ti|al|by|offset|length|re|ve):.*\]$", re.IGNORECASE)


def parse_time_tag(tag: str) -> int:
    match = TIME_TAG_RE.fullmatch(tag.strip())
    if not match:
        raise ValueError(f"Invalid LRC time tag: {tag}")

    minutes = int(match.group(1))
    seconds = int(match.group(2))
    fraction = match.group(3) or "0"
    if len(fraction) == 1:
        millis = int(fraction) * 100
    elif len(fraction) == 2:
        millis = int(fraction) * 10
    else:
        millis = int(fraction[:3])
    return minutes * 60_000 + seconds * 1_000 + millis


def format_lrc_time(ms: int | None) -> str:
    value = max(0, int(ms or 0))
    minutes, rest = divmod(value, 60_000)
    seconds, millis = divmod(rest, 1_000)
    centiseconds = round(millis / 10)
    if centiseconds >= 100:
        seconds += 1
        centiseconds = 0
    if seconds >= 60:
        minutes += 1
        seconds = 0
    return f"[{minutes:02d}:{seconds:02d}.{centiseconds:02d}]"


def strip_time_tags(line: str) -> tuple[str, int | None]:
    times = TIME_TAG_RE.findall(line)
    first_time = None
    if times:
        first_match = TIME_TAG_RE.search(line)
        if first_match:
            first_time = parse_time_tag(first_match.group(0))
    return TIME_TAG_RE.sub("", line).strip(), first_time


def parse_lyrics(text: str) -> list[LyricLine]:
    lines: list[LyricLine] = []
    previous_vocal: LyricLine | None = None

    for raw_line in text.splitlines():
        raw_line = raw_line.strip()
        if not raw_line or META_TAG_RE.match(raw_line):
            continue

        stripped, old_time = strip_time_tags(raw_line)
        if not stripped:
            continue

        line_type = "translation" if _looks_like_translation(stripped, previous_vocal.text if previous_vocal else None) else "vocal"
        line = LyricLine(index=len(lines), text=stripped, line_type=line_type, original_time_ms=old_time)
        lines.append(line)
        if line_type == "vocal":
            previous_vocal = line

    return lines


def export_lrc(lines: list[AlignedLine], translation_mode: str = "follow") -> str:
    output: list[str] = []
    last_vocal_time: int | None = None

    for line in lines:
        if line.line_type == "vocal":
            last_vocal_time = line.start_ms
            output.append(f"{format_lrc_time(line.start_ms)}{line.text}")
        elif translation_mode == "follow" and last_vocal_time is not None:
            output.append(f"{format_lrc_time(last_vocal_time)}{line.text}")
        elif translation_mode == "timestamped" and line.start_ms is not None:
            output.append(f"{format_lrc_time(line.start_ms)}{line.text}")
        elif translation_mode == "plain":
            output.append(line.text)
        else:
            output.append(line.text)

    return "\n".join(output) + ("\n" if output else "")


def _looks_like_translation(text: str, previous_vocal: str | None) -> bool:
    lowered = text.lower()
    if lowered.startswith(("translation:", "translate:", "译：", "翻译：", "//")):
        return True
    if previous_vocal is None:
        return False

    current_script = _dominant_script(text)
    previous_script = _dominant_script(previous_vocal)
    if current_script == "unknown" or previous_script == "unknown":
        return False

    has_translation_hint = text.startswith(("(", "（")) and text.endswith((")", "）"))
    return current_script != previous_script or has_translation_hint


def _dominant_script(text: str) -> str:
    latin = 0
    cjk = 0
    kana = 0
    hangul = 0
    for char in text:
        code = ord(char)
        if "a" <= char.lower() <= "z":
            latin += 1
        elif 0x4E00 <= code <= 0x9FFF:
            cjk += 1
        elif 0x3040 <= code <= 0x30FF:
            kana += 1
        elif 0xAC00 <= code <= 0xD7AF:
            hangul += 1
    counts = {"latin": latin, "cjk": cjk, "kana": kana, "hangul": hangul}
    script, count = max(counts.items(), key=lambda item: item[1])
    return script if count >= 2 else "unknown"

