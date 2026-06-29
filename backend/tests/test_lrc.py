from app.lrc import export_lrc, format_lrc_time, parse_lyrics, parse_time_tag
from app.models import AlignedLine


def test_parse_time_tag_accepts_centiseconds_and_milliseconds():
    assert parse_time_tag("[01:02.34]") == 62_340
    assert parse_time_tag("[01:02.345]") == 62_345
    assert format_lrc_time(62_345) == "[01:02.34]"


def test_parse_lyrics_strips_old_timestamps_metadata_and_empty_lines():
    lyrics = """
    [ar:Someone]
    [00:01.00]Hello world

    [00:03.40]Second line
    """
    parsed = parse_lyrics(lyrics)
    assert [line.text for line in parsed] == ["Hello world", "Second line"]
    assert parsed[0].original_time_ms == 1_000


def test_parse_lyrics_marks_obvious_translation_line():
    parsed = parse_lyrics("Hello world\n世界你好\nNext line\n")
    assert [line.line_type for line in parsed] == ["vocal", "translation", "vocal"]


def test_export_lrc_can_keep_translation_plain_or_following_vocal_time():
    lines = [
        AlignedLine(index=0, text="Hello world", line_type="vocal", start_ms=1_000, confidence=1),
        AlignedLine(index=1, text="世界你好", line_type="translation", start_ms=1_000, confidence=1),
    ]
    assert export_lrc(lines, "follow") == "[00:01.00]Hello world\n[00:01.00]世界你好\n"
    assert export_lrc(lines, "plain") == "[00:01.00]Hello world\n世界你好\n"

