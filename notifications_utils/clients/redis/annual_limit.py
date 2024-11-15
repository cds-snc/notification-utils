"""
This module stores daily notification counts and annual limit statuses for a service in Redis using a hash structure:


annual-limit: {
    {service_id}: {
        notifications: {
            sms_delivered: int,
            email_delivered: int,
            sms_failed: int,
            email_failed: int
        },
        status: {
            near_sms_limit: Datetime,
            near_email_limit: Datetime,
            over_sms_limit: Datetime,
            over_email_limit: Datetime
            seeded_at: Datetime
        }
    }
}


"""

from datetime import datetime

from notifications_utils.clients.redis.redis_client import RedisClient

SMS_DELIVERED = "sms_delivered"
EMAIL_DELIVERED = "email_delivered"
SMS_FAILED = "sms_failed"
EMAIL_FAILED = "email_failed"

NOTIFICATIONS = [SMS_DELIVERED, EMAIL_DELIVERED, SMS_FAILED, EMAIL_FAILED]

NEAR_SMS_LIMIT = "near_sms_limit"
NEAR_EMAIL_LIMIT = "near_email_limit"
OVER_SMS_LIMIT = "over_sms_limit"
OVER_EMAIL_LIMIT = "over_email_limit"
SEEDED_AT = "seeded_at"

STATUSES = [NEAR_SMS_LIMIT, NEAR_EMAIL_LIMIT, OVER_SMS_LIMIT, OVER_EMAIL_LIMIT]


def annual_limit_notifications_key(service_id):
    """
    Generates the Redis hash key for storing daily metrics of a service.
    """
    return f"annual-limit:{service_id}:notifications"


def annual_limit_status_key(service_id):
    """
    Generates the Redis hash key for storing annual limit information of a service.
    """
    return f"annual-limit:{service_id}:status"


def decode_byte_dict(byte_dict: dict, value_type=str):
    """
    Redis-py returns byte strings for keys and values. This function decodes them to UTF-8 strings.
    """
    # Check if expected_value_type is one of the allowed types
    if value_type not in {int, float, str}:
        raise ValueError("expected_value_type must be int, float, or str")
    if byte_dict is None or not byte_dict.items():
        return None
    return {key.decode("utf-8"): value_type(value.decode("utf-8")) for key, value in byte_dict.items()}


