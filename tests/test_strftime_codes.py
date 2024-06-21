from unittest.mock import MagicMock, patch

from notifications_utils.strftime_codes import no_pad_code, no_pad_day, no_pad_hour12, no_pad_hour24, no_pad_month

LINUX = "linux"
WINDOWS = "windows"
GET_SYSTEM = "notifications_utils.strftime_codes._get_system"


def test_posix_no_pad_code():
    with patch(GET_SYSTEM, MagicMock(return_value=LINUX)):
        code = no_pad_code("d")
        assert code == "%-d"


def test_win_no_pad_code():
    with patch(GET_SYSTEM, MagicMock(return_value=WINDOWS)):
        code = no_pad_code("d")
        assert code == "%#d"


def test_posix_no_pad_day():
    with patch(GET_SYSTEM, MagicMock(return_value=LINUX)):
        code = no_pad_day()
        assert code == "%-d"


def test_win_no_pad_day():
    with patch(GET_SYSTEM, MagicMock(return_value=WINDOWS)):
        code = no_pad_day()
        assert code == "%#d"


def test_posix_no_pad_hour12():
    with patch(GET_SYSTEM, MagicMock(return_value=LINUX)):
        code = no_pad_hour12()
        assert code == "%-I"


def test_win_no_pad_hour12():
    with patch(GET_SYSTEM, MagicMock(return_value=WINDOWS)):
        code = no_pad_hour12()
        assert code == "%#I"


def test_posix_no_pad_hour24():
    with patch(GET_SYSTEM, MagicMock(return_value=LINUX)):
        code = no_pad_hour24()
        assert code == "%-H"


def test_win_no_pad_hour24():
    with patch(GET_SYSTEM, MagicMock(return_value=WINDOWS)):
        code = no_pad_hour24()
        assert code == "%#H"


def test_posix_no_pad_month():
    with patch(GET_SYSTEM, MagicMock(return_value=LINUX)):
        code = no_pad_month()
        assert code == "%-m"


def test_win_no_pad_month():
    with patch(GET_SYSTEM, MagicMock(return_value=WINDOWS)):
        code = no_pad_month()
        assert code == "%#m"
