import uuid
import pytest
from unittest.mock import Mock
from freezegun import freeze_time

from notifications_utils.clients.redis.bounce_rate import (
    RedisBounceRate,
    _hard_bounce_total_key,
    _current_time,
    _total_notifications_key,
)
from notifications_utils.clients.redis.redis_client import RedisClient


@pytest.fixture(scope="function")
def mocked_redis_pipeline():
    return Mock()


@pytest.fixture(scope="function")
def mocked_redis_client(app, mocked_redis_pipeline, mocker):
    app.config["REDIS_ENABLED"] = True
    return build_redis_client(app, mocked_redis_pipeline, mocker)


def build_redis_client(app, mocked_redis_pipeline, mocker):
    redis_client = RedisClient()
    redis_client.init_app(app)
    return redis_client


@pytest.fixture(scope="function")
def mocked_bounce_rate_client(mocked_redis_client, mocker):
    return build_bounce_rate_client(mocker, mocked_redis_client)


def build_bounce_rate_client(mocker, mocked_redis_client):
    bounce_rate_client = RedisBounceRate(mocked_redis_client)
    mocker.patch.object(bounce_rate_client._redis_client, "add_key_to_sorted_set")
    mocker.patch.object(bounce_rate_client._redis_client, "get_length_of_sorted_set", side_effect=[10, 20, 3, 0, 0, 8])
    return bounce_rate_client


@pytest.fixture(scope="function")
def mocked_service_id():
    return str(uuid.uuid4())


class TestRedisBounceRate:
    @freeze_time("2001-01-01 12:00:00.000000")
    def test_set_hard_bounce(self, mocked_bounce_rate_client, mocked_service_id):
        mocked_bounce_rate_client.set_hard_bounce(mocked_service_id)
        mocked_bounce_rate_client._redis_client.add_key_to_sorted_set.assert_called_with(
            _hard_bounce_total_key(mocked_service_id), _current_time(), _current_time()
        )

    @freeze_time("2001-01-01 12:00:00.000000")
    def test_set_total_notifications(self, mocked_bounce_rate_client, mocked_service_id):
        mocked_bounce_rate_client.set_total_notifications(mocked_service_id)
        mocked_bounce_rate_client._redis_client.add_key_to_sorted_set.assert_called_with(
            _total_notifications_key(mocked_service_id), _current_time(), _current_time()
        )

    @freeze_time("2001-01-01 12:00:00.000000")
    def test_get_bounce_rate(self, mocked_bounce_rate_client, mocked_service_id):
        answer = mocked_bounce_rate_client.get_bounce_rate(mocked_service_id)
        assert answer == 0.5

        answer = mocked_bounce_rate_client.get_bounce_rate(mocked_service_id)
        assert answer == 0

        answer = mocked_bounce_rate_client.get_bounce_rate(mocked_service_id)
        assert answer == 0
