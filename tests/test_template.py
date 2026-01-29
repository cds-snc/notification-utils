import pytest
from bs4 import BeautifulSoup
from notifications_utils.template import SMSMessageTemplate, get_html_email_body


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


class TestTemplateParts:
    def test_message_parts_basic(self):
        template = {"content": "Hello world", "template_type": "sms"}
        sms = SMSMessageTemplate(template)
        parts = sms.message_parts()

        assert parts["character_count"] == 11
        assert parts["fragment_count"] == 1
        assert parts["unicode"] == set()  # Empty set for non-unicode

    def test_message_parts_with_unicode(self):
        # Welsh character 'â' triggers unicode ('â' is 2 bytes in UTF-8)
        template = {"content": "Helo byd â", "template_type": "sms"}
        sms = SMSMessageTemplate(template)
        parts = sms.message_parts()

        assert parts["character_count"] == 11  # "Helo byd " (9 bytes) + "â" (2 bytes) = 11 total bytes
        assert parts["fragment_count"] == 1
        assert parts["unicode"] == {"â"}  # Set containing unicode char

    def test_message_parts_long_non_unicode_single_fragment(self):
        # 160 bytes is the limit for single non-unicode SMS
        template = {"content": "a" * 160, "template_type": "sms"}
        sms = SMSMessageTemplate(template)
        parts = sms.message_parts()

        assert parts["character_count"] == 160
        assert parts["fragment_count"] == 1
        assert parts["unicode"] == set()  # Empty set for non-unicode

    def test_message_parts_long_non_unicode_multiple_fragments(self):
        # 161 bytes triggers multi-part SMS (153 bytes per fragment)
        template = {"content": "a" * 161, "template_type": "sms"}
        sms = SMSMessageTemplate(template)
        parts = sms.message_parts()

        assert parts["character_count"] == 161
        assert parts["fragment_count"] == 2
        assert parts["unicode"] == set()  # Empty set for non-unicode

    def test_message_parts_long_unicode_single_fragment(self):
        # 70 bytes is the limit for single unicode SMS ('â' is 2 bytes each)
        template = {"content": "â" * 35, "template_type": "sms"}
        sms = SMSMessageTemplate(template)
        parts = sms.message_parts()

        assert parts["character_count"] == 70  # 35 chars * 2 bytes each
        assert parts["fragment_count"] == 1
        assert parts["unicode"] == {"â"}  # Set containing unicode char

    def test_message_parts_long_unicode_multiple_fragments(self):
        # 71 bytes triggers multi-part unicode SMS (67 bytes per fragment)
        template = {"content": "â" * 36, "template_type": "sms"}
        sms = SMSMessageTemplate(template)
        parts = sms.message_parts()

        assert parts["character_count"] == 72  # 36 chars * 2 bytes each
        assert parts["fragment_count"] == 2
        assert parts["unicode"] == {"â"}  # Set containing unicode char

    def test_message_parts_with_placeholders(self):
        template = {"content": "Hello ((name))", "template_type": "sms"}
        sms = SMSMessageTemplate(template, values={"name": "Alice"})
        parts = sms.message_parts()

        assert parts["character_count"] == 11  # "Hello Alice"
        assert parts["fragment_count"] == 1
        assert parts["unicode"] == set()  # Empty set for non-unicode

    def test_message_parts_with_unicode_placeholder(self):
        template = {"content": "Hello ((name))", "template_type": "sms"}
        sms = SMSMessageTemplate(template, values={"name": "Siân"})
        parts = sms.message_parts()

        assert parts["character_count"] == 11  # "Hello Siân" (â is 2 bytes)
        assert parts["fragment_count"] == 1
        assert parts["unicode"] == {"â"}  # Set containing unicode char

    def test_message_parts_with_prefix(self):
        template = {"content": "Hello world", "template_type": "sms"}
        sms = SMSMessageTemplate(template, prefix="Service")
        parts = sms.message_parts()

        # "Service: Hello world" = 20 bytes
        assert parts["character_count"] == 20
        assert parts["fragment_count"] == 1
        assert parts["unicode"] == set()  # Empty set for non-unicode

    def test_message_parts_with_prefix_hidden(self):
        template = {"content": "Hello world", "template_type": "sms"}
        sms = SMSMessageTemplate(template, prefix="Service", show_prefix=False)
        parts = sms.message_parts()

        # Prefix not shown, so just "Hello world" = 11 bytes
        assert parts["character_count"] == 11
        assert parts["fragment_count"] == 1
        assert parts["unicode"] == set()  # Empty set for non-unicode

    @pytest.mark.parametrize(
        "content, byte_count, fragment_count, has_unicode",
        [
            # Non-unicode: single fragment up to 160 bytes, then 153 bytes per fragment
            ("a" * 160, 160, 1, False),
            ("a" * 161, 161, 2, False),
            ("a" * 306, 306, 2, False),
            ("a" * 307, 307, 3, False),
            # Unicode: single fragment up to 70 bytes, then 67 bytes per fragment
            # 'â' is 2 bytes in UTF-8
            ("â" * 35, 70, 1, True),  # 35 chars * 2 = 70 bytes
            ("â" * 36, 72, 2, True),  # 36 chars * 2 = 72 bytes (>70)
            ("â" * 67, 134, 2, True),  # 67 chars * 2 = 134 bytes
            ("â" * 68, 136, 3, True),  # 68 chars * 2 = 136 bytes (>134)
        ],
    )
    def test_message_parts_fragment_boundaries(self, content, byte_count, fragment_count, has_unicode):
        template = {"content": content, "template_type": "sms"}
        sms = SMSMessageTemplate(template)
        parts = sms.message_parts()

        assert parts["character_count"] == byte_count
        assert parts["fragment_count"] == fragment_count
        # Check if unicode set is empty or not
        assert bool(parts["unicode"]) == has_unicode

    def test_message_parts_with_multiple_unicode_chars_near_250_bytes(self):
        # Test with 4 different French non-GSM unicode characters (each 2 bytes in UTF-8)
        # Using: â, ê, î, ô from FRENCH_NON_GSM_CHARACTERS
        # Unicode SMS fragments: 70 bytes for single, then 67 bytes per fragment
        # 4 fragments can hold up to 268 bytes (70 for first would be single, but 71+ triggers multi-part at 67 each)
        # Boundary: 201 bytes = 3 fragments, 202 bytes = 4 fragments

        # Create content with mix of 4 French non-GSM unicode characters: â, ê, î, ô
        # Each is 2 bytes, so we need 100 chars total = 200 bytes (just under boundary)
        content_200_bytes = "âêîô" * 25  # 4 chars * 25 = 100 chars * 2 bytes = 200 bytes
        template = {"content": content_200_bytes, "template_type": "sms"}
        sms = SMSMessageTemplate(template)
        parts = sms.message_parts()

        assert parts["character_count"] == 200
        assert parts["fragment_count"] == 3  # 200 bytes = 3 fragments (67*2 = 134, need 3rd for remaining 66)
        assert len(parts["unicode"]) == 4  # 4 different non-GSM chars

        # Now add one more unicode char to cross the boundary to 202 bytes
        content_202_bytes = content_200_bytes + "â"  # +2 bytes = 202 bytes total
        template = {"content": content_202_bytes, "template_type": "sms"}
        sms = SMSMessageTemplate(template)
        parts = sms.message_parts()

        assert parts["character_count"] == 202
        assert parts["fragment_count"] == 4  # 202 bytes crosses boundary, needs 4 fragments
        assert len(parts["unicode"]) == 4  # Still 4 different non-GSM chars

        # Test at exactly 250 bytes (still in 4-fragment range: 202-268 bytes)
        # Need 125 chars * 2 bytes = 250 bytes
        # Adjust: 124 chars = 248 bytes, 125 chars = 250 bytes
        content_250_bytes = "âêîô" * 31 + "â"  # (4*31 + 1) = 125 chars * 2 bytes = 250 bytes
        template = {"content": content_250_bytes, "template_type": "sms"}
        sms = SMSMessageTemplate(template)
        parts = sms.message_parts()

        assert parts["character_count"] == 250
        assert parts["fragment_count"] == 4  # 250 bytes = 4 fragments
        assert len(parts["unicode"]) == 4  # 4 different non-GSM chars

    def test_message_parts_with_multiple_unicode_chars(self):
        # Real-world bilingual emergency test message with French accented characters
        content = (
            "NB- xxxxxxxx, 120 xxxxxxxxxxx Blvd: This is a test for the xxxxxxxx employees, "
            "and no action is required from you at this time. The purpose of this exercise is "
            "to ensure that our emergency communication system is functioning properly and that "
            "everyone is familiar with the process.\n"
            "Ceci est uniquement un test pour les employés xx xxxxxxxx et aucune action n'est "
            "requise de votre part pour le moment. L'objectif de cet exercice est de s'assurer "
            "que notre système de communication d'urgence fonctionne correctement et que chacun "
            "connaît la procédure."
        )

        template = {"content": content, "template_type": "sms"}
        sms = SMSMessageTemplate(template)
        parts = sms.message_parts()

        # Verify it's detected as unicode (has French accented characters)
        assert len(parts["unicode"]) > 0

        # Content is large enough to require multiple SMS fragments
        # With unicode, fragments are: first 70 bytes, then 67 bytes each
        assert parts["character_count"] > 500  # Should be around 580+ bytes
        assert parts["fragment_count"] == 9

        # Verify specific unicode characters from French text
        french_unicode_chars = {"î"}
        assert french_unicode_chars.issubset(parts["unicode"])
