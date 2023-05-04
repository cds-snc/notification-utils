import datetime
import uuid
import pytest
from unittest.mock import Mock
import fakeredis
from freezegun import freeze_time

from notifications_utils.clients.redis.bounce_rate import (
    _current_timestamp_ms,
    RedisBounceRate,
    hard_bounce_key,
    total_notifications_key,
)
from notifications_utils.clients.redis.redis_client import RedisClient


@pytest.fixture(scope="function")
def mocked_redis_pipeline():
    return Mock()


@pytest.fixture(scope="function")
def mocked_redis_client(app, mocked_redis_pipeline, mocker):
    app.config["REDIS_ENABLED"] = True
    app.config["BR_CRITICAL_PERCENTAGE"] = 0.1
    app.config["BR_WARNING_PERCENTAGE"] = 0.05
    return build_redis_client(app, mocked_redis_pipeline, mocker)


@pytest.fixture(scope="function")
def better_mocked_redis_client(app):
    app.config["REDIS_ENABLED"] = True
    redis_client = RedisClient()
    redis_client.redis_store = fakeredis.FakeStrictRedis(version=6)  # type: ignore
    redis_client.active = True
    return redis_client


def build_redis_client(app, mocked_redis_pipeline, mocker):
    redis_client = RedisClient()
    redis_client.init_app(app)
    return redis_client


@pytest.fixture(scope="function")
def mocked_bounce_rate_client(app, better_mocked_redis_client, mocker):
    return build_bounce_rate_client(mocker, better_mocked_redis_client)


@pytest.fixture(scope="function")
def better_mocked_bounce_rate_client(better_mocked_redis_client, mocker):
    return RedisBounceRate(better_mocked_redis_client)


@pytest.fixture(scope="function")
def mocked_seeded_data_hours():
    hour_delta = datetime.timedelta(hours=1)
    hours = [datetime.datetime.now() - hour_delta]
    for i in range(23):
        hours.append(hours[i] - hour_delta)
    return hours


def build_bounce_rate_client(mocker, better_mocked_redis_client):
    bounce_rate_client = RedisBounceRate(better_mocked_redis_client)
    mocker.patch.object(bounce_rate_client._redis_client, "add_data_to_sorted_set")
    mocker.patch.object(bounce_rate_client._redis_client, "expire")
    return bounce_rate_client


@pytest.fixture(scope="function")
def mocked_service_id():
    return str(uuid.uuid4())


