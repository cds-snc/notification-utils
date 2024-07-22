import pytest
import requests
from notifications_utils.system_status import THRESHOLDS, determine_notification_status, determine_site_status


@pytest.mark.parametrize("site, threshold", [("http://site-1.example.com", 400)])
@pytest.mark.parametrize("response_time, expected_status", [(100, "up"), (500, "degraded")])
def test_determine_site_status(mocker, site, threshold, response_time, expected_status):
    # mock the call to check_response_time()
    mocker.patch("notifications_utils.system_status.check_response_time", return_value=response_time)

    result = determine_site_status(site, threshold)

    assert result == expected_status


def test_determine_site_status_down(mocker):
    mocker.patch("notifications_utils.system_status.check_response_time", side_effect=requests.exceptions.ConnectionError)
    result = determine_site_status("http://site-1.example.com", 400)

    assert result == "down"


@pytest.mark.parametrize(
    "email_low, email_medium, email_high, expected_result",
    [
        (THRESHOLDS["email-low"], THRESHOLDS["email-medium"], THRESHOLDS["email-high"], "up"),
        (THRESHOLDS["email-low"], THRESHOLDS["email-medium"], THRESHOLDS["email-high"] + 1, "degraded"),
        (THRESHOLDS["email-low"], THRESHOLDS["email-medium"], -1, "down"),
        (THRESHOLDS["email-low"], THRESHOLDS["email-medium"] + 1, THRESHOLDS["email-high"], "degraded"),
        (THRESHOLDS["email-low"], THRESHOLDS["email-medium"] + 1, THRESHOLDS["email-high"] + 1, "degraded"),
        (THRESHOLDS["email-low"], THRESHOLDS["email-medium"] + 1, -1, "down"),
        (THRESHOLDS["email-low"], -1, THRESHOLDS["email-high"], "down"),
        (THRESHOLDS["email-low"], -1, THRESHOLDS["email-high"] + 1, "down"),
        (THRESHOLDS["email-low"], -1, -1, "down"),
        (THRESHOLDS["email-low"] + 1, THRESHOLDS["email-medium"], THRESHOLDS["email-high"], "degraded"),
        (THRESHOLDS["email-low"] + 1, THRESHOLDS["email-medium"], THRESHOLDS["email-high"] + 1, "degraded"),
        (THRESHOLDS["email-low"] + 1, THRESHOLDS["email-medium"], -1, "down"),
        (THRESHOLDS["email-low"] + 1, THRESHOLDS["email-medium"] + 1, THRESHOLDS["email-high"], "degraded"),
        (THRESHOLDS["email-low"] + 1, THRESHOLDS["email-medium"] + 1, THRESHOLDS["email-high"] + 1, "degraded"),
        (THRESHOLDS["email-low"] + 1, THRESHOLDS["email-medium"] + 1, -1, "down"),
        (THRESHOLDS["email-low"] + 1, -1, THRESHOLDS["email-high"], "down"),
        (THRESHOLDS["email-low"] + 1, -1, THRESHOLDS["email-high"] + 1, "down"),
        (THRESHOLDS["email-low"] + 1, -1, -1, "down"),
        (-1, THRESHOLDS["email-medium"], THRESHOLDS["email-high"], "down"),
        (-1, THRESHOLDS["email-medium"], THRESHOLDS["email-high"] + 1, "down"),
        (-1, THRESHOLDS["email-medium"], -1, "down"),
        (-1, THRESHOLDS["email-medium"] + 1, THRESHOLDS["email-high"], "down"),
        (-1, THRESHOLDS["email-medium"] + 1, THRESHOLDS["email-high"] + 1, "down"),
        (-1, THRESHOLDS["email-medium"] + 1, -1, "down"),
        (-1, -1, THRESHOLDS["email-high"], "down"),
        (-1, -1, THRESHOLDS["email-high"] + 1, "down"),
        (-1, -1, -1, "down"),
    ],
)
def test_determine_notification_status_for_email(mocker, email_low, email_medium, email_high, expected_result):
    notifications_data = [
        ["73079cb9-c169-44ea-8cf4-8d397711cc9d", email_low]
        if email_low != -1
        else [
            "dummy-data",
            0,
        ],  # this just omits a row with the particular id in the case of -1, since there would be no db records
        ["c75c4539-3014-4c4c-96b5-94d326758a74", email_medium] if email_medium != -1 else ["dummy-data", 0],
        ["276da251-3103-49f3-9054-cbf6b5d74411", email_high] if email_high != -1 else ["dummy-data", 0],
        ["ab3a603b-d602-46ea-8c83-e05cb280b950", 1],  # SMS
        ["a48b54ce-40f6-4e4a-abe8-1e2fa389455b", 1],  # SMS    # med sms
        ["4969a9e9-ddfd-476e-8b93-6231e6f1be4a", 1],
    ]

    assert determine_notification_status(notifications_data) == (expected_result, "up")


