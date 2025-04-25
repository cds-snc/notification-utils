from notifications_utils.formatters import (
    CTA_MARKER,
    is_cta_link,
    notify_email_markdown,
    strip_cta_marker,
)


def test_is_cta_link():
    """Test the is_cta_link helper function"""
    assert is_cta_link("https://example.com" + CTA_MARKER) is True
    assert is_cta_link("https://example.com") is False
    assert is_cta_link("https://example.com#something") is False


def test_strip_cta_marker():
    """Test the strip_cta_marker helper function"""
    assert strip_cta_marker("https://example.com" + CTA_MARKER) == "https://example.com"
    assert strip_cta_marker("https://example.com") == "https://example.com"


def test_cta_links_in_email_renderer():
    """Test that links with the CTA marker are rendered properly in emails"""
    # Normal link
    markdown_content = "[Sign in](https://www.canada.ca/sign-in)"
    html = notify_email_markdown(markdown_content)
    assert 'style="word-wrap: break-word;"' in html
    assert "background-color: rgb(178, 227, 255);" not in html

    # CTA link
    markdown_content = "[Sign in](https://www.canada.ca/sign-in#CTA)"
    html = notify_email_markdown(markdown_content)
    assert "background-color: rgb(178, 227, 255);" in html
    assert "font-weight: 700;" in html
    assert 'href="https://www.canada.ca/sign-in"' in html
    assert "#CTA" not in html


def test_cta_links_dont_affect_other_renderers():
    """Test that CTA links don't affect other markdown renderers"""
    from notifications_utils.formatters import notify_plain_text_email_markdown

    markdown_content = "[Sign in](https://www.canada.ca/sign-in#CTA)"
    result = notify_plain_text_email_markdown(markdown_content)
    assert "Sign in: https://www.canada.ca/sign-in#CTA" in result
