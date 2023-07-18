from datetime import datetime


def daily_limit_cache_key(service_id):
    return "{}-{}-{}".format(str(service_id), datetime.utcnow().strftime("%Y-%m-%d"), "count")


def near_daily_limit_cache_key(service_id):
    return f"nearing-{daily_limit_cache_key(service_id)}"


def template_version_cache_key(template_id, version=None):
    return f"template-{template_id}-version-{version}"


def service_cache_key(service_id):
    return f"service-{service_id}"


def over_daily_limit_cache_key(service_id):
    return f"over-{daily_limit_cache_key(service_id)}"


def rate_limit_cache_key(service_id, api_key_type):
    return "{}-{}".format(str(service_id), api_key_type)


def sms_daily_count_cache_key(service_id):
    return "sms-{}-{}-{}".format(str(service_id), datetime.utcnow().strftime("%Y-%m-%d"), "count")


def near_sms_daily_limit_cache_key(service_id):
    return f"nearing-daily-limit-{sms_daily_count_cache_key(service_id)}"


def over_sms_daily_limit_cache_key(service_id):
    return f"over-daily-limit-{sms_daily_count_cache_key(service_id)}"


def email_daily_count_cache_key(service_id) -> str:
    """
    Used to keep track how many emails a service has sent in a day.

    """
    return "email-{}-{}-{}".format(str(service_id), datetime.utcnow().strftime("%Y-%m-%d"), "count")


def near_email_daily_limit_cache_key(service_id) -> str:
    """
    Cache key that stores a str with the current date time indicating is the service is nearing the daily email limit.

    """
    return f"nearing-daily-email-limit-{email_daily_count_cache_key(service_id)}"


def over_email_daily_limit_cache_key(service_id) -> str:
    """
    Cache key that stores a str with the current date time indicating is the service is over the daily email limit.

    """
    return f"over-daily-email-limit-{email_daily_count_cache_key(service_id)}"
