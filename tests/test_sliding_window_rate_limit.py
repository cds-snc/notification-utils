import uuid
from time import time

import fakeredis
import pytest
from notifications_utils.clients.redis.redis_client import RedisClient
from notifications_utils.clients.redis.sliding_window_rate_limit import (
    check_and_record_window_request,
    report_rate_limit_cache_key,
)


@pytest.fixture
def fake_redis_client():
    client = RedisClient()
    client.redis_store = fakeredis.FakeStrictRedis(version=6)  # type: ignore
    client.active = True
    return client


@pytest.fixture
def inactive_redis_client():
    client = RedisClient()
    client.active = False
    return client


@pytest.fixture
def cache_key():
    return report_rate_limit_cache_key(str(uuid.uuid4()))


class TestReportRateLimitCacheKey:
    def test_includes_service_id(self):
        service_id = "abc-123"
        assert report_rate_limit_cache_key(service_id) == "report-rate-limit:abc-123"

    def test_different_services_produce_different_keys(self):
        assert report_rate_limit_cache_key("aaa") != report_rate_limit_cache_key("bbb")


class TestCheckAndRecordWindowRequest:
    def test_returns_not_exceeded_when_redis_inactive(self, inactive_redis_client, cache_key):
        exceeded, oldest_ts = check_and_record_window_request(inactive_redis_client, cache_key, 10, 3600)
        assert exceeded is False
        assert oldest_ts is None

    def test_not_exceeded_below_limit(self, fake_redis_client, cache_key):
        now = time()
        for i in range(9):
            exceeded, oldest_ts = check_and_record_window_request(fake_redis_client, cache_key, 10, 3600, now + i * 0.001)
            assert exceeded is False
            assert oldest_ts is None

    def test_not_exceeded_at_exact_limit(self, fake_redis_client, cache_key):
        now = time()
        # Pre-fill 9 entries, then add the 10th — count reaches limit but does not exceed
        for i in range(9):
            fake_redis_client.redis_store.zadd(cache_key, {now - i: now - i})

        exceeded, oldest_ts = check_and_record_window_request(fake_redis_client, cache_key, 10, 3600, now)
        assert exceeded is False
        assert oldest_ts is None

    def test_exceeded_when_over_limit(self, fake_redis_client, cache_key):
        now = time()
        # Pre-fill 10 entries so the next add pushes count to 11.
        # Use now - (i+1) so no member equals `now` (sorted sets deduplicate by member).
        for i in range(10):
            fake_redis_client.redis_store.zadd(cache_key, {now - (i + 1): now - (i + 1)})

        exceeded, oldest_ts = check_and_record_window_request(fake_redis_client, cache_key, 10, 3600, now)
        assert exceeded is True

    def test_oldest_ts_is_populated_when_exceeded(self, fake_redis_client, cache_key):
        now = time()
        oldest = now - 100
        for i in range(9):
            fake_redis_client.redis_store.zadd(cache_key, {oldest - i: oldest - i})
        # one more entry puts us to 10 before the new add
        fake_redis_client.redis_store.zadd(cache_key, {now - 50: now - 50})

        exceeded, oldest_ts = check_and_record_window_request(fake_redis_client, cache_key, 10, 3600, now)
        assert exceeded is True
        # oldest_ts should be the smallest score still in the window
        assert oldest_ts is not None
        assert oldest_ts <= oldest

    def test_expired_entries_are_trimmed_before_counting(self, fake_redis_client, cache_key):
        now = time()
        # 8 old entries outside the window + 1 inside = 9 total before add
        for i in range(8):
            old_ts = now - 7200 - i
            fake_redis_client.redis_store.zadd(cache_key, {old_ts: old_ts})
        fake_redis_client.redis_store.zadd(cache_key, {now - 10: now - 10})

        # After trim, only 1 valid entry + the new one = count 2, not exceeded
        exceeded, oldest_ts = check_and_record_window_request(fake_redis_client, cache_key, 10, 3600, now)
        assert exceeded is False

    def test_entry_at_window_boundary_is_trimmed(self, fake_redis_client, cache_key):
        now = time()
        boundary_ts = now - 3600  # exactly at window start — should be removed
        for i in range(10):
            fake_redis_client.redis_store.zadd(cache_key, {boundary_ts - i: boundary_ts - i})

        # All 10 pre-filled entries fall outside or at the boundary; only the new
        # entry remains after trim, so count == 1 and limit is not exceeded
        exceeded, _ = check_and_record_window_request(fake_redis_client, cache_key, 10, 3600, now)
        assert exceeded is False

    def test_sets_key_expiry(self, fake_redis_client, cache_key):
        check_and_record_window_request(fake_redis_client, cache_key, 10, 3600)

        ttl = fake_redis_client.redis_store.ttl(cache_key)
        # expiry is window_seconds + 60; allow small margin for test execution time
        assert 3600 <= ttl <= 3661

    def test_rejected_request_occupies_a_slot(self, fake_redis_client, cache_key):
        now = time()
        # Fill to the brim so the next add exceeds the limit.
        # Use now - (i+1) so no member equals `now`.
        for i in range(10):
            fake_redis_client.redis_store.zadd(cache_key, {now - (i + 1): now - (i + 1)})

        exceeded, _ = check_and_record_window_request(fake_redis_client, cache_key, 10, 3600, now)
        assert exceeded is True

        # The rejected entry was still added; set now has 11 members
        count = fake_redis_client.redis_store.zcard(cache_key)
        assert count == 11

    def test_uses_current_time_when_now_not_provided(self, fake_redis_client, cache_key):
        before = time()
        check_and_record_window_request(fake_redis_client, cache_key, 10, 3600)
        after = time()

        entries = fake_redis_client.redis_store.zrange(cache_key, 0, -1, withscores=True)
        assert len(entries) == 1
        assert before <= entries[0][1] <= after
