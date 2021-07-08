import pytest

from functools import partial
from notifications_utils.columns import Columns, Row, Cell


def test_columns_as_dict_with_keys():
    assert Columns({"Date of Birth": "01/01/2001", "TOWN": "Toronto"}).as_dict_with_keys({"date_of_birth", "town"}) == {
        "date_of_birth": "01/01/2001",
        "town": "Toronto",
    }


def test_columns_as_dict():
    assert dict(Columns({"date of birth": "01/01/2001", "TOWN": "Toronto"})) == {"dateofbirth": "01/01/2001", "town": "Toronto"}


def test_missing_data():
    partial_row = partial(
        Row,
        row_dict={},
        index=1,
        error_fn=None,
        recipient_column_headers=[],
        placeholders=[],
        template=None,
    )
    assert Columns({})["foo"] is None
    assert Columns({}).get("foo") is None
    assert Columns({}).get("foo", "bar") == "bar"
    assert partial_row()["foo"] == Cell()
    assert partial_row().get("foo") == Cell()
    assert partial_row().get("foo", "bar") == "bar"


@pytest.mark.parametrize(
    "in_dictionary",
    [
        {"foo": "bar"},
        {"F_O O": "bar"},
    ],
)
@pytest.mark.parametrize(
    "key, should_be_present",
    [
        ("foo", True),
        ("f_o_o", True),
        ("F O O", True),
        ("bar", False),
    ],
)
def test_lookup(key, should_be_present, in_dictionary):
    assert (key in Columns(in_dictionary)) == should_be_present
