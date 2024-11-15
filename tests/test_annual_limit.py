import uuid
from datetime import datetime
from unittest.mock import Mock

import fakeredis
import pytest
from freezegun import freeze_time
from notifications_utils.clients.redis.annual_limit import (
    EMAIL_DELIVERED,
    EMAIL_FAILED,
    NEAR_EMAIL_LIMIT,
    NEAR_SMS_LIMIT,
    OVER_EMAIL_LIMIT,
    OVER_SMS_LIMIT,
    SMS_DELIVERED,
    SMS_FAILED,
    RedisAnnualLimit,
    annual_limit_notifications_key,
    annual_limit_status_key,
)
from notifications_utils.clients.redis.redis_client import RedisClient


@pytest.fixture(scope="function")
def mock_notification_count_types():
    return [SMS_DELIVERED, EMAIL_DELIVERED, SMS_FAILED, EMAIL_FAILED]


@pytest.fixture(scope="function")
def mock_annual_limit_statuses():
    return [NEAR_SMS_LIMIT, NEAR_EMAIL_LIMIT, OVER_SMS_LIMIT, OVER_EMAIL_LIMIT]


@pytest.fixture(scope="function")
def mocked_redis_pipeline():
    return Mock()


@pytest.fixture
def mock_redis_client(app, mocked_redis_pipeline, mocker):
    app.config["REDIS_ENABLED"] = True
    return build_redis_client(app, mocked_redis_pipeline, mocker)


@pytest.fixture(scope="function")
def better_mocked_redis_client(app):
    app.config["REDIS_ENABLED"] = True
    redis_client = RedisClient()
    redis_client.redis_store = fakeredis.FakeStrictRedis(version=6)  # type: ignore
    redis_client.active = True
    return redis_client


@pytest.fixture
def redis_annual_limit(mock_redis_client):
    return RedisAnnualLimit(mock_redis_client)


def build_redis_client(app, mocked_redis_pipeline, mocker):
    redis_client = RedisClient()
    redis_client.init_app(app)
    return redis_client


def build_annual_limit_client(mocker, better_mocked_redis_client):
    annual_limit_client = RedisAnnualLimit(better_mocked_redis_client)
    return annual_limit_client


@pytest.fixture(scope="function")
def mock_annual_limit_client(better_mocked_redis_client, mocker):
    return RedisAnnualLimit(better_mocked_redis_client)


@pytest.fixture(scope="function")
def mocked_service_id():
    return str(uuid.uuid4())


def test_notifications_key(mocked_service_id):
    expected_key = f"annual-limit:{mocked_service_id}:notifications"
    assert annual_limit_notifications_key(mocked_service_id) == expected_key


def test_annual_limits_key(mocked_service_id):
    expected_key = f"annual-limit:{mocked_service_id}:status"
    assert annual_limit_status_key(mocked_service_id) == expected_key


@pytest.mark.parametrize(
    "increment_by, metric",
    [
        (1, SMS_DELIVERED),
        (1, EMAIL_DELIVERED),
        (1, SMS_FAILED),
        (1, EMAIL_FAILED),
        (2, SMS_DELIVERED),
        (2, EMAIL_DELIVERED),
        (2, SMS_FAILED),
        (2, EMAIL_FAILED),
    ],
)
def test_increment_notification_count(mock_annual_limit_client, mocked_service_id, metric, increment_by):
    for _ in range(increment_by):
        mock_annual_limit_client.increment_notification_count(mocked_service_id, metric)
    counts = mock_annual_limit_client.get_all_notification_counts(mocked_service_id)
    assert int(counts[metric]) == increment_by


def test_get_notification_count(mock_annual_limit_client, mocked_service_id):
    mock_annual_limit_client.increment_notification_count(mocked_service_id, SMS_DELIVERED)
    result = mock_annual_limit_client.get_notification_count(mocked_service_id, SMS_DELIVERED)
    assert result == 1


def test_get_notification_count_returns_none_when_field_does_not_exist(mock_annual_limit_client, mocked_service_id):
    assert mock_annual_limit_client.get_notification_count(mocked_service_id, SMS_DELIVERED) is None


def test_get_all_notification_counts(mock_annual_limit_client, mock_notification_count_types, mocked_service_id):
    for field in mock_notification_count_types:
        mock_annual_limit_client.increment_notification_count(mocked_service_id, field)
    assert len(mock_annual_limit_client.get_all_notification_counts(mocked_service_id)) == 4


def test_get_all_notification_counts_returns_none_if_fields_do_not_exist(mock_annual_limit_client, mocked_service_id):
    assert mock_annual_limit_client.get_all_notification_counts(mocked_service_id) is None


def test_clear_notification_counts(mock_annual_limit_client, mock_notification_count_types, mocked_service_id):
    for field in mock_notification_count_types:
        mock_annual_limit_client.increment_notification_count(mocked_service_id, field)
    assert len(mock_annual_limit_client.get_all_notification_counts(mocked_service_id)) == 4
    mock_annual_limit_client.clear_notification_counts(mocked_service_id)
    assert mock_annual_limit_client.get_all_notification_counts(mocked_service_id) is None