@pytest.mark.parametrize(
    "sms_low, sms_medium, sms_high, expected_result",
    [
        (THRESHOLDS["sms-low"], THRESHOLDS["sms-medium"], THRESHOLDS["sms-high"], "up"),
        (THRESHOLDS["sms-low"], THRESHOLDS["sms-medium"], THRESHOLDS["sms-high"] + 1, "degraded"),
        (THRESHOLDS["sms-low"], THRESHOLDS["sms-medium"], -1, "down"),
        (THRESHOLDS["sms-low"], THRESHOLDS["sms-medium"] + 1, THRESHOLDS["sms-high"], "degraded"),
        (THRESHOLDS["sms-low"], THRESHOLDS["sms-medium"] + 1, THRESHOLDS["sms-high"] + 1, "degraded"),
        (THRESHOLDS["sms-low"], THRESHOLDS["sms-medium"] + 1, -1, "down"),
        (THRESHOLDS["sms-low"], -1, THRESHOLDS["sms-high"], "down"),
        (THRESHOLDS["sms-low"], -1, THRESHOLDS["sms-high"] + 1, "down"),
        (THRESHOLDS["sms-low"], -1, -1, "down"),
        (THRESHOLDS["sms-low"] + 1, THRESHOLDS["sms-medium"], THRESHOLDS["sms-high"], "degraded"),
        (THRESHOLDS["sms-low"] + 1, THRESHOLDS["sms-medium"], THRESHOLDS["sms-high"] + 1, "degraded"),
        (THRESHOLDS["sms-low"] + 1, THRESHOLDS["sms-medium"], -1, "down"),
        (THRESHOLDS["sms-low"] + 1, THRESHOLDS["sms-medium"] + 1, THRESHOLDS["sms-high"], "degraded"),
        (THRESHOLDS["sms-low"] + 1, THRESHOLDS["sms-medium"] + 1, THRESHOLDS["sms-high"] + 1, "degraded"),
        (THRESHOLDS["sms-low"] + 1, THRESHOLDS["sms-medium"] + 1, -1, "down"),
        (THRESHOLDS["sms-low"] + 1, -1, THRESHOLDS["sms-high"], "down"),
        (THRESHOLDS["sms-low"] + 1, -1, THRESHOLDS["sms-high"] + 1, "down"),
        (THRESHOLDS["sms-low"] + 1, -1, -1, "down"),
        (-1, THRESHOLDS["sms-medium"], THRESHOLDS["sms-high"], "down"),
        (-1, THRESHOLDS["sms-medium"], THRESHOLDS["sms-high"] + 1, "down"),
        (-1, THRESHOLDS["sms-medium"], -1, "down"),
        (-1, THRESHOLDS["sms-medium"] + 1, THRESHOLDS["sms-high"], "down"),
        (-1, THRESHOLDS["sms-medium"] + 1, THRESHOLDS["sms-high"] + 1, "down"),
        (-1, THRESHOLDS["sms-medium"] + 1, -1, "down"),
        (-1, -1, THRESHOLDS["sms-high"], "down"),
        (-1, -1, THRESHOLDS["sms-high"] + 1, "down"),
        (-1, -1, -1, "down"),
    ],
)
def test_determine_notification_status_for_sms(mocker, sms_low, sms_medium, sms_high, expected_result):
    notifications_data = [
        ["73079cb9-c169-44ea-8cf4-8d397711cc9d", 1],
        ["c75c4539-3014-4c4c-96b5-94d326758a74", 1],
        ["276da251-3103-49f3-9054-cbf6b5d74411", 1],
        ["ab3a603b-d602-46ea-8c83-e05cb280b950", sms_low] if sms_low != -1 else ["dummy-data", 0],
        ["a48b54ce-40f6-4e4a-abe8-1e2fa389455b", sms_medium] if sms_medium != -1 else ["dummy-data", 0],
        ["4969a9e9-ddfd-476e-8b93-6231e6f1be4a", sms_high] if sms_high != -1 else ["dummy-data", 0],
    ]

    assert determine_notification_status(notifications_data) == ("up", expected_result)


