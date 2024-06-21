from typing import Any, Dict

import pytest
from notifications_utils.field import Field, str2bool


@pytest.mark.parametrize(
    "content",
    [
        "",
        "the quick brown fox",
        """
        the
        quick brown

        fox
    """,
        "the ((quick brown fox",
        "the (()) brown fox",
    ],
)
def test_returns_a_string_without_placeholders(content):
    assert str(Field(content)) == content


@pytest.mark.parametrize(
    "template_content,data,expected",
    [
        ("((colour))", {"colour": "red"}, "red"),
        ("the quick ((colour)) fox", {"colour": "brown"}, "the quick brown fox"),
        (
            "((article)) quick ((colour)) ((animal))",
            {"article": "the", "colour": "brown", "animal": "fox"},
            "the quick brown fox",
        ),
        ("the quick (((colour))) fox", {"colour": "brown"}, "the quick (brown) fox"),
        ("the quick ((colour)) fox", {"colour": "<script>alert('foo')</script>"}, "the quick alert('foo') fox"),
        (
            "before ((placeholder)) after",
            {"placeholder": True},
            "before True after",
        ),
        (
            "before ((placeholder)) after",
            {"placeholder": False},
            "before False after",
        ),
        (
            "before ((placeholder)) after",
            {"placeholder": 0},
            "before 0 after",
        ),
        (
            "before ((placeholder)) after",
            {"placeholder": 0.0},
            "before 0.0 after",
        ),
        (
            "before ((placeholder)) after",
            {"placeholder": 123},
            "before 123 after",
        ),
        (
            "before ((placeholder)) after",
            {"placeholder": 0.1 + 0.2},
            "before 0.30000000000000004 after",
        ),
        (
            "before ((placeholder)) after",
            {"placeholder": {"key": "value"}},
            "before {'key': 'value'} after",
        ),
        ("((warning?))", {"warning?": "This is not a conditional"}, "This is not a conditional"),
        ("((warning?warning))", {"warning?warning": "This is not a conditional"}, "This is not a conditional"),
        ("((warning??This is a conditional warning))", {"warning": True}, "This is a conditional warning"),
        ("((warning??This is a conditional warning))", {"warning": False}, ""),
        ("((alert??Its up (yes)))", {"alert": True}, "Its up (yes)"),
        ("((ifvar?? (5) ))", {"ifvar": False}, ""),
    ],
)
def test_replacement_of_placeholders(template_content: str, data: Dict[str, Any], expected: str):
    assert str(Field(template_content, data)) == expected


@pytest.mark.parametrize(
    "template_content,data,expected",
    [
        ("((code)) is your security code", {"code": "12345"}, "12345 is your security code"),
        ("((code)) is your security code", {}, "<mark class='placeholder-redacted'>[hidden]</mark> is your security code"),
        (
            "Hey ((name)), click http://example.com/reset-password/?token=((token))",
            {"name": "Example"},
            (
                "Hey Example, click "
                "http://example.com/reset-password/?token="
                "<mark class='placeholder-redacted'>[hidden]</mark>"
            ),
        ),
    ],
)
def test_optional_redacting_of_missing_values(template_content, data, expected):
    assert str(Field(template_content, data, redact_missing_personalisation=True)) == expected


@pytest.mark.parametrize(
    "content,expected",
    [
        ("((colour))", "<mark class='placeholder'>((colour))</mark>"),
        ("the quick ((colour)) fox", "the quick <mark class='placeholder'>((colour))</mark> fox"),
        (
            "((article)) quick ((colour)) ((animal))",
            "<mark class='placeholder'>((article))</mark> quick "
            "<mark class='placeholder'>((colour))</mark> <mark class='placeholder'>((animal))</mark>",
        ),
        (
            """
                ((article)) quick
                ((colour))
                ((animal))
            """,
            """
                <mark class='placeholder'>((article))</mark> quick
                <mark class='placeholder'>((colour))</mark>
                <mark class='placeholder'>((animal))</mark>
            """,
        ),
        ("the quick (((colour))) fox", "the quick (<mark class='placeholder'>((colour))</mark>) fox"),
        ("((warning?))", "<mark class='placeholder'>((warning?))</mark>"),
        ("((warning? This is not a conditional))", "<mark class='placeholder'>((warning? This is not a conditional))</mark>"),
        (
            "((warning?? This is a warning))",
            "<mark class='placeholder-conditional'><span class='condition'>((warning??</span> This is a warning))</mark>",
        ),
        (
            "((alert??With both (parenthesis) ))",
            "<mark class='placeholder-conditional'><span class='condition'>((alert??</span>With both (parenthesis) ))</mark>",
        ),
        (
            "((alert??Missing (right parenthesis ))",
            "<mark class='placeholder-conditional'><span class='condition'>((alert??</span>Missing (right parenthesis ))</mark>",
        ),
        (
            "((alert??Missing left parenthesis) ))",
            "<mark class='placeholder-conditional'><span class='condition'>((alert??</span>Missing left parenthesis) ))</mark>",
        ),
        (
            "((warning?)) and ((alert?? alert!))",
            "<mark class='placeholder'>((warning?))</mark> and "
            "<mark class='placeholder-conditional'><span class='condition'>((alert??</span> alert!))</mark>",
        ),
        (
            "(((warning))) and ((alert?? alert!))",
            "(<mark class='placeholder'>((warning))</mark>) and "
            "<mark class='placeholder-conditional'><span class='condition'>((alert??</span> alert!))</mark>",
        ),
    ],
)
def test_formatting_of_placeholders(content, expected):
    assert str(Field(content)) == expected


