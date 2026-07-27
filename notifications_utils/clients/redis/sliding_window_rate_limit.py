"""
Sliding window rate limiting using Redis sorted sets.

Uses a sorted set where each member is a request timestamp and its score is also
the timestamp. This allows efficient removal of entries outside the window and
accurate counting of requests within it.
"""

from time import time
from typing import Optional, Tuple

from notifications_utils.clients.redis.redis_client import RedisClient


def report_rate_limit_cache_key(service_id):
    return f"report-rate-limit:{service_id}"


def check_and_record_window_request(
    redis_client: RedisClient,
    cache_key: str,
    limit: int,
    window_seconds: int,
    now: Optional[float] = None,
) -> Tuple[bool, Optional[float]]:
    """
    Atomically record a request and check whether the rate limit has been exceeded.

    Uses a single pipeline (zadd -> zremrangebyscore -> zcard -> zrange -> expire)
    so the record and check happen in the same round-trip, matching the pattern of
    RedisClient.exceeded_rate_limit.

    Because the entry is added before the count is inspected, a rejected request
    still occupies a slot in the window.  This prevents concurrent callers from all
    observing the same pre-add count and all proceeding past the limit.

    Returns:
        (exceeded, oldest_ts)
        - exceeded:   True if the count after adding exceeds the limit.
        - oldest_ts:  Timestamp of the oldest entry when exceeded (used by the
                      caller to compute reset_at / Retry-After), or None when the
                      limit is not exceeded or Redis is inactive.
    """
    if not redis_client.active:
        return False, None
    if now is None:
        now = time()
    window_start = now - window_seconds
    pipe = redis_client.redis_store.pipeline()
    pipe.zadd(cache_key, {now: now})
    pipe.zremrangebyscore(cache_key, "-inf", window_start)
    pipe.zcard(cache_key)
    pipe.zrange(cache_key, 0, 0, withscores=True)
    pipe.expire(cache_key, window_seconds + 60)
    results = pipe.execute()
    count = results[2]
    if count > limit:
        oldest_entries = results[3]
        oldest_ts = oldest_entries[0][1] if oldest_entries else None
        return True, oldest_ts
    return False, None