def test_determine_notification_status_for_email_down_when_no_rows():
    notifications_data = [
        ["73079cb9-c169-44ea-8cf4-8d397711cc9d", THRESHOLDS["email-low"]],
        ["c75c4539-3014-4c4c-96b5-94d326758a74", None],  # no results for email medium
        ["276da251-3103-49f3-9054-cbf6b5d74411", THRESHOLDS["email-high"]],
        ["ab3a603b-d602-46ea-8c83-e05cb280b950", 1],  # SMS
        ["a48b54ce-40f6-4e4a-abe8-1e2fa389455b", 1],  # SMS    # med sms
        ["4969a9e9-ddfd-476e-8b93-6231e6f1be4a", 1],
    ]

    assert determine_notification_status(notifications_data) == ("down", "up")

    notifications_data = [
        ["73079cb9-c169-44ea-8cf4-8d397711cc9d", None],  # no results for email low
        ["c75c4539-3014-4c4c-96b5-94d326758a74", THRESHOLDS["email-medium"]],
        ["276da251-3103-49f3-9054-cbf6b5d74411", THRESHOLDS["email-high"]],
        ["ab3a603b-d602-46ea-8c83-e05cb280b950", 1],  # SMS
        ["a48b54ce-40f6-4e4a-abe8-1e2fa389455b", 1],  # SMS    # med sms
        ["4969a9e9-ddfd-476e-8b93-6231e6f1be4a", 1],
    ]

    assert determine_notification_status(notifications_data) == ("down", "up")

    notifications_data = [
        ["73079cb9-c169-44ea-8cf4-8d397711cc9d", THRESHOLDS["email-low"]],
        ["c75c4539-3014-4c4c-96b5-94d326758a74", THRESHOLDS["email-medium"]],
        ["276da251-3103-49f3-9054-cbf6b5d74411", None],  # no results for email high
        ["ab3a603b-d602-46ea-8c83-e05cb280b950", 1],  # SMS
        ["a48b54ce-40f6-4e4a-abe8-1e2fa389455b", 1],  # SMS    # med sms
        ["4969a9e9-ddfd-476e-8b93-6231e6f1be4a", 1],
    ]

    assert determine_notification_status(notifications_data) == ("down", "up")


