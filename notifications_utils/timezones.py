import os

import pytz
from dateutil import parser

local_timezone = pytz.timezone(os.getenv("TIMEZONE", "America/Toronto"))


def utc_string_to_aware_gmt_datetime(date):
    date = parser.parse(date)
    forced_utc = date.replace(tzinfo=pytz.utc)
    return forced_utc.astimezone(local_timezone)


def convert_utc_to_est(utc_dt):
    return pytz.utc.localize(utc_dt).astimezone(local_timezone).replace(tzinfo=None)


def convert_est_to_utc(date):
    return local_timezone.localize(date).astimezone(pytz.UTC).replace(tzinfo=None)


def convert_utc_to_local_timezone(utc_dt, timezone=local_timezone):
    return pytz.utc.localize(utc_dt).astimezone(timezone).replace(tzinfo=None)


def convert_local_timezone_to_utc(date, timezone=local_timezone):
    return timezone.localize(date).astimezone(pytz.UTC).replace(tzinfo=None)
