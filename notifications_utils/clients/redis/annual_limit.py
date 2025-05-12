"""
This module stores daily notification counts and annual limit statuses for a service in Redis using a hash structure:

# TODO: Remove the first key once all services have been migrated to the new Redis structure
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
        },
        notifications_v2: {
            sms_delivered_today: int,
            email_delivered_today: int,
            sms_failed_today: int,
            email_failed_today: int,
            total_sms_fiscal_year_to_yesterday: int,
            total_email_fiscal_year_to_yesterday: int,
            seeded_at: Datetime
        }
    }
}


"""

from datetime import datetime

from flask import current_app

from notifications_utils.clients.redis.redis_client import RedisClient

# TODO: Remove the first 4 keys once all services have been migrated to the new Redis structure
SMS_DELIVERED = "sms_delivered"
EMAIL_DELIVERED = "email_delivered"
SMS_FAILED = "sms_failed"
EMAIL_FAILED = "email_failed"
SMS_DELIVERED_TODAY = "sms_delivered_today"
EMAIL_DELIVERED_TODAY = "email_delivered_today"
SMS_FAILED_TODAY = "sms_failed_today"
EMAIL_FAILED_TODAY = "email_failed_today"
TOTAL_SMS_FISCAL_YEAR_TO_YESTERDAY = "total_sms_fiscal_year_to_yesterday"
TOTAL_EMAIL_FISCAL_YEAR_TO_YESTERDAY = "total_email_fiscal_year_to_yesterday"

NOTIFICATION_FIELDS = [SMS_DELIVERED, EMAIL_DELIVERED, SMS_FAILED, EMAIL_FAILED]
NOTIFICATION_FIELDS_V2 = [
    SMS_DELIVERED_TODAY,
    EMAIL_DELIVERED_TODAY,
    SMS_FAILED_TODAY,
    EMAIL_FAILED_TODAY,
    TOTAL_SMS_FISCAL_YEAR_TO_YESTERDAY,
    TOTAL_EMAIL_FISCAL_YEAR_TO_YESTERDAY,
]

NEAR_SMS_LIMIT = "near_sms_limit"
NEAR_EMAIL_LIMIT = "near_email_limit"
OVER_SMS_LIMIT = "over_sms_limit"
OVER_EMAIL_LIMIT = "over_email_limit"
SEEDED_AT = "seeded_at"

STATUS_FIELDS = [NEAR_SMS_LIMIT, NEAR_EMAIL_LIMIT, OVER_SMS_LIMIT, OVER_EMAIL_LIMIT]


# TODO: Remove this once all services have been migrated to the new Redis structure
def annual_limit_notifications_key(service_id):
    """
    Generates the Redis hash key for storing daily metrics of a service.
    """
    return f"annual-limit:{service_id}:notifications"


def annual_limit_notifications_v2_key(service_id):
    """
    Generates the Redis hash key for storing daily metrics of a service.
    """
    return f"annual-limit:{service_id}:notifications_v2"


def annual_limit_status_key(service_id):
    """
    Generates the Redis hash key for storing annual limit information of a service.
    """
    return f"annual-limit:{service_id}:status"


def prepare_byte_dict(byte_dict: dict, value_type=str, required_keys=None):
    """
    Redis-py returns byte strings for keys and values. This function decodes them to UTF-8 strings.
    """
    # Check if expected_value_type is one of the allowed types
    if value_type not in {int, float, str}:
        raise ValueError("expected_value_type must be int, float, or str")

    decoded_dict = (
        {key.decode("utf-8"): value_type(value.decode("utf-8")) for key, value in byte_dict.items()} if byte_dict else {}
    )

    if required_keys:
        for key in required_keys:
            default_value = 0 if value_type in {int, float} else None
            decoded_dict.setdefault(key, default_value)
    return decoded_dict


