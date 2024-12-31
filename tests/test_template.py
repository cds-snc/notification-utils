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
    def test_variable(self):
        template_content = "((variable))"
        expected_rendered_markdown = "((variable))"
        html = BeautifulSoup(str(get_html_email_body(template_content, {})), "html.parser")
        rendered_markdown = html.get_text()
        assert rendered_markdown == expected_rendered_markdown

    def test_link_text_with_variable(self):
        template_content = "[link text with ((variable))](https://developer.mozilla.org/en-US/)"
        html = BeautifulSoup(str(get_html_email_body(template_content, {})), "html.parser")
        href = html.select("a")[0].get_attribute_list("href")[0]
        link_text = html.select("a")[0].get_text()
        assert href == "https://developer.mozilla.org/en-US/"
        assert link_text == "link text with ((variable))"

    def test_link_with_query_param(self):
        template_content = "[link with query param](https://developer.mozilla.org/en-US/search?q=asdf)"
        html = BeautifulSoup(str(get_html_email_body(template_content, {})), "html.parser")
        href = html.select("a")[0].get_attribute_list("href")[0]
        link_text = html.select("a")[0].get_text()
        assert href == "https://developer.mozilla.org/en-US/search?q=asdf"
        assert link_text == "link with query param"

    def test_link_with_var_as_url(self):
        # failing
        template_content = "[link with variable as url](((url_var)))"
        html = BeautifulSoup(str(get_html_email_body(template_content, {})), "html.parser")
        href = html.select("a")[0].get_attribute_list("href")[0]
        link_text = html.select("a")[0].get_text()
        print(html)
        assert link_text == "link with variable as url"
        assert href == "url_var"

    def test_link_with_var_in_url(self):
        # failing
        template_content = "[link with variable in url](((url_var))/en-US/)"
        html = BeautifulSoup(str(get_html_email_body(template_content, {})), "html.parser")
        href = html.select("a")[0].get_attribute_list("href")[0]
        link_text = html.select("a")[0].get_text()
        print(html)
        assert link_text == "link with variable in url"
        assert href == "url_var/en-US/"

    def test_link_with_var_and_query_param(self):
        # failing
        template_content = "[link with variable and query param](((url_var))/en-US/search?q=asdf)"
        html = BeautifulSoup(str(get_html_email_body(template_content, {})), "html.parser")
        href = html.select("a")[0].get_attribute_list("href")[0]
        link_text = html.select("a")[0].get_text()
        print(html)
        assert link_text == "link with variable and query param"
        assert href == "url_var/en-US/search?q=asdf"


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