class RedisAnnualLimit:
    def __init__(self, redis: RedisClient):
        self._redis_client = redis

    def init_app(self, app, *args, **kwargs):
        pass

    def increment_notification_count(self, service_id: str, field: str):
        """Increments the specified daily notification count field for a service.
        Fields that can be set: `sms_delivered`, `email_delivered`, `sms_failed`, `email_failed`

        Args:
            service_id (str): _description_
            field (str): _description_
        """
        self._redis_client.increment_hash_value(annual_limit_notifications_key(service_id), field)

    def get_notification_count(self, service_id: str, field: str):
        """
        Retrieves the specified daily notification count for a service. (e.g. SMS_DELIVERED, EMAIL_FAILED, etc.)
        """
        count = self._redis_client.get_hash_field(annual_limit_notifications_key(service_id), field)
        return count and int(count.decode("utf-8"))

    def get_all_notification_counts(self, service_id: str):
        """
        Retrieves all daily notification metrics for a service.
        """
        return decode_byte_dict(self._redis_client.get_all_from_hash(annual_limit_notifications_key(service_id)), int)

    def reset_all_notification_counts(self, service_ids=None):
        """Resets all daily notification metrics.

        Args:
            service_ids (Optional): A list of service_ids to reset notification counts for. Resets all services if None.

        """
        hashes = (
            annual_limit_notifications_key("*")
            if not service_ids
            else [annual_limit_notifications_key(service_id) for service_id in service_ids]
        )

        self._redis_client.delete_hash_fields(hashes=hashes)

    def seed_annual_limit_notifications(self, service_id: str, mapping: dict):
        """Seeds annual limit notifications for a service.

        Args:
            service_id (str): Service to seed annual limit notifications for.
            mapping (dict): A dict used to map notification counts to their respective fields formatted as follows

        Examples:
            `mapping` format:

                {
                    "sms_delivered": int,
                    "email_delivered": int,
                    "sms_failed": int,
                    "email_failed": int
                }
        """
        self._redis_client.bulk_set_hash_fields(key=annual_limit_notifications_key(service_id), mapping=mapping)

    def was_seeded_today(self, service_id):
        last_seeded_time = self.get_seeded_at(service_id)
        return last_seeded_time == datetime.utcnow().strftime("%Y-%m-%d") if last_seeded_time else False

    def get_seeded_at(self, service_id: str):
        seeded_at = self._redis_client.get_hash_field(annual_limit_status_key(service_id), SEEDED_AT)
        return seeded_at and seeded_at.decode("utf-8")

    def set_seeded_at(self, service_id):
        self._redis_client.set_hash_value(annual_limit_status_key(service_id), SEEDED_AT, datetime.utcnow().strftime("%Y-%m-%d"))

    def clear_notification_counts(self, service_id: str):
        """
        Clears all daily notification metrics for a service.
        """
        self._redis_client.expire(annual_limit_notifications_key(service_id), -1)

    def set_annual_limit_status(self, service_id: str, field: str, value: datetime):
        """
        Sets the specified status field in the annual limits Redis hash for a service.
        Fields that can be set: `near_sms_limit`, `near_email_limit`, `over_sms_limit`, `over_email_limit`, `seeded_at`

        Args:
            service_id (str): The service to set the annual limit status field for
            field (str): The field to set in the annual limit status hash.
            value (datetime): The date to set the status to
        """
        self._redis_client.set_hash_value(annual_limit_status_key(service_id), field, value.strftime("%Y-%m-%d"))

    def get_annual_limit_status(self, service_id: str, field: str):
        """
        Retrieves the value of a specific annual limit status from the Redis hash.
        Fields that can be fetched: `near_sms_limit`, `near_email_limit`, `over_sms_limit`, `over_email_limit`, `seeded_at`

        Args:
            service_id (str): The service to fetch the annual limit status field for
            field (str): The field to fetch from the annual limit status hash values:
                         `near_sms_limit`, `near_email_limit`, `over_sms_limit`, `over_email_limit`, `seeded_at`

        Returns:
            str | None: The date the status was set, or None if the status has not been set
        """
        response = self._redis_client.get_hash_field(annual_limit_status_key(service_id), field)
        return response and response.decode("utf-8")

    def get_all_annual_limit_statuses(self, service_id: str):
        """Retrieves all annual limit status fields for a specified service from Redis

        Args:
            service_id (str): The service to fetch annual limit statuses for

        Returns:
            dict | None: A dictionary of annual limit statuses or None if no statuses are found
        """
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

    def check_has_warning_been_sent(self, service_id: str, message_type: str):
        """
        Check if an annual limit warning email has been sent to the service.
        Returns None if no warning has been sent, otherwise returns the date the
        last warning was issued.
        When a service's annual limit is increased this value is reset.
        """
        field_to_fetch = NEAR_SMS_LIMIT if message_type == "sms" else NEAR_EMAIL_LIMIT
        return self.get_annual_limit_status(service_id, field_to_fetch)

    def check_has_over_limit_been_sent(self, service_id: str, message_type: str):
        """
        Check if an annual limit exceeded email has been sent to the service.
        Returns None if no exceeded email has been sent, otherwise returns the date the
        last exceeded email was issued.
        When a service's annual limit is increased this value is reset.
        """
        field_to_fetch = OVER_SMS_LIMIT if message_type == "sms" else OVER_EMAIL_LIMIT
        return self.get_annual_limit_status(service_id, field_to_fetch)
