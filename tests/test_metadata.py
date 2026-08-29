from app.enrichment.metadata import (
    compute_reading_time_minutes,
    compute_word_count,
    derive_title,
    generate_excerpt,
)


def test_compute_word_count() -> None:
    assert compute_word_count("one two three") == 3
    assert compute_word_count("") == 0


def test_reading_time_minimum_is_one_minute() -> None:
    assert compute_reading_time_minutes(0) == 1
    assert compute_reading_time_minutes(10) == 1


def test_reading_time_scales_with_words_per_minute() -> None:
    assert compute_reading_time_minutes(400, words_per_minute=200) == 2


def test_generate_excerpt_short_text_is_unchanged() -> None:
    assert generate_excerpt("Short text.") == "Short text."


def test_generate_excerpt_truncates_on_word_boundary() -> None:
    text = "word " * 100
    excerpt = generate_excerpt(text, max_length=20)
    assert len(excerpt) <= 21
    assert excerpt.endswith("…")
    assert not excerpt[:-1].endswith(" ")


def test_generate_excerpt_strips_urls() -> None:
    excerpt = generate_excerpt("Check this https://example.com/very/long/path out")
    assert "https://" not in excerpt


def test_derive_title_prefers_explicit_title() -> None:
    assert derive_title("Some text.", "Explicit Title") == "Explicit Title"


def test_derive_title_falls_back_to_first_sentence() -> None:
    assert derive_title("First sentence. Second sentence.", None) == "First sentence."


def test_derive_title_truncates_long_first_line() -> None:
    long_line = "word " * 40
    title = derive_title(long_line, None, max_length=40)
    assert title is not None
    assert len(title) <= 41


def test_derive_title_empty_text_returns_none() -> None:
    assert derive_title("   ", None) is None
