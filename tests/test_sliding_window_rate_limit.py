import uuid
from time import time

import fakeredis
import pytest
from notifications_utils.clients.redis.redis_client import RedisClient
from notifications_utils.clients.redis.sliding_window_rate_limit import (
    check_and_count_window,
    get_window_oldest_entry,
    record_window_request,
    report_rate_limit_cache_key,
)


@pytest.fixture
def fake_redis_client():
    client = RedisClient()
    client.redis_store = fakeredis.FakeStrictRedis(version=6)
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


class TestCheckAndCountWindow:
    def test_returns_zero_when_redis_inactive(self, inactive_redis_client, cache_key):
        assert check_and_count_window(inactive_redis_client, cache_key, 3600) == 0

    def test_returns_zero_for_empty_set(self, fake_redis_client, cache_key):
        assert check_and_count_window(fake_redis_client, cache_key, 3600) == 0

    def test_counts_entries_within_window(self, fake_redis_client, cache_key):
        now = time()
        # Add 3 entries inside the window
        for i in range(3):
            ts = now - i * 10
            fake_redis_client.redis_store.zadd(cache_key, {ts: ts})

        count = check_and_count_window(fake_redis_client, cache_key, 3600, now)
        assert count == 3

    def test_removes_entries_outside_window(self, fake_redis_client, cache_key):
        now = time()
        old_ts = now - 7200  # 2 hours ago — outside a 1-hour window
        recent_ts = now - 60  # 1 minute ago — inside window

        fake_redis_client.redis_store.zadd(cache_key, {old_ts: old_ts, recent_ts: recent_ts})

        count = check_and_count_window(fake_redis_client, cache_key, 3600, now)
        assert count == 1

        # Old entry should be gone from the set
        remaining = fake_redis_client.redis_store.zrange(cache_key, 0, -1, withscores=True)
        assert len(remaining) == 1
        assert abs(remaining[0][1] - recent_ts) < 0.001

    def test_entry_exactly_at_window_boundary_is_removed(self, fake_redis_client, cache_key):
        now = time()
        boundary_ts = now - 3600  # exactly at the start of a 1-hour window
        inside_ts = now - 3599

        fake_redis_client.redis_store.zadd(cache_key, {boundary_ts: boundary_ts, inside_ts: inside_ts})

        count = check_and_count_window(fake_redis_client, cache_key, 3600, now)
        assert count == 1

    def test_uses_current_time_when_now_not_provided(self, fake_redis_client, cache_key):
        ts = time() - 10
        fake_redis_client.redis_store.zadd(cache_key, {ts: ts})

        count = check_and_count_window(fake_redis_client, cache_key, 3600)
        assert count == 1


class TestGetWindowOldestEntry:
    def test_returns_none_when_redis_inactive(self, inactive_redis_client, cache_key):
        assert get_window_oldest_entry(inactive_redis_client, cache_key) is None

    def test_returns_none_for_empty_set(self, fake_redis_client, cache_key):
        assert get_window_oldest_entry(fake_redis_client, cache_key) is None

    def test_returns_oldest_timestamp(self, fake_redis_client, cache_key):
        now = time()
        oldest = now - 500
        newer = now - 200
        newest = now - 50

        fake_redis_client.redis_store.zadd(cache_key, {oldest: oldest, newer: newer, newest: newest})

        result = get_window_oldest_entry(fake_redis_client, cache_key)
        assert abs(result - oldest) < 0.001

    def test_returns_single_entry(self, fake_redis_client, cache_key):
        now = time()
        fake_redis_client.redis_store.zadd(cache_key, {now: now})

        result = get_window_oldest_entry(fake_redis_client, cache_key)
        assert abs(result - now) < 0.001


class TestRecordWindowRequest:
    def test_no_op_when_redis_inactive(self, inactive_redis_client, cache_key):
        # Should not raise
        record_window_request(inactive_redis_client, cache_key, 3600)

    def test_adds_entry_to_sorted_set(self, fake_redis_client, cache_key):
        now = time()
        record_window_request(fake_redis_client, cache_key, 3600, now)

        entries = fake_redis_client.redis_store.zrange(cache_key, 0, -1, withscores=True)
        assert len(entries) == 1
        assert abs(entries[0][1] - now) < 0.001

    def test_sets_key_expiry(self, fake_redis_client, cache_key):
        record_window_request(fake_redis_client, cache_key, 3600)

        ttl = fake_redis_client.redis_store.ttl(cache_key)
        # expiry is window + 60; allow a small margin for test execution time
        assert 3600 <= ttl <= 3661

    def test_multiple_requests_accumulate(self, fake_redis_client, cache_key):
        now = time()
        for i in range(5):
            record_window_request(fake_redis_client, cache_key, 3600, now + i * 0.001)

        entries = fake_redis_client.redis_store.zrange(cache_key, 0, -1)
        assert len(entries) == 5

    def test_uses_current_time_when_now_not_provided(self, fake_redis_client, cache_key):
        before = time()
        record_window_request(fake_redis_client, cache_key, 3600)
        after = time()

        entries = fake_redis_client.redis_store.zrange(cache_key, 0, -1, withscores=True)
        assert len(entries) == 1
        assert before <= entries[0][1] <= after


class TestSlidingWindowIntegration:
    def test_full_flow_within_limit(self, fake_redis_client, cache_key):
        now = time()
        for i in range(9):
            count = check_and_count_window(fake_redis_client, cache_key, 3600, now)
            assert count < 10
            record_window_request(fake_redis_client, cache_key, 3600, now + i * 0.001)

    def test_full_flow_at_limit(self, fake_redis_client, cache_key):
        now = time()
        # Pre-fill with 10 entries
        for i in range(10):
            fake_redis_client.redis_store.zadd(cache_key, {now - i: now - i})

        count = check_and_count_window(fake_redis_client, cache_key, 3600, now)
        assert count == 10

    def test_expired_entries_bring_count_below_limit(self, fake_redis_client, cache_key):
        now = time()
        # 8 old entries outside window + 5 recent entries inside window
        for i in range(8):
            old_ts = now - 7200 - i
            fake_redis_client.redis_store.zadd(cache_key, {old_ts: old_ts})
        for i in range(5):
            recent_ts = now - i * 10
            fake_redis_client.redis_store.zadd(cache_key, {recent_ts: recent_ts})

        count = check_and_count_window(fake_redis_client, cache_key, 3600, now)
        assert count == 5
