import pytest
from notifications_utils.template import get_html_email_body


def test_lang_tags_in_templates():
    content = "[[en]]\n# EN title\nEN body\n[[/en]]\n[[fr]]\n# FR title\n FR content\n[[/fr]]"
    html = get_html_email_body(content, {})
    assert '<div lang="en-ca">' in html
    assert '<div lang="fr-ca">' in html
    assert "h2" in html


@pytest.mark.parametrize(
    "bad_content",
    [
        "[[en]\nEN text\n[[/en]]",  # missing bracket
        # "[[en]]EN text\n[[/en]]",  # missing \n
        # "[[en]]\nEN text[[/en]]",  # missing \n
        "[[EN]]\nEN text\n[[/EN]]",  # tags not lowercase
        "[[en]]\nEN text\n",  # tag missing
        "EN text\n[[/en]]",  # tag missing
        "((en))\nEN text\n((/en))",  # wrong brackets
        # "[[en]]EN text[[/en]]",  # tags not on their own line
    ],
)
def test_lang_tags_in_templates_bad_content(bad_content: str):
    html = get_html_email_body(bad_content, {})
    assert '<div lang="en-ca">' not in html


@pytest.mark.parametrize(
    "good_content",
    [
        "[[fr]]\nFR text\n[[/fr]]",
        "[[fr]]\n\nFR text\n\n[[/fr]]",  # extra newline
        "[[fr]]\n\n\nFR text\n\n\n[[/fr]]",  # two extra newlines
        "[[fr]] \nFR text\n[[/fr]] ",  # extra spaces
        " [[fr]] \nFR text\n [[/fr]] \t    ",  # more extra spaces and tabs
    ],
)
def test_lang_tags_in_templates_good_content(good_content: str):
    html = get_html_email_body(good_content, {})
    assert '<div lang="fr-ca">' in html


@pytest.mark.parametrize(
    "bad_content",
    [
        "[[ircc-ga-seal]",  # missing bracket
        "[ircc-ga-seal]",  # missing brackets
        "[[ircc-coat-arms]",  # missing bracket
        "[ircc-coat-arms]",  # missing brackets
        "[[ircc-seal]",  # missing bracket
        "[ircc-seal]",  # missing brackets
        "[[ircc-gc-seal]",  # missing bracket
        "[ircc-gc-seal]",  # missing brackets
    ],
)
def test_ircc_tags_in_templates_bad_content(bad_content: str):
    html = get_html_email_body(bad_content, {})
    assert "<img" not in html
    assert "[ircc-" in html


@pytest.mark.parametrize(
    "good_content",
    [
        "[[ircc-ga-seal]]\nEmail Body",
        "Hi,\n[[ircc-ga-seal]]\nBye",
        "Hi,\n\n[[ircc-ga-seal]]\n\nBye",
        "Hi,\n\n[[ircc-seal]]\n\nBye",
        "Hi,\n\n[[ircc-gc-seal]]\n\nBye",
        "Hi,\n\n[[ircc-ga-seal]]\n\n# Title\nBye",
        "Hi,\n\n[[ircc-coat-arms]]\n\n# Title\nBye",
    ],
)
def test_ircc_tags_in_templates_good_content(good_content: str):
    html = get_html_email_body(good_content, {})
    assert "<img" in html
    assert "[[ircc" not in html
