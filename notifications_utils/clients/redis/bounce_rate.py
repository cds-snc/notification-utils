"""This module is used to calculate the bounce rate for a service. It uses Redis to store the total number of hard bounces """
import time

from notifications_utils.clients.redis.redis_client import RedisClient


def _hard_bounce_key(service_id: str):
    return f"sliding_hard_bounce:{service_id}"


def _notifications_key(service_id: str):
    return f"sliding_notifications:{service_id}"


def _total_notifications_seeded_key(service_id: str):
    return f"total_notifications_seeded:{service_id}"


def _total_hard_bounces_seeded_key(service_id: str):
    return f"total_hard_bounces_seeded:{service_id}"


def _twenty_four_hour_window():
    return 60 * 60 * 24


def _current_time():
    return int(time.time())


class RedisBounceRate:
    def __init__(self, redis=RedisClient()):
        self._redis_client = redis

    def set_sliding_hard_bounce(self, service_id: str):
        current_time = _current_time()
        self._redis_client.add_key_to_sorted_set(_hard_bounce_key(service_id), current_time, current_time)

    def set_sliding_notifications(self, service_id: str):
        current_time = _current_time()
        self._redis_client.add_key_to_sorted_set(_notifications_key(service_id), current_time, current_time)

    def set_total_notifications_seeded(self, service_id: str, time_of_bounce, value):
        # Strip the time down to the hour and convert to epoch
        bounce_epoch = time_of_bounce.replace(minute=0, second=0, microsecond=0).timestamp()
        cache_key = _total_notifications_seeded_key(service_id)
        self._redis_client.add_key_to_sorted_set(cache_key, bounce_epoch, value)
        self._redis_client.expire(cache_key, _twenty_four_hour_window())

    def set_total_hard_bounce_seeded(self, service_id: str, time_of_bounce, value):
        # Strip the time down to the hour and convert to epoch
        bounce_epoch = time_of_bounce.replace(minute=0, second=0, microsecond=0).timestamp()
        cache_key = _total_hard_bounces_seeded_key(service_id)
        self._redis_client.add_key_to_sorted_set(cache_key, bounce_epoch, value)
        self._redis_client.expire(cache_key, _twenty_four_hour_window())

    def get_bounce_rate(self, service_id: str, bounce_window=_twenty_four_hour_window()) -> int:
        total_hard_bounces_sliding = self._redis_client.get_length_of_sorted_set(_hard_bounce_key(service_id), bounce_window)
        total_notifications_sliding = self._redis_client.get_length_of_sorted_set(_notifications_key(service_id), bounce_window)
        total_hard_bounces_seeded = self._redis_client.get_sorted_set_members_by_score(
            _total_hard_bounces_seeded_key(service_id), _current_time() - bounce_window, _current_time()
        )
        total_notifications_seeded = self._redis_client.get_sorted_set_members_by_score(
            _total_notifications_seeded_key(service_id), _current_time() - bounce_window, _current_time()
        )
        return (
            round(
                (total_hard_bounces_sliding + total_hard_bounces_seeded)
                / (total_notifications_sliding + total_notifications_seeded),
                2,
            )
            if (total_notifications_sliding + total_notifications_seeded > 0)
            else 0
        )