class TestRedisBounceRate:
    @freeze_time("2001-01-01 12:00:00.000000")
    def test_set_hard_bounce(self, mocked_bounce_rate_client, mocked_service_id):
        mocked_bounce_rate_client.set_sliding_hard_bounce(mocked_service_id)
        mocked_bounce_rate_client._redis_client.add_data_to_sorted_set.assert_called_with(
            hard_bounce_key(mocked_service_id), {_current_timestamp_ms(): _current_timestamp_ms()}
        )

    @freeze_time("2001-01-01 12:00:00.000000")
    def test_set_total_notifications(self, mocked_bounce_rate_client, mocked_service_id):
        mocked_bounce_rate_client.set_sliding_notifications(mocked_service_id)
        mocked_bounce_rate_client._redis_client.add_data_to_sorted_set.assert_called_with(
            total_notifications_key(mocked_service_id), {_current_timestamp_ms(): _current_timestamp_ms()}
        )

    @pytest.mark.parametrize(
        "total_bounces, total_notifications, expected_bounce_rate",
        [
            (10, 100, 0.1),
            (5, 100, 0.05),
            (5, 1000, 0.005),  # inexact b/c we are rounding to 2 decimal places
            (5, 10000, 0.0005),  # inexact b/c we are rounding to 2 decimal places
            (5, 100000, 0.00005),  # inexact b/c we are rounding to 2 decimal places
            (0, 100, 0),
            (40, 100, 0.4),
            (0, 0, 0),
            (0, 1, 0),
            (1, 1, 1.0),
        ],
    )
    def test_get_bounce_rate(
        self, better_mocked_bounce_rate_client, mocked_service_id, total_bounces, total_notifications, expected_bounce_rate
    ):

        better_mocked_bounce_rate_client.clear_bounce_rate_data(mocked_service_id)
        now = int(datetime.datetime.now().timestamp() * 1000.0)

        notification_data = [(now - n, now - n) for n in range(total_notifications)]
        bounce_data = [(now - n, now - n) for n in range(total_bounces)]

        better_mocked_bounce_rate_client.set_notifications_seeded(mocked_service_id, dict(notification_data))
        better_mocked_bounce_rate_client.set_hard_bounce_seeded(mocked_service_id, dict(bounce_data))

        bounce_rate = better_mocked_bounce_rate_client.get_bounce_rate(mocked_service_id)
        assert bounce_rate == expected_bounce_rate

    def test_set_total_hard_bounce_seeded(
        self,
        mocked_bounce_rate_client,
        mocked_service_id,
    ):
        seeded_data = {12345: 12345, 12346: 12346}
        mocked_bounce_rate_client.set_hard_bounce_seeded(mocked_service_id, seeded_data)
        mocked_bounce_rate_client._redis_client.add_data_to_sorted_set.assert_called_with(
            hard_bounce_key(mocked_service_id), seeded_data
        )

    def test_set_total_notifications_seeded(self, mocked_bounce_rate_client, mocked_service_id):
        seeded_data = {12345: 12345, 12346: 12346}
        mocked_bounce_rate_client.set_notifications_seeded(mocked_service_id, seeded_data)
        mocked_bounce_rate_client._redis_client.add_data_to_sorted_set.assert_called_with(
            total_notifications_key(mocked_service_id), seeded_data
        )

    def test_seeding_started_flag(self, better_mocked_bounce_rate_client, mocked_service_id):
        assert better_mocked_bounce_rate_client.get_seeding_started(mocked_service_id) is False
        better_mocked_bounce_rate_client.set_seeding_started(mocked_service_id)
        assert better_mocked_bounce_rate_client.get_seeding_started(mocked_service_id)

    def test_clear_bounce_rate_data(self, better_mocked_bounce_rate_client, mocked_service_id):
        better_mocked_bounce_rate_client.set_sliding_notifications(mocked_service_id)
        better_mocked_bounce_rate_client.set_sliding_hard_bounce(mocked_service_id)

        total_hard_bounces = better_mocked_bounce_rate_client._redis_client.get_length_of_sorted_set(
            hard_bounce_key(mocked_service_id), min_score=0, max_score="+inf"
        )
        assert total_hard_bounces == 1
        total_notifications = better_mocked_bounce_rate_client._redis_client.get_length_of_sorted_set(
            total_notifications_key(mocked_service_id), min_score=0, max_score="+inf"
        )
        assert total_notifications == 1

        better_mocked_bounce_rate_client.clear_bounce_rate_data(mocked_service_id)

        total_hard_bounces = better_mocked_bounce_rate_client._redis_client.get_length_of_sorted_set(
            hard_bounce_key(mocked_service_id), min_score=0, max_score="+inf"
        )
        assert total_hard_bounces == 0
        total_notifications = better_mocked_bounce_rate_client._redis_client.get_length_of_sorted_set(
            total_notifications_key(mocked_service_id), min_score=0, max_score="+inf"
        )
        assert total_notifications == 0

    @pytest.mark.parametrize(
        "total_bounces, total_notifications, expected_status, volume_threshold",
        [
            (10, 100, "critical", 75),
            (5, 100, "warning", 75),
            (0, 100, "normal", 75),
            (0, 0, "normal", 75),
            (0, 1, "normal", 75),
            (1, 1, "normal", 75),
        ],
    )
    def test_check_bounce_rate_critical(
        app,
        better_mocked_bounce_rate_client,
        mocked_service_id,
        total_bounces,
        total_notifications,
        expected_status,
        volume_threshold,
    ):
        better_mocked_bounce_rate_client._critical_threshold = 0.1
        better_mocked_bounce_rate_client._warning_threshold = 0.05
        better_mocked_bounce_rate_client.clear_bounce_rate_data(mocked_service_id)
        now = int(datetime.datetime.now().timestamp() * 1000.0)

        notification_data = [(now - n, now - n) for n in range(total_notifications)]
        bounce_data = [(now - n, now - n) for n in range(total_bounces)]

        better_mocked_bounce_rate_client.set_notifications_seeded(mocked_service_id, dict(notification_data))
        better_mocked_bounce_rate_client.set_hard_bounce_seeded(mocked_service_id, dict(bounce_data))

        bounce_status = better_mocked_bounce_rate_client.check_bounce_rate_status(
            mocked_service_id, volume_threshold=volume_threshold
        )
        assert bounce_status == expected_status
