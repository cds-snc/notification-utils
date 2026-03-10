import csv
import io
from importlib.resources import files
from unittest.mock import patch

import pytest
from notifications_utils.template import SMSMessageTemplate, SMSPreviewTemplate, Template, WithSubjectTemplate, is_unicode


def test_class():
    assert repr(Template({"content": "hello ((name))"})) == 'Template("hello ((name))", {})'


def test_passes_through_template_attributes():
    assert Template({"content": ""}).name is None
    assert Template({"content": "", "name": "Two week reminder"}).name == "Two week reminder"
    assert Template({"content": ""}).id is None
    assert Template({"content": "", "id": "1234"}).id == "1234"
    assert Template({"content": ""}).template_type is None
    assert Template({"content": "", "template_type": "sms"}).template_type == "sms"
    assert not hasattr(Template({"content": ""}), "subject")


def test_errors_for_missing_template_content():
    with pytest.raises(KeyError):
        Template({})


@pytest.mark.parametrize("template", [0, 1, 2, True, False, None])
def test_errors_for_invalid_template_types(template):
    with pytest.raises(TypeError):
        Template(template)


@pytest.mark.parametrize("values", [[], False])
def test_errors_for_invalid_values(values):
    with pytest.raises(TypeError):
        Template({"content": ""}, values)


def test_matches_keys_to_placeholder_names():
    template = Template({"content": "hello ((name))"})

    template.values = {"NAME": "Chris"}
    assert template.values == {"name": "Chris"}

    template.values = {"NAME": "Chris", "Town": "Toronto"}
    assert template.values == {"name": "Chris", "Town": "Toronto"}
    assert template.additional_data == {"Town"}

    template.values = None
    assert template.missing_data == ["name"]


@pytest.mark.parametrize(
    "template_content, template_subject, expected",
    [
        ("the quick brown fox", "jumps", []),
        ("the quick ((colour)) fox", "jumps", ["colour"]),
        ("the quick ((colour)) ((animal))", "jumps", ["colour", "animal"]),
        ("((colour)) ((animal)) ((colour)) ((animal))", "jumps", ["colour", "animal"]),
        ("the quick brown fox", "((colour))", ["colour"]),
        ("the quick ((colour)) ", "((animal))", ["animal", "colour"]),
        ("((colour)) ((animal)) ", "((colour)) ((animal))", ["colour", "animal"]),
        ("Dear ((name)), ((warning?? This is a warning))", "", ["name", "warning"]),
        ("((warning? one question mark))", "", ["warning? one question mark"]),
    ],
)
def test_extracting_placeholders(template_content, template_subject, expected):
    assert WithSubjectTemplate({"content": template_content, "subject": template_subject}).placeholders == expected


@pytest.mark.parametrize("template_cls", [SMSMessageTemplate, SMSPreviewTemplate])
@pytest.mark.parametrize(
    "content,prefix, expected_length, expected_replaced_length",
    [
        ("The quick brown fox jumped over the lazy dog", None, 44, 44),
        # should be replaced with a ?
        ("深", None, 1, 1),
        ("'First line.\n", None, 12, 12),
        ("\t\n\r", None, 0, 0),
        ("((placeholder))", None, 15, 3),
        ("((placeholder))", "Service name", 29, 17),
        ("Foo", "((placeholder))", 20, 20),  # placeholder doesn’t work in service name
    ],
)
def test_get_character_count_of_content(content, prefix, template_cls, expected_length, expected_replaced_length):
    template = template_cls(
        {"content": content},
    )
    template.prefix = prefix
    template.sender = None
    assert template.content_count == expected_length
    template.values = {"placeholder": "123"}
    assert template.content_count == expected_replaced_length


def _load_sms_fragment_test_cases():
    csv_file = files("notifications_utils").joinpath("sms_fragment_count_cases.csv")
    with io.StringIO(csv_file.read_text()) as f:
        return [(row["sms_content"], int(row["expected_fragments"])) for row in csv.DictReader(f)]


@pytest.mark.parametrize("sms_content, expected_fragments", _load_sms_fragment_test_cases())
def test_sms_fragment_count(sms_content, expected_fragments):
    template = SMSMessageTemplate({"content": sms_content, "template_type": "sms"})
    assert template.fragment_count == expected_fragments


@pytest.mark.parametrize(
    "content, expected",
    [
        # Pure GSM content — not unicode
        ("Hello world", False),
        # Welsh characters — detected before and after fix
        ("ŵ", True),
        ("This is â Welsh message", True),
        # French non-GSM characters not in Welsh set — only detected after fix
        ("À", True),
        ("ç", True),
        ("Œ", True),
        ("Message en français: À noël", True),
        # Inuktituk characters — only detected after fix
        ("ᐁ", True),
        # Cree characters — only detected after fix
        ("ᐊ", True),
    ],
)
def test_is_unicode(content, expected):
    assert bool(is_unicode(content)) == expected


@pytest.mark.parametrize(
    "content, expected_count",
    [
        # Multibyte UTF-8 characters must be counted as one character each,
        # not by byte length. Old code used .encode('utf-8') which inflated counts.
        ("â", 1),  # Welsh: U+00E2 = 2 bytes in UTF-8, but 1 SMS character
        ("ŵ", 1),  # Welsh: U+0175 = 2 bytes in UTF-8, but 1 SMS character
        ("âê", 2),  # Two Welsh chars: 4 bytes but 2 SMS characters
        ("À", 1),  # French: U+00C0 = 2 bytes in UTF-8, but 1 SMS character
        ("ç", 1),  # French: U+00E7 = 2 bytes in UTF-8, but 1 SMS character
    ],
)
def test_content_count_uses_character_count_not_byte_count(content, expected_count):
    template = SMSMessageTemplate({"content": content, "template_type": "sms"})
    assert template.content_count == expected_count


@pytest.mark.parametrize(
    "content, expected_fragments",
    [
        # 70 French non-GSM chars (unicode mode): exactly 1 fragment (≤70 chars)
        ("À" * 70, 1),
        # 71 French non-GSM chars (unicode mode): 2 fragments (ceil(71/67) = 2)
        ("À" * 71, 2),
        # 134 French non-GSM chars (unicode mode): 2 fragments (ceil(134/67) = 2)
        ("À" * 134, 2),
        # 135 French non-GSM chars (unicode mode): 3 fragments (ceil(135/67) = 3)
        ("À" * 135, 3),
    ],
)
def test_sms_fragment_count_french_uses_unicode_encoding(content, expected_fragments):
    # French non-GSM characters (e.g. "À") were not detected by is_unicode() before the fix.
    # They should trigger unicode fragment counting rules (70/67 chars), not GSM (160/153).
    template = SMSMessageTemplate({"content": content, "template_type": "sms"})
    assert template.fragment_count == expected_fragments


def test_random_variable_retrieve():
    template = Template({"content": "content", "template_type": "sms", "created_by": "now"})
    assert template.get_raw("created_by") == "now"
    assert template.get_raw("missing", default="random") == "random"
    assert template.get_raw("missing") is None


def test_compare_template():
    with patch("notifications_utils.template_change.TemplateChange.__init__", return_value=None) as mocked:
        old_template = Template({"content": "faked", "template_type": "sms"})
        new_template = Template({"content": "faked", "template_type": "sms"})
        old_template.compare_to(new_template)
        mocked.assert_called_once_with(old_template, new_template)
