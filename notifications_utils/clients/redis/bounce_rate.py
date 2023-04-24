"""This module is used to calculate the bounce rate for a service. It uses Redis to store the total number of hard bounces """
import time


def hard_bounce_key(service_id: str):
    return f"sliding_hard_bounce:{service_id}"


def total_notifications_key(service_id: str):
    return f"sliding_total_notifications:{service_id}"


def _twenty_four_hour_window_ms():
    return 60 * 60 * 24 * 1000


def _current_time_ms():
    return int(time.time()) * 1000


class RedisBounceRate:
    def __init__(self, redis):
        self._redis_client = redis

    def set_sliding_notifications(self, service_id: str):
        current_time = _current_time_ms()
        self._redis_client.add_data_to_sorted_set(total_notifications_key(service_id), {current_time: current_time})

    def set_sliding_hard_bounce(self, service_id: str):
        current_time = _current_time_ms()
        self._redis_client.add_data_to_sorted_set(hard_bounce_key(service_id), {current_time: current_time})

    def set_notifications_seeded(self, service_id: str, seeded_data: dict):
        self._redis_client.add_data_to_sorted_set(total_notifications_key(service_id), seeded_data)

    def set_hard_bounce_seeded(self, service_id: str, seeded_data: dict):
        self._redis_client.add_data_to_sorted_set(hard_bounce_key(service_id), seeded_data)

    def get_bounce_rate(self, service_id: str, bounce_window=_twenty_four_hour_window_ms()) -> int:
        total_hard_bounces_sliding = self._redis_client.get_length_of_sorted_set(hard_bounce_key(service_id), bounce_window)
        total_notifications_sliding = self._redis_client.get_length_of_sorted_set(
            total_notifications_key(service_id), bounce_window
        )
        return (
            round(total_hard_bounces_sliding / (1.0 * total_notifications_sliding), 2) if (total_notifications_sliding > 0) else 0
        )
