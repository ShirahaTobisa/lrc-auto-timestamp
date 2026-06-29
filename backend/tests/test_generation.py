from app.jobs import transcript_to_aligned_lines
from app.models import TranscriptSegment


def test_transcript_to_aligned_lines_preserves_segment_timing():
    lines = transcript_to_aligned_lines(
        [
            TranscriptSegment(start_ms=1200, end_ms=3000, text="Hello world"),
            TranscriptSegment(start_ms=3500, end_ms=5000, text="Second line"),
        ]
    )
    assert [line.text for line in lines] == ["Hello world", "Second line"]
    assert [line.start_ms for line in lines] == [1200, 3500]
    assert lines[0].warnings == []


def test_transcript_to_aligned_lines_marks_transcript_only_results():
    lines = transcript_to_aligned_lines([TranscriptSegment(start_ms=0, end_ms=0, text="Plain transcript")])
    assert lines[0].confidence == 0.25
    assert "estimated" in lines[0].warnings

