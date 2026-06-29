from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


LineType = Literal["vocal", "translation"]
WarningCode = Literal["low_confidence", "unmatched", "estimated", "translation"]


@dataclass(slots=True)
class LyricLine:
    index: int
    text: str
    line_type: LineType = "vocal"
    original_time_ms: int | None = None


@dataclass(slots=True)
class TranscriptSegment:
    start_ms: int
    end_ms: int
    text: str


@dataclass(slots=True)
class AlignedLine:
    index: int
    text: str
    line_type: LineType
    start_ms: int | None
    confidence: float
    warnings: list[WarningCode] = field(default_factory=list)

