"""This module is used to calculate the bounce rate for a service. It uses Redis to store the total number of hard bounces """
from datetime import datetime

from notifications_utils.clients.redis.redis_client import RedisClient


def hard_bounce_key(service_id: str):
    return f"sliding_hard_bounce:{service_id}"


def total_notifications_key(service_id: str):
    return f"sliding_total_notifications:{service_id}"


def _twenty_four_hour_window_ms() -> int:
    return 24 * 60 * 60 * 1000


def _current_timestamp_ms() -> int:
    return int(datetime.now().timestamp() * 1000.0)


class RedisBounceRate:
    def __init__(self, redis: RedisClient):
        self._redis_client = redis
        self.minimum_volume = 1000

    def init_app(self, app, *args, **kwargs):
        self.minimum_volume = app.config.get("BR_DISPLAY_VOLUME_MINIMUM")

    def set_sliding_notifications(self, service_id: str) -> None:
        current_time = _current_timestamp_ms()
        self._redis_client.add_data_to_sorted_set(total_notifications_key(service_id), {current_time: current_time})

    def set_sliding_hard_bounce(self, service_id: str) -> None:
        current_time = _current_timestamp_ms()
        self._redis_client.add_data_to_sorted_set(hard_bounce_key(service_id), {current_time: current_time})

    def set_notifications_seeded(self, service_id: str, seeded_data: dict) -> None:
        self._redis_client.add_data_to_sorted_set(total_notifications_key(service_id), seeded_data)

    def set_hard_bounce_seeded(self, service_id: str, seeded_data: dict) -> None:
        self._redis_client.add_data_to_sorted_set(hard_bounce_key(service_id), seeded_data)

    def get_bounce_rate(self, service_id: str, bounce_window=_twenty_four_hour_window_ms()) -> float:

        now = _current_timestamp_ms()
        twenty_four_hours_ago = now - bounce_window

        # delete data older than 24 hours
        self._redis_client.delete_from_sorted_set(hard_bounce_key(service_id), min_score=twenty_four_hours_ago, max_score=now)
        self._redis_client.delete_from_sorted_set(
            total_notifications_key(service_id), min_score=twenty_four_hours_ago, max_score=now
        )

        total_hard_bounces = self._redis_client.get_length_of_sorted_set(
            hard_bounce_key(service_id), min_score=twenty_four_hours_ago, max_score=now
        )
        total_notifications = self._redis_client.get_length_of_sorted_set(
            total_notifications_key(service_id), min_score=twenty_four_hours_ago, max_score=now
        )

        return round(total_hard_bounces / (1.0 * total_notifications), 2) if (total_notifications >= self.minimum_volume) else 0.0
