"""This module is used to calculate the bounce rate for a service. It uses Redis to store the total number of hard bounces """
import time

from clients.redis import (
    add_key_to_sorted_set,
    get_length_of_sorted_set,
)
from redis import Redis
from flask import current_app


def _hard_bounce_total_key(service_id):
    return f"hard_bounce_total:{service_id}"


def _total_notifications_key(service_id):
    return f"total_notifications:{service_id}"


def _twenty_four_hour_window():
    return 60 * 60 * 24


def _current_time():
    return int(time.time())


class RedisBounceRate:
    def init_app(self, redis: Redis):
        self._redis_client = redis

    def set_hard_bounce(self, service_id):
        add_key_to_sorted_set(self._redis_client, _hard_bounce_total_key(service_id), _current_time())

    def set_total_notifications(self, service_id):
        add_key_to_sorted_set(self._redis_client, _total_notifications_key(service_id), _current_time())

    def get_bounce_rate(self, service_id, bounce_window=_twenty_four_hour_window()):
        current_app.logger.info(f"Getting bounce rate for {service_id}")
        total_hard_bounces = get_length_of_sorted_set(self._redis_client, _hard_bounce_total_key(service_id), bounce_window)
        total_notifications = get_length_of_sorted_set(self._redis_client, _total_notifications_key(service_id), bounce_window)
        return round(total_hard_bounces / total_notifications, 2) if total_notifications else 0