@pytest.mark.parametrize(
    "content,expected,translated,values",
    [
        ("((colour))", "<mark class='placeholder'>((colour))</mark>", False, None),
        ("((colour))", "<span class='placeholder-no-brackets'>[colour]</span>", True, None),
        ("((colour))", "blue", False, {"colour": "blue"}),
        ("((colour))", "blue", True, {"colour": "blue"}),
    ],
)
def test_formatting_of_placeholders_translated(content, expected, translated, values):
    field = Field(content, translated=translated, values=values)
    assert str(field) == expected


@pytest.mark.parametrize(
    "content, values, expected",
    [
        (
            "((name)) ((colour))",
            {"name": "Jo"},
            "Jo <mark class='placeholder'>((colour))</mark>",
        ),
        (
            "((name)) ((colour))",
            {"name": "Jo", "colour": None},
            "Jo <mark class='placeholder'>((colour))</mark>",
        ),
        (
            "((show_thing??thing)) ((colour))",
            {"colour": "red"},
            "<mark class='placeholder-conditional'><span class='condition'>((show_thing??</span>thing))</mark> red",
        ),
    ],
)
def test_handling_of_missing_values(content, values, expected):
    assert str(Field(content, values)) == expected


@pytest.mark.parametrize(
    "value",
    [
        "0",
        0,
        2,
        99.99999,
        "off",
        "exclude",
        "no" "any random string",
        "false",
        False,
        [],
        {},
        (),
        ["true"],
        {"True": True},
        (True, "true", 1),
    ],
)
def test_what_will_not_trigger_conditional_placeholder(value):
    assert str2bool(value) is False


@pytest.mark.parametrize("value", [1, "1", "yes", "y", "true", "True", True, "include", "show"])
def test_what_will_trigger_conditional_placeholder(value):
    assert str2bool(value) is True


@pytest.mark.parametrize(
    "values, expected, expected_as_markdown",
    [
        (
            {"placeholder": []},
            "list: <mark class='placeholder'>((placeholder))</mark>",
            "list: <mark class='placeholder'>((placeholder))</mark>",
        ),
        (
            {"placeholder": ["", ""]},
            "list: <mark class='placeholder'>((placeholder))</mark>",
            "list: <mark class='placeholder'>((placeholder))</mark>",
        ),
        (
            {"placeholder": ["one"]},
            "list: one",
            "list: \n\n* one",
        ),
        (
            {"placeholder": ["one", "two"]},
            "list: one and two",
            "list: \n\n* one\n* two",
        ),
        (
            {"placeholder": ["one", "two", "three"]},
            "list: one, two and three",
            "list: \n\n* one\n* two\n* three",
        ),
        (
            {"placeholder": ["one", None, None]},
            "list: one",
            "list: \n\n* one",
        ),
        (
            {"placeholder": ["<script>", 'alert("foo")', "</script>"]},
            'list: , alert("foo") and ',
            'list: \n\n* \n* alert("foo")\n* ',
        ),
        (
            {"placeholder": [1, {"two": 2}, "three", None]},
            "list: 1, {'two': 2} and three",
            "list: \n\n* 1\n* {'two': 2}\n* three",
        ),
        (
            {"placeholder": [[1, 2], [3, 4]]},
            "list: [1, 2] and [3, 4]",
            "list: \n\n* [1, 2]\n* [3, 4]",
        ),
    ],
)
def test_field_renders_lists_as_strings(values, expected, expected_as_markdown):
    assert str(Field("list: ((placeholder))", values, markdown_lists=True)) == expected_as_markdown
    assert str(Field("list: ((placeholder))", values)) == expected


@pytest.mark.parametrize(
    "template_str, result",
    [
        ("Lorem ipsum ((var))", False),
        ("Lorem ipsum ((var??Conditional text))", True),
        ("Lorem ipsum ((var)) Lorem ipsum ((var??Conditional text)) Lorem ipsum ((var))", True),
        ("Lorem ipsum ((var)) Lorem ipsum ((var))", False),
        ("Lorem ipsum ((var??Conditional text))", True),
        ("Lorem ipsum ((var??Conditional text)) ((other_var))", True),
        ("Lorem ipsum ((var)) Lorem ipsum ((var??Conditional text))", True),
        ("Lorem ipsum ((var??Conditional text)) Lorem ipsum ((var))", True),
    ],
)
def test_placeholder_meta(template_str: str, result: bool):
    assert Field(template_str).placeholders_meta["var"]["is_conditional"] == result