@pytest.mark.parametrize(
    "service_ids",
    [
        [
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            str(uuid.uuid4()),
        ]
    ],
)
def test_bulk_reset_notification_counts(mock_annual_limit_client, mock_notification_count_types, service_ids):
    for service_id in service_ids:
        for field in mock_notification_count_types:
            mock_annual_limit_client.increment_notification_count(service_id, field)
        assert len(mock_annual_limit_client.get_all_notification_counts(service_id)) == 4

    mock_annual_limit_client.reset_all_notification_counts()

    for service_id in service_ids:
        assert mock_annual_limit_client.get_all_notification_counts(service_id) is None


def test_set_annual_limit_status(mock_annual_limit_client, mocked_service_id):
    mock_annual_limit_client.set_annual_limit_status(mocked_service_id, NEAR_SMS_LIMIT, datetime.utcnow())
    result = mock_annual_limit_client.get_annual_limit_status(mocked_service_id, NEAR_SMS_LIMIT)
    assert result == datetime.utcnow().strftime("%Y-%m-%d")


@freeze_time("2024-10-25 12:00:00.000000")
def test_get_annual_limit_status(mock_annual_limit_client, mocked_service_id):
    near_limit_date = datetime.utcnow()
    mock_annual_limit_client.set_annual_limit_status(mocked_service_id, NEAR_SMS_LIMIT, near_limit_date)
    result = mock_annual_limit_client.get_annual_limit_status(mocked_service_id, NEAR_SMS_LIMIT)
    assert result == near_limit_date.strftime("%Y-%m-%d")


def test_get_annual_limit_status_returns_none_when_fields_do_not_exist(mock_annual_limit_client, mocked_service_id):
    assert mock_annual_limit_client.get_annual_limit_status(mocked_service_id, NEAR_SMS_LIMIT) is None


@freeze_time("2024-10-25 12:00:00.000000")
def test_get_all_annual_limit_statuses(mock_annual_limit_client, mock_annual_limit_statuses, mocked_service_id):
    for status in mock_annual_limit_statuses:
        mock_annual_limit_client.set_annual_limit_status(mocked_service_id, status, datetime.utcnow())
    assert len(mock_annual_limit_client.get_all_annual_limit_statuses(mocked_service_id)) == 4


def test_get_all_annual_limit_statuses_returns_none_when_fields_do_not_exist(mock_annual_limit_client, mocked_service_id):
    assert mock_annual_limit_client.get_all_annual_limit_statuses(mocked_service_id) is None


@freeze_time("2024-10-25 12:00:00.000000")
def test_clear_annual_limit_statuses(mock_annual_limit_client, mock_annual_limit_statuses, mocked_service_id):
    for status in mock_annual_limit_statuses:
        mock_annual_limit_client.set_annual_limit_status(mocked_service_id, status, datetime.utcnow())
    assert len(mock_annual_limit_client.get_all_annual_limit_statuses(mocked_service_id)) == 4
    mock_annual_limit_client.clear_annual_limit_statuses(mocked_service_id)
    assert mock_annual_limit_client.get_all_annual_limit_statuses(mocked_service_id) is None


@freeze_time("2024-10-25 12:00:00.000000")
@pytest.mark.parametrize("seeded_at_value, expected_value", [(b"2024-10-25", True), (None, False)])
def test_was_seeded_today(mock_annual_limit_client, seeded_at_value, expected_value, mocked_service_id, mocker):
    mocker.patch.object(mock_annual_limit_client._redis_client, "get_hash_field", return_value=seeded_at_value)
    result = mock_annual_limit_client.was_seeded_today(mocked_service_id)
    assert result == expected_value


@freeze_time("2024-10-25 12:00:00.000000")
def test_set_seeded_at(mock_annual_limit_client, mocked_service_id):
    mock_annual_limit_client.set_seeded_at(mocked_service_id)
    result = mock_annual_limit_client.get_seeded_at(mocked_service_id)
    assert result == datetime.utcnow().strftime("%Y-%m-%d")


@freeze_time("2024-10-25 12:00:00.000000")
@pytest.mark.parametrize("seeded_at_value, expected_value", [(b"2024-10-25", "2024-10-25"), (None, None)])
def test_get_seeded_at(mock_annual_limit_client, seeded_at_value, expected_value, mocked_service_id, mocker):
    mocker.patch.object(mock_annual_limit_client._redis_client, "get_hash_field", return_value=seeded_at_value)
    result = mock_annual_limit_client.get_seeded_at(mocked_service_id)
    assert result == expected_value


def test_get_seeded_at_returns_none_when_field_does_not_exist(mock_annual_limit_client, mocked_service_id):
    assert mock_annual_limit_client.get_seeded_at(mocked_service_id) is None


@freeze_time("2024-10-25 12:00:00.000000")
def test_set_nearing_sms_limit(mock_annual_limit_client, mocked_service_id):
    mock_annual_limit_client.set_nearing_sms_limit(mocked_service_id)
    result = mock_annual_limit_client.get_annual_limit_status(mocked_service_id, NEAR_SMS_LIMIT)
    assert result == datetime.utcnow().strftime("%Y-%m-%d")


