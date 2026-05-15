from lecture_slide_notes.sources import (
    SourceResolver,
    build_vimeo_player_url,
    build_youtube_watch_url,
    extract_manifest_candidates,
    extract_vimeo_iframe,
    extract_youtube_iframe,
    parse_vimeo_id,
    parse_youtube_id,
)


def test_parse_vimeo_id_from_player_url():
    assert parse_vimeo_id("https://player.vimeo.com/video/1170307610?h=abc") == "1170307610"


def test_build_vimeo_player_url():
    assert build_vimeo_player_url("123") == "https://player.vimeo.com/video/123"


def test_extract_vimeo_iframe():
    html = '<iframe src="https://player.vimeo.com/video/123456?h=test"></iframe>'
    assert extract_vimeo_iframe(html) == "https://player.vimeo.com/video/123456?h=test"


def test_extract_manifest_candidates():
    text = 'fetch("https://example.com/video/playlist.json?x=1&amp;y=2"); fetch("https://cdn.test/master.m3u8")'
    assert extract_manifest_candidates(text) == [
        "https://cdn.test/master.m3u8",
        "https://example.com/video/playlist.json?x=1&y=2",
    ]


def test_parse_youtube_id_from_watch_url():
    assert parse_youtube_id("https://www.youtube.com/watch?si=x&v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_parse_youtube_id_from_short_url():
    assert parse_youtube_id("https://youtu.be/dQw4w9WgXcQ?t=42") == "dQw4w9WgXcQ"


def test_build_youtube_watch_url():
    assert build_youtube_watch_url("dQw4w9WgXcQ") == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_extract_youtube_iframe():
    html = '<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ?si=test"></iframe>'
    assert extract_youtube_iframe(html) == "https://www.youtube.com/embed/dQw4w9WgXcQ?si=test"


def test_parse_youtube_nocookie_embed_url():
    assert parse_youtube_id("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_resolve_youtube_url():
    source = SourceResolver().resolve("https://youtu.be/dQw4w9WgXcQ?t=42", title="YouTube lesson")
    assert source.source_type == "youtube"
    assert source.video_id == "dQw4w9WgXcQ"
    assert source.player_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert source.title == "YouTube lesson"
