import pytest
from bs4 import BeautifulSoup
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
        "[[EN]]\nEN text\n[[/EN]]",  # tags not lowercase
        "[[en]]\nEN text\n",  # tag missing
        "EN text\n[[/en]]",  # tag missing
        "((en))\nEN text\n((/en))",  # wrong brackets
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


class TestVariablesInLinks:
    @pytest.mark.parametrize(
        "template_content,variable,expected_html",
        [
            ("((variable))", {}, "((variable))"),
            ("((variable))", {"variable": "my content"}, "my content"),
        ],
    )
    def test_variable(self, template_content, variable, expected_html):
        html = BeautifulSoup(str(get_html_email_body(template_content, variable)), "html.parser")
        rendered_markdown = html.get_text()
        assert rendered_markdown == expected_html

    @pytest.mark.parametrize(
        "template_content,variable,expected_link_text,expected_href",
        [
            (
                "[link text with ((variable))](https://developer.mozilla.org/en-US/)",
                {},
                "link text with ((variable))",
                "https://developer.mozilla.org/en-US/",
            ),
            (
                "[link text with ((variable))](https://developer.mozilla.org/en-US/)",
                {"variable": "var"},
                "link text with var",
                "https://developer.mozilla.org/en-US/",
            ),
            (
                "[link with query param](https://developer.mozilla.org/en-US/search?q=asdf)",
                {},
                "link with query param",
                "https://developer.mozilla.org/en-US/search?q=asdf",
            ),
            ("[link with variable as url](((url_var)))", {}, "link with variable as url", "url_var"),
            (
                "[link with variable as url](((url_var)))",
                {"url_var": "replaced_variable"},
                "link with variable as url",
                "replaced_variable",
            ),
            ("[link with variable in url](((url_var))/en-US/)", {}, "link with variable in url", "url_var/en-US/"),
            (
                "[link with variable in url](((url_var))/en-US/)",
                {"url_var": "replaced_variable"},
                "link with variable in url",
                "replaced_variable/en-US/",
            ),
            (
                "[link with variable and query param](((url_var))/en-US/search?q=asdf)",
                {},
                "link with variable and query param",
                "url_var/en-US/search?q=asdf",
            ),
            (
                "[link with variable and query param](((url_var))/en-US/search?q=asdf)",
                {"url_var": "replaced_variable"},
                "link with variable and query param",
                "replaced_variable/en-US/search?q=asdf",
            ),
        ],
    )
    def test_link_text_with_variable(self, template_content, variable, expected_link_text, expected_href):
        html = BeautifulSoup(str(get_html_email_body(template_content, variable)), "html.parser")
        href = html.select("a")[0].get_attribute_list("href")[0]
        link_text = html.select("a")[0].get_text()
        assert href == expected_href
        assert link_text == expected_link_text