@freeze_time("2024-10-25 12:00:00.000000")
def test_set_over_sms_limit(mock_annual_limit_client, mocked_service_id):
    mock_annual_limit_client.set_over_sms_limit(mocked_service_id)
    result = mock_annual_limit_client.get_annual_limit_status(mocked_service_id, OVER_SMS_LIMIT)
    assert result == datetime.utcnow().strftime("%Y-%m-%d")


@freeze_time("2024-10-25 12:00:00.000000")
def test_set_nearing_email_limit(mock_annual_limit_client, mocked_service_id):
    mock_annual_limit_client.set_nearing_email_limit(mocked_service_id)
    result = mock_annual_limit_client.get_annual_limit_status(mocked_service_id, NEAR_EMAIL_LIMIT)
    assert result == datetime.utcnow().strftime("%Y-%m-%d")


@freeze_time("2024-10-25 12:00:00.000000")
def test_set_over_email_limit(mock_annual_limit_client, mocked_service_id):
    mock_annual_limit_client.set_over_email_limit(mocked_service_id)
    result = mock_annual_limit_client.get_annual_limit_status(mocked_service_id, OVER_EMAIL_LIMIT)
    assert result == datetime.utcnow().strftime("%Y-%m-%d")


def test_increment_sms_delivered(mock_annual_limit_client, mock_notification_count_types, mocked_service_id):
    for field in mock_notification_count_types:
        mock_annual_limit_client.increment_notification_count(mocked_service_id, field)

    mock_annual_limit_client.increment_sms_delivered(mocked_service_id)

    assert mock_annual_limit_client.get_notification_count(mocked_service_id, SMS_DELIVERED) == 2
    for field in mock_notification_count_types:
        if field != SMS_DELIVERED:
            assert mock_annual_limit_client.get_notification_count(mocked_service_id, field) == 1


def test_increment_sms_failed(mock_annual_limit_client, mock_notification_count_types, mocked_service_id):
    for field in mock_notification_count_types:
        mock_annual_limit_client.increment_notification_count(mocked_service_id, field)

    mock_annual_limit_client.increment_sms_failed(mocked_service_id)

    assert mock_annual_limit_client.get_notification_count(mocked_service_id, SMS_FAILED) == 2
    for field in mock_notification_count_types:
        if field != SMS_FAILED:
            assert mock_annual_limit_client.get_notification_count(mocked_service_id, field) == 1


def test_increment_email_delivered(mock_annual_limit_client, mock_notification_count_types, mocked_service_id):
    for field in mock_notification_count_types:
        mock_annual_limit_client.increment_notification_count(mocked_service_id, field)

    mock_annual_limit_client.increment_email_delivered(mocked_service_id)

    assert mock_annual_limit_client.get_notification_count(mocked_service_id, EMAIL_DELIVERED) == 2
    for field in mock_notification_count_types:
        if field != EMAIL_DELIVERED:
            assert mock_annual_limit_client.get_notification_count(mocked_service_id, field) == 1


def test_increment_email_failed(mock_annual_limit_client, mock_notification_count_types, mocked_service_id):
    for field in mock_notification_count_types:
        mock_annual_limit_client.increment_notification_count(mocked_service_id, field)

    mock_annual_limit_client.increment_email_failed(mocked_service_id)

    assert mock_annual_limit_client.get_notification_count(mocked_service_id, EMAIL_FAILED) == 2
    for field in mock_notification_count_types:
        if field != EMAIL_FAILED:
            assert mock_annual_limit_client.get_notification_count(mocked_service_id, field) == 1


@freeze_time("2024-10-25 12:00:00.000000")
def test_check_has_warning_been_sent(mock_annual_limit_client, mocked_service_id):
    mock_annual_limit_client.set_annual_limit_status(mocked_service_id, NEAR_SMS_LIMIT, datetime.utcnow())
    mock_annual_limit_client.set_annual_limit_status(mocked_service_id, NEAR_EMAIL_LIMIT, datetime.utcnow())

    assert mock_annual_limit_client.check_has_warning_been_sent(mocked_service_id, "sms") == datetime.utcnow().strftime(
        "%Y-%m-%d"
    )
    assert mock_annual_limit_client.check_has_warning_been_sent(mocked_service_id, "email") == datetime.utcnow().strftime(
        "%Y-%m-%d"
    )


@freeze_time("2024-10-25 12:00:00.000000")
def test_check_has_over_limit_been_sent(mock_annual_limit_client, mocked_service_id):
    mock_annual_limit_client.set_annual_limit_status(mocked_service_id, OVER_SMS_LIMIT, datetime.utcnow())
    mock_annual_limit_client.set_annual_limit_status(mocked_service_id, OVER_EMAIL_LIMIT, datetime.utcnow())

    assert mock_annual_limit_client.check_has_over_limit_been_sent(mocked_service_id, "sms") == datetime.utcnow().strftime(
        "%Y-%m-%d"
    )
    assert mock_annual_limit_client.check_has_over_limit_been_sent(mocked_service_id, "email") == datetime.utcnow().strftime(
        "%Y-%m-%d"
    )
