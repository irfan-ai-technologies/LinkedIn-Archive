from app.site.render import render_markdown


def test_basic_markdown_renders_to_html() -> None:
    html = render_markdown("**bold** and _em_")
    assert "<strong>bold</strong>" in html
    assert "<em>em</em>" in html


def test_script_tags_are_stripped() -> None:
    html = render_markdown("Hello <script>alert('xss')</script> world")
    assert "<script" not in html
    assert "</script>" not in html


def test_on_event_handlers_are_stripped() -> None:
    html = render_markdown('<img src="x.png" onerror="alert(1)">')
    assert "onerror" not in html


def test_javascript_urls_are_neutralized() -> None:
    html = render_markdown("[click me](javascript:alert(1))")
    assert "<a" not in html
    assert 'href="javascript' not in html


def test_external_links_get_safe_attributes() -> None:
    html = render_markdown("[a link](https://example.com)")
    assert 'rel="nofollow noopener noreferrer"' in html
    assert 'target="_blank"' in html


def test_plain_urls_are_linkified() -> None:
    html = render_markdown("Visit https://example.com for more.")
    assert '<a href="https://example.com"' in html


def test_allows_basic_formatting_tags() -> None:
    html = render_markdown("# Heading\n\n- item one\n- item two\n\n> a quote")
    assert "<h1>Heading</h1>" in html
    assert "<li>item one</li>" in html
    assert "<blockquote>" in html


def test_disallowed_tags_are_stripped_but_text_kept() -> None:
    html = render_markdown('<iframe src="evil.com"></iframe>Safe text')
    assert "<iframe" not in html
    assert "Safe text" in html
