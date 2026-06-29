from app.alignment import align_lyrics, normalize_text, similarity
from app.models import LyricLine, TranscriptSegment, TranscriptWord


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


def test_align_lyrics_prefers_word_timestamps_when_segments_are_coarse():
    lyrics = [
        LyricLine(index=0, text="We had to choose just only one"),
        LyricLine(index=1, text="Even if there's nowhere to go"),
    ]
    transcript = [
        TranscriptSegment(
            start_ms=0,
            end_ms=8_000,
            text="We had to choose just only one even if there is nowhere to go",
            words=[
                TranscriptWord(1_680, 1_900, "We"),
                TranscriptWord(1_910, 2_050, "had"),
                TranscriptWord(2_060, 2_160, "to"),
                TranscriptWord(2_200, 2_500, "choose"),
                TranscriptWord(2_510, 2_700, "just"),
                TranscriptWord(2_710, 2_900, "only"),
                TranscriptWord(2_910, 3_100, "one"),
                TranscriptWord(3_420, 3_600, "Even"),
                TranscriptWord(3_610, 3_760, "if"),
                TranscriptWord(3_770, 4_000, "there"),
                TranscriptWord(4_010, 4_200, "is"),
                TranscriptWord(4_210, 4_500, "nowhere"),
                TranscriptWord(4_510, 4_650, "to"),
                TranscriptWord(4_660, 4_850, "go"),
            ],
        )
    ]
    aligned = align_lyrics(lyrics, transcript)
    assert aligned[0].start_ms == 1_680
    assert aligned[1].start_ms == 3_420
    assert aligned[1].confidence > 0.6
