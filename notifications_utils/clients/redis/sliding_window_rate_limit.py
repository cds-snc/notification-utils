"""
Sliding window rate limiting using Redis sorted sets.

Uses a sorted set where each member is a request timestamp and its score is also
the timestamp. This allows efficient removal of entries outside the window and
accurate counting of requests within it.
"""

from time import time
from typing import Optional

from notifications_utils.clients.redis.redis_client import RedisClient


def report_rate_limit_cache_key(service_id):
    return f"report-rate-limit:{service_id}"


def check_and_count_window(redis_client: RedisClient, cache_key: str, window_seconds: int, now: Optional[float] = None) -> int:
    """
    Remove entries older than or equal to window_seconds and return the current
    count of entries within the window. Returns 0 if Redis is inactive.
    """
    if not redis_client.active:
        return 0
    if now is None:
        now = time()
    window_start = now - window_seconds
    pipe = redis_client.redis_store.pipeline()
    pipe.zremrangebyscore(cache_key, "-inf", window_start)
    pipe.zcard(cache_key)
    results = pipe.execute()
    return results[1]


def get_window_oldest_entry(redis_client: RedisClient, cache_key: str):
    """
    Returns the timestamp of the oldest entry in the sorted set, or None if the
    set is empty or Redis is inactive.
    """
    if not redis_client.active:
        return None
    oldest = redis_client.redis_store.zrange(cache_key, 0, 0, withscores=True)
    if oldest:
        return oldest[0][1]
    return None


def record_window_request(redis_client: RedisClient, cache_key: str, window_seconds: int, now: Optional[float] = None) -> None:
    """
    Record a request in the sliding window sorted set and refresh the key expiry.
    No-op if Redis is inactive.
    """
    if not redis_client.active:
        return
    if now is None:
        now = time()
    pipe = redis_client.redis_store.pipeline()
    pipe.zadd(cache_key, {now: now})
    pipe.expire(cache_key, window_seconds + 60)
    pipe.execute()
