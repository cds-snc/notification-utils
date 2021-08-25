import pytest

from notifications_utils.validate_html import check_if_string_contains_valid_html


@pytest.mark.parametrize(
    "good_content",
    (
        "<div>abc</div>",
        '<div style="xyz">abc</div>',
        """<div style="margin: 20px auto 30px auto;">
  <img
    src="http://google.com"
    alt="alt text"
    height="10"
    width="10"
  />
</div>""",
        "abc<div>abc</div>xyz",
    ),
)
def test_good_content_is_valid(good_content: str):
    assert check_if_string_contains_valid_html(good_content) == []


@pytest.mark.parametrize(
    "bad_content", ("<div>abc<div>", '<img src="http://google.com">', "abc<div>abc<div>xyz", '<div style=">abc</div>')
)
def test_bad_content_is_invalid(bad_content: str):
    assert check_if_string_contains_valid_html(bad_content) != []
