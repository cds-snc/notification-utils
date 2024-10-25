"""This module is used to calculate the bounce rate for a service. It uses Redis to store the total number of hard bounces"""

from datetime import datetime

from notifications_utils.clients.redis.redis_client import RedisClient

SMS_DELIVERED = "sms_delivered"
EMAIL_DELIVERED = "email_delivered"
SMS_FAILED = "sms_failed"
EMAIL_FAILED = "email_failed"

NEAR_SMS_LIMIT = "near_sms_limit"
NEAR_EMAIL_LIMIT = "near_email_limit"
OVER_SMS_LIMIT = "over_sms_limit"
OVER_EMAIL_LIMIT = "over_email_limit"


def notifications_key(service_id):
    """
    Generates the Redis hash key for storing daily metrics of a service.
    """
    return f"annual-limit:{service_id}:notifications"


def annual_limit_status_key(service_id):
    """
    Generates the Redis hash key for storing annual limit information of a service.
    """
    return f"annual-limit:{service_id}:status"


def decode_byte_dict(dict: dict):
    return {key.decode("utf-8"): value.decode("utf-8") for key, value in dict.items()}


class RedisAnnualLimit:
    def __init__(self, redis: RedisClient):
        self._redis_client = redis

    def init_app(self, app, *args, **kwargs):
        self._default_volume_threshold = app.config.get("DEFAULT_ANNUAL_LIMIT")
        self._default_rate = app.config.get("DEFAULT_RATE")

    def increment_notification_count(self, service_id: str, field: str):
        self._redis_client.increment_hash_value(notifications_key(service_id), field)

    def get_notification_count(self, service_id: str, field: str):
        return int(self._redis_client.get_hash_field(notifications_key(service_id), field))

    def get_all_notification_counts(self, service_id: str):
        return decode_byte_dict(self._redis_client.get_all_from_hash(notifications_key(service_id)))

    def clear_notification_counts(self, service_id: str):
        self._redis_client.expire(notifications_key(service_id), -1)

    def set_annual_limit_status(self, service_id: str, field: str, value: datetime):
        """
        Sets the status (e.g., 'nearing_limit', 'over_limit') in the annual limits Redis hash.
        """
        self._redis_client.set_hash_value(annual_limit_status_key(service_id), field, value.strftime("%Y-%m-%d"))

    def get_annual_limit_status(self, service_id: str, field: str):
        """
        Retrieves the value of a specific annual limit status from the Redis hash.
        """
        return self._redis_client.get_hash_field(annual_limit_status_key(service_id), field).decode("utf-8")

    def get_all_annual_limit_statuses(self, service_id: str):
        return decode_byte_dict(self._redis_client.get_all_from_hash(annual_limit_status_key(service_id)))

    def clear_annual_limit_statuses(self, service_id: str):
        self._redis_client.expire(f"{annual_limit_status_key(service_id)}", -1)

    # Helper methods for daily metrics
    def increment_sms_delivered(self, service_id: str):
        self.increment_notification_count(service_id, SMS_DELIVERED)

    def increment_sms_failed(self, service_id: str):
        self.increment_notification_count(service_id, SMS_FAILED)

    def increment_email_delivered(self, service_id: str):
        self.increment_notification_count(service_id, EMAIL_DELIVERED)

    def increment_email_failed(self, service_id: str):
        self.increment_notification_count(service_id, EMAIL_FAILED)

    # Helper methods for annual limits
    def set_nearing_sms_limit(self, service_id: str):
        self.set_annual_limit_status(service_id, NEAR_SMS_LIMIT, datetime.utcnow())

    def set_nearing_email_limit(self, service_id: str):
        self.set_annual_limit_status(service_id, NEAR_EMAIL_LIMIT, datetime.utcnow())

    def set_over_sms_limit(self, service_id: str):
        self.set_annual_limit_status(service_id, OVER_SMS_LIMIT, datetime.utcnow())

    def set_over_email_limit(self, service_id: str):
        self.set_annual_limit_status(service_id, OVER_EMAIL_LIMIT, datetime.utcnow())

    def check_has_warning_been_sent():
        pass

    def check_has_over_limit_been_sent():
        pass