class TestRTLTags:
    def test_rtl_tags_in_templates(self):
        content = "[[rtl]]\nRTL content\n[[/rtl]]"
        html = get_html_email_body(content, {})
        assert '<div dir="rtl">' in html
        assert "RTL content" in html

    @pytest.mark.parametrize(
        "nested_content",
        [
            "[[rtl]]\nRTL content\n[[/rtl]]\n[[rtl]]\nMore RTL content\n[[/rtl]]",
            "[[rtl]]\nRTL content with [[en]]\nEN content\n[[/en]]\n[[/rtl]]",
        ],
    )
    def test_rtl_tags_in_templates_nested_content(self, nested_content: str):
        html = get_html_email_body(nested_content, {})
        assert '<div dir="rtl">' in html
        assert "RTL content" in html

    @pytest.mark.parametrize(
        "bad_content",
        [
            "[[rtl]\nRTL content\n[[/rtl]]",  # missing bracket
            "[[RTL]]\nRTL content\n[[/RTL]]",  # tags not lowercase
            "[[rtl]]\nRTL content\n",  # tag missing
            "RTL content\n[[/rtl]]",  # tag missing
            "((rtl))\nRTL content\n((/rtl))",  # wrong brackets
        ],
    )
    def test_rtl_tags_in_templates_bad_content(self, bad_content: str):
        html = get_html_email_body(bad_content, {})
        assert '<div dir="rtl">' not in html

    @pytest.mark.parametrize(
        "mixed_content",
        [
            "[[rtl]]\nRTL content\n[[/rtl]]\nLTR content",
            "LTR content\n[[rtl]]\nRTL content\n[[/rtl]]",
        ],
    )
    def test_rtl_tags_in_templates_mixed_content(self, mixed_content: str):
        html = get_html_email_body(mixed_content, {})
        assert '<div dir="rtl">' in html
        assert "RTL content" in html
        assert "LTR content" in html

    @pytest.mark.parametrize(
        "content, extra_tag",
        [
            ("[[rtl]] # RTL CONTENT [[/rtl]]", "h2"),
            ("[[rtl]] ## RTL CONTENT [[/rtl]]", "h3"),
            ("[[rtl]]\n- RTL CONTENT 1\n-item 2\n[[/rtl]]", "ul"),
            ("[[rtl]]\n1. RTL CONTENT 1\n1. item 2\n[[/rtl]]", "ol"),
            ("[[rtl]]**RTL CONTENT**[[/rtl]]", "strong"),
            ("[[rtl]]_RTL CONTENT_[[/rtl]]", "em"),
            ("[[rtl]]---\nRTL CONTENT[[/rtl]]", "hr"),
            (
                "[[rtl]]1. RTL CONTENT\n1. First level\n   1. Second level\n   1. Second level\n   1. Second level\n      1. Third level\n      1. Third level\n         1. Fourth level\n         1. Fourth level\n            1. Fifth level\n            1. Fifth level[[/rtl]]",
                "ol",
            ),
            ("[[rtl]]^RTL CONTENT[[/rtl]]", "blockquote"),
            ("[[rtl]]RTL CONTENT now at https://www.canada.ca[[/rtl]]", "a"),
            ("[[rtl]][RTL CONTENT](https://www.canada.ca/sign-in)[[/rtl]]", "a"),
            ("[[rtl]][[en]]RTL CONTENT[[/en]][[/rtl]]", 'div lang="en-ca"'),
            ("[[rtl]][[fr]]RTL CONTENT[[/fr]][[/rtl]]", 'div lang="fr-ca"'),
        ],
        ids=[
            "heading_1",
            "heading_2",
            "list_unordered",
            "list_ordered",
            "bold",
            "italic",
            "hr",
            "nested_list",
            "blockquote",
            "link",
            "link_with_text",
            "nested_lang_tags_en",
            "nested_lang_tags_fr",
        ],
    )
    def test_rtl_tags_work_with_other_features(self, content: str, extra_tag: str):
        html = get_html_email_body(content, {})
        assert '<div dir="rtl">' in html
        assert "RTL CONTENT" in html
        assert "<{}".format(extra_tag) in html


class TestCalloutTags:
    def test_callout_tags_in_templates(self):
        content = "[[callout]]\nCallout content\n[[/callout]]"
        html = get_html_email_body(content, {})
        assert "box-shadow: 0 1px 3px #0000000d" in html
        assert "border: 1px solid #edeaea" in html
        assert "Callout content" in html

    @pytest.mark.parametrize(
        "nested_content",
        [
            "[[callout]]\nCallout content\n[[/callout]]\n[[callout]]\nMore callout content\n[[/callout]]",
            "[[callout]]\nCallout content with [[en]]\nEN content\n[[/en]]\n[[/callout]]",
            "[[callout]]\nCallout content with [[rtl]]\nRTL content\n[[/rtl]]\n[[/callout]]",
            "[[rtl]]\n[[callout]]\nCallout in RTL\n[[/callout]]\n[[/rtl]]",
        ],
    )
    def test_callout_tags_in_templates_nested_content(self, nested_content: str):
        html = get_html_email_body(nested_content, {})
        assert "box-shadow: 0 1px 3px #0000000d" in html
        assert "Callout" in html

    @pytest.mark.parametrize(
        "bad_content",
        [
            "[[callout]\nCallout content\n[[/callout]]",  # missing bracket
            "[[CALLOUT]]\nCallout content\n[[/CALLOUT]]",  # tags not lowercase
            "[[callout]]\nCallout content\n",  # tag missing
            "Callout content\n[[/callout]]",  # tag missing
            "((callout))\nCallout content\n((/callout))",  # wrong brackets
        ],
    )
    def test_callout_tags_in_templates_bad_content(self, bad_content: str):
        html = get_html_email_body(bad_content, {})
        assert "box-shadow" not in html

    @pytest.mark.parametrize(
        "mixed_content",
        [
            "[[callout]]\nCallout content\n[[/callout]]\nRegular content",
            "Regular content\n[[callout]]\nCallout content\n[[/callout]]",
        ],
    )
    def test_callout_tags_in_templates_mixed_content(self, mixed_content: str):
        html = get_html_email_body(mixed_content, {})
        assert "box-shadow: 0 1px 3px #0000000d" in html
        assert "Callout content" in html
        assert "Regular content" in html

    @pytest.mark.parametrize(
        "content, extra_tag",
        [
            ("[[callout]]# CALLOUT CONTENT[[/callout]]", "h2"),
            ("[[callout]]## CALLOUT CONTENT[[/callout]]", "h3"),
            ("[[callout]]\n- CALLOUT CONTENT 1\n- item 2\n[[/callout]]", "ul"),
            ("[[callout]]\n1. CALLOUT CONTENT 1\n1. item 2\n[[/callout]]", "ol"),
            ("[[callout]]**CALLOUT CONTENT**[[/callout]]", "strong"),
            ("[[callout]]_CALLOUT CONTENT_[[/callout]]", "em"),
            ("[[callout]]---\nCALLOUT CONTENT[[/callout]]", "hr"),
            ("[[callout]]^CALLOUT CONTENT[[/callout]]", "blockquote"),
            ("[[callout]]CALLOUT CONTENT now at https://www.canada.ca[[/callout]]", "a"),
            ("[[callout]][CALLOUT CONTENT](https://www.canada.ca/sign-in)[[/callout]]", "a"),
            ("[[callout]][[en]]CALLOUT CONTENT[[/en]][[/callout]]", 'div lang="en-ca"'),
            ("[[callout]][[fr]]CALLOUT CONTENT[[/fr]][[/callout]]", 'div lang="fr-ca"'),
            ("[[callout]][[rtl]]CALLOUT CONTENT[[/rtl]][[/callout]]", 'div dir="rtl"'),
        ],
        ids=[
            "heading_1",
            "heading_2",
            "list_unordered",
            "list_ordered",
            "bold",
            "italic",
            "hr",
            "blockquote",
            "link",
            "link_with_text",
            "nested_lang_tags_en",
            "nested_lang_tags_fr",
            "nested_rtl_tags",
        ],
    )
    def test_callout_tags_work_with_other_features(self, content: str, extra_tag: str):
        html = get_html_email_body(content, {})
        assert "box-shadow: 0 1px 3px #0000000d" in html
        assert "CALLOUT CONTENT" in html
        assert "<{}".format(extra_tag) in html