@pytest.mark.parametrize(
    "email_low, email_medium, email_high, status, log_expected",
    [
        (THRESHOLDS["email-low"], THRESHOLDS["email-medium"], THRESHOLDS["email-high"], "up", False),
        (THRESHOLDS["email-low"], THRESHOLDS["email-medium"], THRESHOLDS["email-high"] + 1, "degraded", True),
        (THRESHOLDS["email-low"], THRESHOLDS["email-medium"], -1, "down", True),
        (THRESHOLDS["email-low"], THRESHOLDS["email-medium"] + 1, THRESHOLDS["email-high"], "degraded", True),
        (THRESHOLDS["email-low"], THRESHOLDS["email-medium"] + 1, THRESHOLDS["email-high"] + 1, "degraded", True),
        (THRESHOLDS["email-low"], THRESHOLDS["email-medium"] + 1, -1, "down", True),
        (THRESHOLDS["email-low"], -1, THRESHOLDS["email-high"], "down", True),
        (THRESHOLDS["email-low"], -1, THRESHOLDS["email-high"] + 1, "down", True),
        (THRESHOLDS["email-low"], -1, -1, "down", True),
        (THRESHOLDS["email-low"] + 1, THRESHOLDS["email-medium"], THRESHOLDS["email-high"], "degraded", True),
        (THRESHOLDS["email-low"] + 1, THRESHOLDS["email-medium"], THRESHOLDS["email-high"] + 1, "degraded", True),
        (THRESHOLDS["email-low"] + 1, THRESHOLDS["email-medium"], -1, "down", True),
        (THRESHOLDS["email-low"] + 1, THRESHOLDS["email-medium"] + 1, THRESHOLDS["email-high"], "degraded", True),
        (THRESHOLDS["email-low"] + 1, THRESHOLDS["email-medium"] + 1, THRESHOLDS["email-high"] + 1, "degraded", True),
        (THRESHOLDS["email-low"] + 1, THRESHOLDS["email-medium"] + 1, -1, "down", True),
        (THRESHOLDS["email-low"] + 1, -1, THRESHOLDS["email-high"], "down", True),
        (THRESHOLDS["email-low"] + 1, -1, THRESHOLDS["email-high"] + 1, "down", True),
        (THRESHOLDS["email-low"] + 1, -1, -1, "down", True),
        (-1, THRESHOLDS["email-medium"], THRESHOLDS["email-high"], "down", True),
        (-1, THRESHOLDS["email-medium"], THRESHOLDS["email-high"] + 1, "down", True),
        (-1, THRESHOLDS["email-medium"], -1, "down", True),
        (-1, THRESHOLDS["email-medium"] + 1, THRESHOLDS["email-high"], "down", True),
        (-1, THRESHOLDS["email-medium"] + 1, THRESHOLDS["email-high"] + 1, "down", True),
        (-1, THRESHOLDS["email-medium"] + 1, -1, "down", True),
        (-1, -1, THRESHOLDS["email-high"], "down", True),
        (-1, -1, THRESHOLDS["email-high"] + 1, "down", True),
        (-1, -1, -1, "down", True),
    ],
)
def test_logging_determine_notification_status_logs_on_email_degraded_or_down(
    mocker, email_low, email_medium, email_high, status, log_expected, caplog
):
    notifications_data = [
        ["73079cb9-c169-44ea-8cf4-8d397711cc9d", email_low]
        if email_low != -1
        else [
            "dummy-data",
            0,
        ],  # this just omits a row with the particular id in the case of -1, since there would be no db records
        ["c75c4539-3014-4c4c-96b5-94d326758a74", email_medium] if email_medium != -1 else ["dummy-data", 0],
        ["276da251-3103-49f3-9054-cbf6b5d74411", email_high] if email_high != -1 else ["dummy-data", 0],
        ["ab3a603b-d602-46ea-8c83-e05cb280b950", 1],  # SMS
        ["a48b54ce-40f6-4e4a-abe8-1e2fa389455b", 1],  # SMS    # med sms
        ["4969a9e9-ddfd-476e-8b93-6231e6f1be4a", 1],
    ]

    caplog.set_level("INFO")
    determine_notification_status(notifications_data)

    if log_expected:
        assert "[system_status_email]: email is {}".format(status) in caplog.text


