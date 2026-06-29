from app.alignment import align_lyrics, normalize_text, similarity
from app.models import LyricLine, TranscriptSegment


def test_normalize_text_removes_punctuation_and_spacing():
    assert normalize_text(" Hello, world! ") == "helloworld"
    assert normalize_text("你 好！") == "你好"


def test_similarity_handles_containment():
    assert similarity("helloworld", "sayhelloworldnow") > 0.5


def test_align_lyrics_matches_vocal_lines_in_order_and_keeps_translation():
    lyrics = [
        LyricLine(index=0, text="Hello world"),
        LyricLine(index=1, text="世界你好", line_type="translation"),
        LyricLine(index=2, text="Second line"),
    ]
    transcript = [
        TranscriptSegment(start_ms=900, end_ms=2_000, text="hello world"),
        TranscriptSegment(start_ms=4_000, end_ms=5_000, text="second line"),
    ]
    aligned = align_lyrics(lyrics, transcript)
    assert aligned[0].start_ms == 900
    assert aligned[1].line_type == "translation"
    assert aligned[1].start_ms == 900
    assert aligned[2].start_ms == 4_000
    assert aligned[0].confidence > 0.8


def test_align_lyrics_estimates_unmatched_lines_when_transcript_is_empty():
    aligned = align_lyrics([LyricLine(index=0, text="Missing")], [])
    assert aligned[0].start_ms == 0
    assert "estimated" in aligned[0].warnings

