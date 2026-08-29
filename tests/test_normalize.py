from app.ingestion.normalize import (
    extract_hashtags,
    extract_links,
    guess_language,
    strip_hashtags_and_urls_for_excerpt,
)


def test_extract_hashtags_dedupes_and_preserves_order() -> None:
    text = "Loving #AgenticAI and #MCP. Also #AgenticAI again."
    assert extract_hashtags(text) == ["AgenticAI", "MCP"]


def test_extract_hashtags_ignores_bare_hash() -> None:
    assert extract_hashtags("price is # 5 not a tag") == []


def test_extract_links_dedupes_and_strips_trailing_punctuation() -> None:
    text = "See https://example.com/a, and also https://example.com/a again. Also (https://example.com/b)."
    links = extract_links(text)
    urls = [link.url for link in links]
    assert urls == ["https://example.com/a", "https://example.com/b"]
    assert links[0].domain == "example.com"


def test_strip_hashtags_and_urls_for_excerpt() -> None:
    text = "Check this https://example.com out.   Extra   spaces."
    assert strip_hashtags_and_urls_for_excerpt(text) == "Check this out. Extra spaces."


def test_guess_language_ascii_is_english() -> None:
    assert guess_language("This is a normal English sentence.") == "en"


def test_guess_language_non_ascii_is_unknown() -> None:
    assert guess_language("これは日本語のテキストです") is None


def test_guess_language_empty_text_is_unknown() -> None:
    assert guess_language("1234 !!! ...") is None