class TestCTATags:
    def test_cta_with_single_link(self):
        content = "[[cta]][Sign up now](https://example.com)[[/cta]]"
        html = get_html_email_body(content, {})
        assert "background: #213045" in html
        assert "Sign up now" in html
        assert "https://example.com" in html

    def test_cta_with_no_links_unprocessed(self):
        content = "[[cta]]Click here[[/cta]]"
        html = get_html_email_body(content, {})
        # CTA tags should remain unprocessed (no link inside)
        assert "background: #213045" not in html
        assert "[[cta]]" in html

    def test_cta_with_multiple_links_unprocessed(self):
        content = "[[cta]][Link 1](https://example.com) and [Link 2](https://example.com)[[/cta]]"
        html = get_html_email_body(content, {})
        # CTA tags should remain unprocessed (multiple links)
        assert "background: #213045" not in html
        assert "[[cta]]" in html

    def test_cta_with_link_and_text(self):
        content = "[[cta]]Click **here** to [sign up](https://example.com)[[/cta]]"
        html = get_html_email_body(content, {})
        assert "background: #213045" in html
        assert "<strong>here</strong>" in html
        assert "https://example.com" in html

    def test_multiple_valid_ctas(self):
        content = "[[cta]][First](https://example.com)[[/cta]]\n\n[[cta]][Second](https://example.com)[[/cta]]"
        html = get_html_email_body(content, {})
        # Both should be processed
        assert html.count("background: #213045") == 2

    def test_cta_with_language_tags(self):
        content = "[[cta]][[en]][Sign up](https://example.com)[[/en]][[/cta]]"
        html = get_html_email_body(content, {})
        assert "background: #213045" in html
        assert 'lang="en-ca"' in html
        assert "https://example.com" in html

    def test_cta_with_rtl(self):
        content = "[[cta]][[rtl]][Click](https://example.com)[[/rtl]][[/cta]]"
        html = get_html_email_body(content, {})
        assert "background: #213045" in html
        assert 'dir="rtl"' in html

    def test_cta_inside_callout(self):
        content = "[[callout]]\n[[cta]][Learn more](https://example.com)[[/cta]]\n[[/callout]]"
        html = get_html_email_body(content, {})
        assert "box-shadow" in html  # callout styling
        assert "background: #213045" in html  # CTA styling

    @pytest.mark.parametrize(
        "bad_content",
        [
            "[[cta]\n[Link](https://example.com)\n[[/cta]]",  # missing bracket
            "[[CTA]][Link](https://example.com)[[/CTA]]",  # tags not lowercase
            "[[cta]][Link](https://example.com)\n",  # tag missing
            "[Link](https://example.com)\n[[/cta]]",  # tag missing
            "((cta))[Link](https://example.com)((/cta))",  # wrong brackets
        ],
    )
    def test_cta_malformed_tags_unprocessed(self, bad_content: str):
        html = get_html_email_body(bad_content, {})
        # Malformed tags should not be processed
        assert "background: #213045" not in html
