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
def mocked_bounce_rate_client(mocked_redis_client, mocker):
    return build_bounce_rate_client(mocker, mocked_redis_client)


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


def build_bounce_rate_client(mocker, mocked_redis_client):
    bounce_rate_client = RedisBounceRate(mocked_redis_client)
    mocker.patch.object(bounce_rate_client._redis_client, "add_data_to_sorted_set")
    mocker.patch.object(bounce_rate_client._redis_client, "get_length_of_sorted_set", side_effect=[8, 20, 0, 0, 0, 8, 10, 20])
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

    @freeze_time("2001-01-01 12:00:00.000000")
    def test_get_bounce_rate(self, mocked_bounce_rate_client, mocked_service_id):
        answer = mocked_bounce_rate_client.get_bounce_rate(mocked_service_id)
        assert answer == 0.4

        answer = mocked_bounce_rate_client.get_bounce_rate(mocked_service_id)
        assert answer == 0

        answer = mocked_bounce_rate_client.get_bounce_rate(mocked_service_id)
        assert answer == 0

        answer = mocked_bounce_rate_client.get_bounce_rate(mocked_service_id)
        assert answer == 0.5

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

    def test_seeding_complete_flag(self, better_mocked_bounce_rate_client, mocked_service_id):
        assert better_mocked_bounce_rate_client.get_seeding_complete(mocked_service_id) is False
        better_mocked_bounce_rate_client.set_seeding_complete(mocked_service_id)
        assert better_mocked_bounce_rate_client.get_seeding_complete(mocked_service_id)

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