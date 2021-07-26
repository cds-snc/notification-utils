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
