"""This module is used to calculate the bounce rate for a service. It uses Redis to store the total number of hard bounces"""

from datetime import datetime

from notifications_utils.clients.redis.redis_client import RedisClient

TWENTY_FOUR_HOURS_IN_SECONDS = 24 * 60 * 60
DEFAULT_VOLUME_THRESHOLD = 1000
BR_CRITICAL_PERCENTAGE_DEFAULT = 0.1
BR_WARNING_PERCENTAGE_DEFAULT = 0.05


def hard_bounce_key(service_id: str):
    return f"sliding_hard_bounce:{service_id}"


def total_notifications_key(service_id: str):
    return f"sliding_total_notifications:{service_id}"


def seeding_started_key(service_id: str):
    return f"seeding_started:{service_id}"


def _current_timestamp_s() -> int:
    return int(datetime.utcnow().timestamp())


class RedisBounceRate:
    def __init__(self, redis: RedisClient):
        self._redis_client = redis

    def init_app(self, app, *args, **kwargs):
        self._critical_threshold = (
            app.config.get("BR_CRITICAL_PERCENTAGE")
            if app.config.get("BR_CRITICAL_PERCENTAGE")
            else BR_CRITICAL_PERCENTAGE_DEFAULT
        )
        self._warning_threshold = (
            app.config.get("BR_WARNING_PERCENTAGE") if app.config.get("BR_WARNING_PERCENTAGE") else BR_WARNING_PERCENTAGE_DEFAULT
        )

    def set_sliding_notifications(self, service_id: str, notification_id: str) -> None:
        """Add a notification to the sliding total notifications sorted set in Redis."""
        current_time = _current_timestamp_s()
        self._redis_client.add_data_to_sorted_set(total_notifications_key(service_id), {notification_id: current_time})

    def set_sliding_hard_bounce(self, service_id: str, notification_id: str) -> None:
        """Add a notification to the sliding hard bounce sorted set in Redis."""
        current_time = _current_timestamp_s()
        self._redis_client.add_data_to_sorted_set(hard_bounce_key(service_id), {notification_id: current_time})

    def set_notifications_seeded(self, service_id: str, seeded_data: dict) -> None:
        self._redis_client.add_data_to_sorted_set(total_notifications_key(service_id), seeded_data)

    def set_hard_bounce_seeded(self, service_id: str, seeded_data: dict) -> None:
        self._redis_client.add_data_to_sorted_set(hard_bounce_key(service_id), seeded_data)

    def set_seeding_started(self, service_id: str) -> None:
        """Set a flag in Redis to indicate that we have started to seed data for a given service"""
        self._redis_client.set(seeding_started_key(service_id), "True")
        self._redis_client.expire(seeding_started_key(service_id), TWENTY_FOUR_HOURS_IN_SECONDS)

    def get_seeding_started(self, service_id: str) -> bool:
        """Returns True if seeding is has already started, False otherwise"""
        if self._redis_client.get(seeding_started_key(service_id)) == b"True":
            return True
        return False

    def clear_bounce_rate_data(self, service_id: str) -> None:
        """Clears all bounce rate data for a service before seeding new data"""
        self._redis_client.delete(hard_bounce_key(service_id))
        self._redis_client.delete(total_notifications_key(service_id))

    def get_total_hard_bounces(self, service_id: str, bounce_window=TWENTY_FOUR_HOURS_IN_SECONDS) -> int:
        """Returns the total number of hard bounces for a service in the bounce_window"""
        now = _current_timestamp_s()
        twenty_four_hours_ago = now - bounce_window
        return self._redis_client.get_length_of_sorted_set(
            hard_bounce_key(service_id), min_score=twenty_four_hours_ago, max_score=now
        )

    def get_total_notifications(self, service_id: str, bounce_window=TWENTY_FOUR_HOURS_IN_SECONDS) -> int:
        """Returns the total number of email notifications a service has sent in the bounce_window"""
        now = _current_timestamp_s()
        twenty_four_hours_ago = now - bounce_window
        return self._redis_client.get_length_of_sorted_set(
            total_notifications_key(service_id), min_score=twenty_four_hours_ago, max_score=now
        )

    def get_bounce_rate(self, service_id: str, bounce_window=TWENTY_FOUR_HOURS_IN_SECONDS) -> float:
        """Returns the bounce rate for a service in the last 24 hours, and deletes data older than 24 hours"""
        now = _current_timestamp_s()
        twenty_four_hours_ago = now - bounce_window

        # delete data older than 24 hours
        self._redis_client.delete_from_sorted_set(hard_bounce_key(service_id), min_score=0, max_score=twenty_four_hours_ago)
        self._redis_client.delete_from_sorted_set(
            total_notifications_key(service_id), min_score=0, max_score=twenty_four_hours_ago
        )

        total_hard_bounces = self.get_total_hard_bounces(service_id, bounce_window)
        total_notifications = self.get_total_notifications(service_id, bounce_window)

        if total_notifications < 1:
            return 0.0

        return total_hard_bounces / (1.0 * total_notifications)

    def get_debug_data(self, service_id: str, bounce_window=TWENTY_FOUR_HOURS_IN_SECONDS):
        "Temporary function for debugging purposes"
        now = _current_timestamp_s()
        twenty_four_hours_ago = now - bounce_window

        total_hard_bounces = self.get_total_hard_bounces(service_id, bounce_window)
        total_notifications = self.get_total_notifications(service_id, bounce_window)

        return {
            "total_notifications": total_notifications,
            "total_hard_bounces": total_hard_bounces,
            "twenty_four_hours_ago": twenty_four_hours_ago,
            "now": now,
        }

    def check_bounce_rate_status(
        self, service_id: str, volume_threshold: int = DEFAULT_VOLUME_THRESHOLD, bounce_window=TWENTY_FOUR_HOURS_IN_SECONDS
    ):
        bounce_rate = self.get_bounce_rate(service_id, bounce_window)
        total_notifications = self.get_total_notifications(service_id, bounce_window)

        if total_notifications < volume_threshold or bounce_rate < self._warning_threshold:
            return "normal"

        if bounce_rate >= self._critical_threshold:
            return "critical"

        return "warning"