def init_missing_keys(
    required_keys: list,
    value_type=str,
    incomplete_dict: dict = {},
):
    """Ensures that all expected keys are present in dicts returned from this module. Initializes empty values to defaults if not.

    Args:
        incomplete_dict (dict): A dictionary to check for required keys.
        required_keys (list): The keys that must be present in the dictionary.
        value_type (_type_, optional): The datatype of the values in the dict. Defaults to str.

    Raises:
        ValueError: If the value_type is not int, float, or str.
    """
    if value_type not in {int, float, str}:
        raise ValueError("expected_value_type must be int, float, or str")


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
        # TODO: Remove the else
        if field in NOTIFICATION_FIELDS_V2:
            self._redis_client.increment_hash_value(annual_limit_notifications_v2_key(service_id), field)
        else:
            self._redis_client.increment_hash_value(annual_limit_notifications_key(service_id), field)

    def get_notification_count(self, service_id: str, field: str):
        """
        Retrieves the specified daily notification count for a service. (e.g. SMS_DELIVERED, EMAIL_FAILED, SMS_DELIVERED_TODAY etc.)
        """
        count = self._redis_client.get_hash_field(annual_limit_notifications_v2_key(service_id), field)
        if count:
            return int(count.decode("utf-8"))
        # TODO: Remove this once all services have been migrated to the new Redis structure
        # TODO: Change the above to return 0 if count is None
        count = self._redis_client.get_hash_field(annual_limit_notifications_key(service_id), field)
        return 0 if not count else int(count.decode("utf-8"))

    def get_all_notification_counts(self, service_id: str):
        """
        Retrieves all daily notification metrics for a service.
        """
        if self._redis_client.redis_store.exists(annual_limit_notifications_v2_key(service_id)):
            all_keys = self._redis_client.get_all_from_hash(annual_limit_notifications_v2_key(service_id))
            # remove the seeded_at key from the list of keys
            seeded_at_byte = bytes(SEEDED_AT, "utf-8")
            if seeded_at_byte in all_keys:
                del all_keys[seeded_at_byte]
            return prepare_byte_dict(
                all_keys,
                int,
                NOTIFICATION_FIELDS_V2,
            )
        # TODO: Remove this once all services have been migrated to the new Redis structure
        return prepare_byte_dict(
            self._redis_client.get_all_from_hash(annual_limit_notifications_key(service_id)), int, NOTIFICATION_FIELDS
        )

    def reset_all_notification_counts(self, service_ids=None):
        """Resets all daily notification metrics.

        Args:
            service_ids (Optional): A list of service_ids to reset notification counts for. Resets all services if None.

        """
        hashes = (
            annual_limit_notifications_v2_key("*")
            if not service_ids
            else [annual_limit_notifications_v2_key(service_id) for service_id in service_ids]
        )
        self._redis_client.delete_hash_fields(hashes=hashes, fields=NOTIFICATION_FIELDS_V2)
        # TODO: Remove the else once all services have been migrated to the new Redis structure
        hashes = (
            annual_limit_notifications_key("*")
            if not service_ids
            else [annual_limit_notifications_key(service_id) for service_id in service_ids]
        )
        self._redis_client.delete_hash_fields(hashes=hashes, fields=NOTIFICATION_FIELDS)

    def seed_annual_limit_notifications(self, service_id: str, mapping: dict):
        """Seeds annual limit notifications for a service.
        # TODO: Update the docstring once all services have been migrated to the new Redis structure
        Args:
            service_id (str): Service to seed annual limit notifications for.
            mapping (dict): A dict used to map notification counts to their respective fields formatted as follows

        Examples:
            `mapping` format:

                {
                    "sms_delivered": int,
                    "email_delivered": int,
                    "sms_failed": int,
                    "email_failed": int,
                }
            as we added notifications_v2, the mapping can also be:
                {
                    "sms_delivered_today": int,
                    "email_delivered_today": int,
                    "sms_failed_today": int,
                    "email_failed_today": int,
                    "total_sms_fiscal_year_to_yesterday": int,
                    "total_email_fiscal_year_to_yesterday": int,
                }
        """
        if not mapping or all(notification_count == 0 for notification_count in mapping.values()):
            current_app.logger.info(
                f"Skipping seeding of annual limit notifications for service {service_id}. No mapping provided, or mapping is empty."
            )
            return

        # Extract only V2 fields that exist in the mapping
        v2_mapping = {k: mapping[k] for k in NOTIFICATION_FIELDS_V2 if k in mapping}

        # Log if we're missing any V2 fields
        if set(v2_mapping.keys()) != set(NOTIFICATION_FIELDS_V2):
            missing_fields = set(NOTIFICATION_FIELDS_V2) - set(v2_mapping.keys())
            current_app.logger.warning(f"Missing V2 fields when seeding annual limit for service {service_id}: {missing_fields}")

        # Store V2 fields
        self._redis_client.bulk_set_hash_fields(key=annual_limit_notifications_v2_key(service_id), mapping=v2_mapping)

        # Store V1 fields
        legacy_mapping = {k: mapping[k] for k in NOTIFICATION_FIELDS if k in mapping}
        self._redis_client.bulk_set_hash_fields(key=annual_limit_notifications_key(service_id), mapping=legacy_mapping)

        # Only after successful storage, set the seeded flag
        self.set_seeded_at(service_id)

    def was_seeded_today(self, service_id):
        last_seeded_time = self.get_seeded_at(service_id)
        return last_seeded_time == datetime.utcnow().strftime("%Y-%m-%d") if last_seeded_time else False

    def get_seeded_at(self, service_id: str, key=None):
        seeded_at = self._redis_client.get_hash_field(annual_limit_notifications_v2_key(service_id), SEEDED_AT)
        return seeded_at and seeded_at.decode("utf-8")

    def set_seeded_at(self, service_id):
        # We are now setting the seeded value for notifications_v2
        self._redis_client.set_hash_value(
            annual_limit_notifications_v2_key(service_id), SEEDED_AT, datetime.utcnow().strftime("%Y-%m-%d")
        )
        # TODO: Remove the below once all services have been migrated to the new Redis structure
        # Setting the seeded at in status for backward compatibility
        self._redis_client.set_hash_value(annual_limit_status_key(service_id), SEEDED_AT, datetime.utcnow().strftime("%Y-%m-%d"))

    def clear_notification_counts(self, service_id: str):
        """
        Clears all daily notification metrics for a service.
        """
        self._redis_client.expire(annual_limit_notifications_v2_key(service_id), -1)
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
        if field == "seeded_at":
            return self.get_seeded_at(service_id)
        response = self._redis_client.get_hash_field(annual_limit_status_key(service_id), field)
        return response and response.decode("utf-8")

    def get_all_annual_limit_statuses(self, service_id: str):
        """Retrieves all annual limit status fields for a specified service from Redis

        Args:
            service_id (str): The service to fetch annual limit statuses for

        Returns:
            dict | None: A dictionary of annual limit statuses or None if no statuses are found
        """
        return prepare_byte_dict(self._redis_client.get_all_from_hash(annual_limit_status_key(service_id)), str, STATUS_FIELDS)

    def clear_annual_limit_statuses(self, service_id: str):
        self._redis_client.expire(f"{annual_limit_status_key(service_id)}", -1)

    # Helper methods for daily metrics
    def increment_sms_delivered(self, service_id: str):
        self.increment_notification_count(service_id, SMS_DELIVERED_TODAY)
        # TODO: remove the below line
        self.increment_notification_count(service_id, SMS_DELIVERED)

    def increment_sms_failed(self, service_id: str):
        self.increment_notification_count(service_id, SMS_FAILED_TODAY)
        # TODO: remove the below line
        self.increment_notification_count(service_id, SMS_FAILED)

    def increment_email_delivered(self, service_id: str):
        self.increment_notification_count(service_id, EMAIL_DELIVERED_TODAY)
        # TODO: remove the below line
        self.increment_notification_count(service_id, EMAIL_DELIVERED)

    def increment_email_failed(self, service_id: str):
        self.increment_notification_count(service_id, EMAIL_FAILED_TODAY)
        # TODO: remove the below line
        self.increment_notification_count(service_id, EMAIL_FAILED)

    # Helper methods for annual limits statuses
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

    def delete_all_annual_limit_hashes(self, service_ids=None):
        """
        THIS SHOULD NOT BE CALLED IN CODE. This is a helper method for testing purposes only.
        Clears all annual limit hashes in Redis

        Args:
            service_ids (Optional): A list of service_ids to clear annual limit hashes for. Clears all services if None.
        """
        if not service_ids:
            self._redis_client.delete_cache_keys_by_pattern(annual_limit_notifications_v2_key("*"))
            # TODO: Remove the line below
            self._redis_client.delete_cache_keys_by_pattern(annual_limit_notifications_key("*"))
            self._redis_client.delete_cache_keys_by_pattern(annual_limit_status_key("*"))
        else:
            for service_id in service_ids:
                self._redis_client.delete(annual_limit_notifications_v2_key(service_id))
                self._redis_client.delete(annual_limit_notifications_key(service_id))
                self._redis_client.delete(annual_limit_status_key(service_id))