@pytest.mark.parametrize(
    "sms_low, sms_medium, sms_high, status, log_expected",
    [
        (THRESHOLDS["sms-low"], THRESHOLDS["sms-medium"], THRESHOLDS["sms-high"], "up", False),
        (THRESHOLDS["sms-low"], THRESHOLDS["sms-medium"], THRESHOLDS["sms-high"] + 1, "degraded", True),
        (THRESHOLDS["sms-low"], THRESHOLDS["sms-medium"], -1, "down", True),
        (THRESHOLDS["sms-low"], THRESHOLDS["sms-medium"] + 1, THRESHOLDS["sms-high"], "degraded", True),
        (THRESHOLDS["sms-low"], THRESHOLDS["sms-medium"] + 1, THRESHOLDS["sms-high"] + 1, "degraded", True),
        (THRESHOLDS["sms-low"], THRESHOLDS["sms-medium"] + 1, -1, "down", True),
        (THRESHOLDS["sms-low"], -1, THRESHOLDS["sms-high"], "down", True),
        (THRESHOLDS["sms-low"], -1, THRESHOLDS["sms-high"] + 1, "down", True),
        (THRESHOLDS["sms-low"], -1, -1, "down", True),
        (THRESHOLDS["sms-low"] + 1, THRESHOLDS["sms-medium"], THRESHOLDS["sms-high"], "degraded", True),
        (THRESHOLDS["sms-low"] + 1, THRESHOLDS["sms-medium"], THRESHOLDS["sms-high"] + 1, "degraded", True),
        (THRESHOLDS["sms-low"] + 1, THRESHOLDS["sms-medium"], -1, "down", True),
        (THRESHOLDS["sms-low"] + 1, THRESHOLDS["sms-medium"] + 1, THRESHOLDS["sms-high"], "degraded", True),
        (THRESHOLDS["sms-low"] + 1, THRESHOLDS["sms-medium"] + 1, THRESHOLDS["sms-high"] + 1, "degraded", True),
        (THRESHOLDS["sms-low"] + 1, THRESHOLDS["sms-medium"] + 1, -1, "down", True),
        (THRESHOLDS["sms-low"] + 1, -1, THRESHOLDS["sms-high"], "down", True),
        (THRESHOLDS["sms-low"] + 1, -1, THRESHOLDS["sms-high"] + 1, "down", True),
        (THRESHOLDS["sms-low"] + 1, -1, -1, "down", True),
        (-1, THRESHOLDS["sms-medium"], THRESHOLDS["sms-high"], "down", True),
        (-1, THRESHOLDS["sms-medium"], THRESHOLDS["sms-high"] + 1, "down", True),
        (-1, THRESHOLDS["sms-medium"], -1, "down", True),
        (-1, THRESHOLDS["sms-medium"] + 1, THRESHOLDS["sms-high"], "down", True),
        (-1, THRESHOLDS["sms-medium"] + 1, THRESHOLDS["sms-high"] + 1, "down", True),
        (-1, THRESHOLDS["sms-medium"] + 1, -1, "down", True),
        (-1, -1, THRESHOLDS["sms-high"], "down", True),
        (-1, -1, THRESHOLDS["sms-high"] + 1, "down", True),
        (-1, -1, -1, "down", True),
    ],
)
def test_logging_determine_notification_status_logs_on_sms_degraded_or_down(
    mocker, sms_low, sms_medium, sms_high, status, log_expected, caplog
):
    notifications_data = [
        ["73079cb9-c169-44ea-8cf4-8d397711cc9d", 1],
        ["c75c4539-3014-4c4c-96b5-94d326758a74", 1],
        ["276da251-3103-49f3-9054-cbf6b5d74411", 1],
        ["ab3a603b-d602-46ea-8c83-e05cb280b950", sms_low] if sms_low != -1 else ["dummy-data", 0],
        ["a48b54ce-40f6-4e4a-abe8-1e2fa389455b", sms_medium] if sms_medium != -1 else ["dummy-data", 0],
        ["4969a9e9-ddfd-476e-8b93-6231e6f1be4a", sms_high] if sms_high != -1 else ["dummy-data", 0],
    ]

    caplog.set_level("INFO")
    determine_notification_status(notifications_data)

    if log_expected:
        assert "[system_status_sms]: sms is {}".format(status) in caplog.text


@pytest.mark.parametrize("site, threshold", [("http://site-1.example.com", 400)])
@pytest.mark.parametrize("response_time", (401, 500))
def test_logging_determine_site_status_logs_on_site_degraded(mocker, site, threshold, response_time, caplog):
    # mock the call to check_response_time()
    mocker.patch("notifications_utils.system_status.check_response_time", return_value=response_time)

    caplog.set_level("INFO")
    determine_site_status(site, threshold)

    assert "[system_status_site]: site {} is degraded".format(site) in caplog.text


@pytest.mark.parametrize("site, threshold", [("http://site-1.example.com", 400)])
def test_logging_determine_site_status_logs_on_site_down_connection_error(mocker, site, threshold, caplog):
    mocker.patch("notifications_utils.system_status.check_response_time", side_effect=requests.exceptions.ConnectionError)

    caplog.set_level("ERROR")
    determine_site_status(site, threshold)

    assert "[system_status_site]: site {} is down: Error connecting to url".format(site) in caplog.text


@pytest.mark.parametrize("site, threshold", [("http://site-1.example.com", 400)])
def test_logging_determine_site_status_logs_on_site_down_other_error(mocker, site, threshold, caplog):
    mocker.patch("notifications_utils.system_status.check_response_time", side_effect=requests.exceptions.TooManyRedirects)

    caplog.set_level("ERROR")
    determine_site_status(site, threshold)

    assert "[system_status_site]: site {} is down: unexpected error".format(site) in caplog.text
