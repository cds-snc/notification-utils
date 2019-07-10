from datetime import datetime

import pytest

from notifications_utils.timezones import convert_est_to_utc, convert_utc_to_est, utc_string_to_aware_gmt_datetime


@pytest.mark.parametrize('input_value', [
    'foo',
    100,
    True,
    False,
    None,
])
def test_utc_string_to_aware_gmt_datetime_rejects_bad_input(input_value):
    with pytest.raises(Exception):
        utc_string_to_aware_gmt_datetime(input_value)


@pytest.mark.parametrize('naive_time, expected_aware_hour', [
    ('2000-12-1 20:01', '15:01'),
    ('2000-06-1 20:01', '16:01'),
])
def test_utc_string_to_aware_gmt_datetime_handles_summer_and_winter(
    naive_time,
    expected_aware_hour,
):
    assert utc_string_to_aware_gmt_datetime(naive_time).strftime('%H:%M') == expected_aware_hour


@pytest.mark.parametrize('date, expected_date', [
    (datetime(2017, 3, 26, 23, 0), datetime(2017, 3, 26, 19, 0)),    # 2017 EST switchover
    (datetime(2017, 3, 20, 23, 0), datetime(2017, 3, 20, 19, 0)),
    (datetime(2017, 3, 28, 10, 0), datetime(2017, 3, 28, 6, 0)),
    (datetime(2017, 10, 28, 1, 0), datetime(2017, 10, 27, 21, 0)),
    (datetime(2017, 10, 29, 1, 0), datetime(2017, 10, 28, 21, 0)),
    (datetime(2017, 5, 12, 14), datetime(2017, 5, 12, 10, 0))
])
def test_get_utc_in_est_returns_expected_date(date, expected_date):
    ret_date = convert_utc_to_est(date)
    assert ret_date == expected_date


def test_convert_est_to_utc():
    est = "2017-05-12 13:15"
    est_datetime = datetime.strptime(est, "%Y-%m-%d %H:%M")
    utc = convert_est_to_utc(est_datetime)
    assert utc == datetime(2017, 5, 12, 17, 15)
