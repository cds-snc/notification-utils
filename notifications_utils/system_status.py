import logging
import requests


TEMPLATES = {
    "email": {
        "low": "73079cb9-c169-44ea-8cf4-8d397711cc9d",
        "medium": "c75c4539-3014-4c4c-96b5-94d326758a74",
        "high": "276da251-3103-49f3-9054-cbf6b5d74411",
    },
    "sms": {
        "low": "ab3a603b-d602-46ea-8c83-e05cb280b950",
        "medium": "a48b54ce-40f6-4e4a-abe8-1e2fa389455b",
        "high": "4969a9e9-ddfd-476e-8b93-6231e6f1be4a",
    },
}

THRESHOLDS = {
    "email-low": 3 * 60 * 60 * 1000,  # 3 hours
    "email-medium": 45 * 60 * 1000,  # 45 minutes
    "email-high": 60 * 1000,  # 60 seconds
    "sms-low": 3 * 60 * 60 * 1000,  # 3 hours
    "sms-medium": 45 * 60 * 1000,  # 45 minutes
    "sms-high": 60 * 1000,  # 60 seconds
    "api": 400,  # 400ms
    "admin": 400,  # 400ms
}


def determine_notification_status(dbresults):  # noqa: C901
    # default all to down
    email_status_low = "down"
    email_status_medium = "down"
    email_status_high = "down"
    sms_status_low = "down"
    sms_status_medium = "down"
    sms_status_high = "down"

    for row in dbresults:
        if str(row[0]) == TEMPLATES["email"]["low"]:
            email_low_response_time = row[1]
            if email_low_response_time <= THRESHOLDS["email-low"]:
                email_status_low = "up"
            else:
                email_status_low = "degraded"

        elif str(row[0]) == TEMPLATES["email"]["medium"]:
            email_medium_response_time = row[1]
            if email_medium_response_time <= THRESHOLDS["email-medium"]:
                email_status_medium = "up"
            else:
                email_status_medium = "degraded"

        elif str(row[0]) == TEMPLATES["email"]["high"]:
            email_high_response_time = row[1]
            if email_high_response_time <= THRESHOLDS["email-high"]:
                email_status_high = "up"
            else:
                email_status_high = "degraded"

        elif str(row[0]) == TEMPLATES["sms"]["low"]:
            sms_low_response_time = row[1]
            if sms_low_response_time <= THRESHOLDS["sms-low"]:
                sms_status_low = "up"
            else:
                sms_status_low = "degraded"

        elif str(row[0]) == TEMPLATES["sms"]["medium"]:
            sms_medium_response_time = row[1]
            if sms_medium_response_time <= THRESHOLDS["sms-medium"]:
                sms_status_medium = "up"
            else:
                sms_status_medium = "degraded"

        elif str(row[0]) == TEMPLATES["sms"]["high"]:
            sms_high_response_time = row[1]
            if sms_high_response_time <= THRESHOLDS["sms-high"]:
                sms_status_high = "up"
            else:
                sms_status_high = "degraded"

    # set overall email_status based on if one of email_status_low, email_status_medium, email_status_high is down,
    # then email_status is down, if one is degraded, then email_status is degraded, otherwise email_status is up
    if email_status_low == "down" or email_status_medium == "down" or email_status_high == "down":
        email_status = "down"
    elif email_status_low == "degraded" or email_status_medium == "degraded" or email_status_high == "degraded":
        email_status = "degraded"
    else:
        email_status = "up"

    # set overall sms_status based on if one of sms_status_low, sms_status_medium, sms_status_high is down,
    # then sms_status is down, if one is degraded, then sms_status is degraded, otherwise sms_status is up
    if sms_status_low == "down" or sms_status_medium == "down" or sms_status_high == "down":
        sms_status = "down"
    elif sms_status_low == "degraded" or sms_status_medium == "degraded" or sms_status_high == "degraded":
        sms_status = "degraded"
    else:
        sms_status = "up"

    return (email_status, sms_status)


def determine_site_status(url, threshold):
    try:
        api_response_time = check_response_time(url)
        site_status = "up" if api_response_time <= threshold else "degraded"

    except requests.exceptions.ConnectionError as e:
        logging.error("utils/system_status: determine_site_status({}): Error connecting to url: {}".format(url, e))
        site_status = "down"
    except Exception as e:
        logging.error("utils/system_status: determine_site_status({}): unknown error: {}".format(url, e))
        site_status = "down"

    return site_status


def check_response_time(url):
    response = requests.get(url)
    return response.elapsed.total_seconds() * 1000
