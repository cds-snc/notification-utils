import pytest
import requests
from notifications_utils.system_status import determine_site_status, determine_notification_status, THRESHOLDS


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
