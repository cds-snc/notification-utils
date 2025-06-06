import uuid
from datetime import datetime
from unittest.mock import Mock

import fakeredis
import pytest
from freezegun import freeze_time
from notifications_utils.clients.redis.annual_limit import (
    EMAIL_DELIVERED,
    EMAIL_DELIVERED_TODAY,
    EMAIL_FAILED,
    EMAIL_FAILED_TODAY,
    NEAR_EMAIL_LIMIT,
    NEAR_SMS_LIMIT,
    NOTIFICATION_FIELDS,
    NOTIFICATION_FIELDS_V2,
    OVER_EMAIL_LIMIT,
    OVER_SMS_LIMIT,
    SMS_DELIVERED,
    SMS_DELIVERED_TODAY,
    SMS_FAILED,
    SMS_FAILED_TODAY,
    STATUS_FIELDS,
    TOTAL_EMAIL_FISCAL_YEAR_TO_YESTERDAY,
    TOTAL_SMS_FISCAL_YEAR_TO_YESTERDAY,
    RedisAnnualLimit,
    annual_limit_notifications_key,
    annual_limit_notifications_v2_key,
    annual_limit_status_key,
)
from notifications_utils.clients.redis.redis_client import RedisClient


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
    expected_key = f"annual-limit:{mocked_service_id}:notifications_v2"
    assert annual_limit_notifications_v2_key(mocked_service_id) == expected_key
    # TODO: remove the below
    expected_key = f"annual-limit:{mocked_service_id}:notifications"
    assert annual_limit_notifications_key(mocked_service_id) == expected_key


def test_annual_limits_key(mocked_service_id):
    expected_key = f"annual-limit:{mocked_service_id}:status"
    assert annual_limit_status_key(mocked_service_id) == expected_key


@pytest.mark.parametrize(
    "increment_by, metric",
    [
        (1, SMS_DELIVERED),
        (1, SMS_DELIVERED_TODAY),
        (1, EMAIL_DELIVERED),
        (1, EMAIL_DELIVERED_TODAY),
        (1, SMS_FAILED),
        (1, SMS_FAILED_TODAY),
        (1, EMAIL_FAILED),
        (1, EMAIL_FAILED_TODAY),
        (2, SMS_DELIVERED),
        (2, SMS_DELIVERED_TODAY),
        (2, EMAIL_DELIVERED),
        (2, EMAIL_DELIVERED_TODAY),
        (2, SMS_FAILED),
        (2, SMS_FAILED_TODAY),
        (2, EMAIL_FAILED),
        (2, EMAIL_FAILED_TODAY),
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
    assert mock_annual_limit_client.get_notification_count(mocked_service_id, SMS_DELIVERED) == 0


def test_get_all_notification_counts(mock_annual_limit_client, mocked_service_id):
    for field in NOTIFICATION_FIELDS:
        mock_annual_limit_client.increment_notification_count(mocked_service_id, field)
    counts = mock_annual_limit_client.get_all_notification_counts(mocked_service_id)
    assert len(counts) == 4
    assert all(isinstance(value, int) for value in counts.values())

    # Test v2 notification fields
    for field in NOTIFICATION_FIELDS_V2:
        mock_annual_limit_client.increment_notification_count(mocked_service_id, field)
    counts = mock_annual_limit_client.get_all_notification_counts(mocked_service_id)
    assert len(counts) == len(NOTIFICATION_FIELDS_V2)
    assert all(isinstance(value, int) for value in counts.values())


def test_get_all_notification_counts_returns_none_if_fields_do_not_exist(mock_annual_limit_client, mocked_service_id):
    notification_counts = mock_annual_limit_client.get_all_notification_counts(mocked_service_id)
    assert set(notification_counts.keys()) == set(NOTIFICATION_FIELDS)
    assert all(value == 0 for value in notification_counts.values())


def test_clear_notification_counts(mock_annual_limit_client, mocked_service_id):
    # Test clearing both structures
    for field in NOTIFICATION_FIELDS:
        mock_annual_limit_client.increment_notification_count(mocked_service_id, field)
    for field in NOTIFICATION_FIELDS_V2:
        mock_annual_limit_client.increment_notification_count(mocked_service_id, field)

    mock_annual_limit_client.clear_notification_counts(mocked_service_id)

    # Verify both structures cleared
    counts = mock_annual_limit_client.get_all_notification_counts(mocked_service_id)
    assert all(value == 0 for value in counts.values())

    counts_v2 = mock_annual_limit_client.get_all_notification_counts(mocked_service_id)
    assert all(value == 0 for value in counts_v2.values())


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
def test_bulk_reset_notification_counts(mock_annual_limit_client, service_ids):
    for service_id in service_ids:
        # TODO: remove the below
        for field in NOTIFICATION_FIELDS:
            mock_annual_limit_client.increment_notification_count(service_id, field)

        for field in NOTIFICATION_FIELDS_V2:
            mock_annual_limit_client.increment_notification_count(service_id, field)
        counts = mock_annual_limit_client.get_all_notification_counts(service_id)

        assert all(value > 0 for value in counts.values())
    mock_annual_limit_client.reset_all_notification_counts()
    for service_id in service_ids:
        counts = mock_annual_limit_client.get_all_notification_counts(service_id)
        assert all(value == 0 for value in counts.values())


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
def test_get_all_annual_limit_statuses(mock_annual_limit_client, mocked_service_id):
    for status in STATUS_FIELDS:
        mock_annual_limit_client.set_annual_limit_status(mocked_service_id, status, datetime.utcnow())

    statuses = mock_annual_limit_client.get_all_annual_limit_statuses(mocked_service_id)
    assert len(statuses) == 4
    assert all(value is not None for value in statuses.values())


def test_get_all_annual_limit_statuses_returns_none_when_fields_do_not_exist(mock_annual_limit_client, mocked_service_id):
    statuses = mock_annual_limit_client.get_all_annual_limit_statuses(mocked_service_id)
    assert set(statuses.keys()) == set(STATUS_FIELDS)
    assert all(value is None for value in statuses.values())


@freeze_time("2024-10-25 12:00:00.000000")
def test_clear_annual_limit_statuses(mock_annual_limit_client, mocked_service_id):
    for status in STATUS_FIELDS:
        mock_annual_limit_client.set_annual_limit_status(mocked_service_id, status, datetime.utcnow())

    statuses = mock_annual_limit_client.get_all_annual_limit_statuses(mocked_service_id)
    assert len(statuses) == 4
    assert all(value == "2024-10-25" for value in statuses.values())

    mock_annual_limit_client.clear_annual_limit_statuses(mocked_service_id)

    statuses = mock_annual_limit_client.get_all_annual_limit_statuses(mocked_service_id)
    assert set(statuses.keys()) == set(STATUS_FIELDS)
    assert all(value is None for value in statuses.values())


@pytest.mark.parametrize(
    "mapping",
    [
        {},
        None,
        {
            "key": 0,
            "key2": 0,
            "key3": 0,
        },
    ],
)
def test_seed_annual_limit_notifications_skips_seeding_if_no_notifications_to_seed(
    app, mock_annual_limit_client, mocked_service_id, mapping, mocker
):
    mock_annual_limit_client.seed_annual_limit_notifications(mocked_service_id, mapping)
    mocked_set_hash_fields = mocker.patch.object(mock_annual_limit_client._redis_client, "bulk_set_hash_fields")
    mocked_set_hash_fields.assert_not_called()


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


def test_increment_sms_delivered(mock_annual_limit_client, mocked_service_id):
    for field in NOTIFICATION_FIELDS:
        mock_annual_limit_client.increment_notification_count(mocked_service_id, field)

    mock_annual_limit_client.increment_sms_delivered(mocked_service_id)

    assert mock_annual_limit_client.get_notification_count(mocked_service_id, SMS_DELIVERED) == 2
    for field in NOTIFICATION_FIELDS:
        if field != SMS_DELIVERED:
            assert mock_annual_limit_client.get_notification_count(mocked_service_id, field) == 1


def test_increment_sms_failed(mock_annual_limit_client, mocked_service_id):
    for field in NOTIFICATION_FIELDS:
        mock_annual_limit_client.increment_notification_count(mocked_service_id, field)

    mock_annual_limit_client.increment_sms_failed(mocked_service_id)

    assert mock_annual_limit_client.get_notification_count(mocked_service_id, SMS_FAILED) == 2
    for field in NOTIFICATION_FIELDS:
        if field != SMS_FAILED:
            assert mock_annual_limit_client.get_notification_count(mocked_service_id, field) == 1


def test_increment_email_delivered(mock_annual_limit_client, mocked_service_id):
    for field in NOTIFICATION_FIELDS:
        mock_annual_limit_client.increment_notification_count(mocked_service_id, field)

    mock_annual_limit_client.increment_email_delivered(mocked_service_id)

    assert mock_annual_limit_client.get_notification_count(mocked_service_id, EMAIL_DELIVERED) == 2
    for field in NOTIFICATION_FIELDS:
        if field != EMAIL_DELIVERED:
            assert mock_annual_limit_client.get_notification_count(mocked_service_id, field) == 1


def test_increment_email_failed(mock_annual_limit_client, mocked_service_id):
    for field in NOTIFICATION_FIELDS:
        mock_annual_limit_client.increment_notification_count(mocked_service_id, field)

    mock_annual_limit_client.increment_email_failed(mocked_service_id)

    assert mock_annual_limit_client.get_notification_count(mocked_service_id, EMAIL_FAILED) == 2
    for field in NOTIFICATION_FIELDS:
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


# Add these tests after test_seed_annual_limit_notifications_skips_seeding_if_no_notifications_to_seed
@freeze_time("2024-10-25 12:00:00.000000")
def test_seed_annual_limit_notifications_with_partial_fields(mock_annual_limit_client, mocked_service_id):
    """Test that seeding works with partial fields without requiring an exact match."""
    # Create a mapping with only some of the V2 fields
    partial_mapping = {
        EMAIL_DELIVERED_TODAY: 10,
        SMS_DELIVERED_TODAY: 5,
        # Deliberately omit some fields like TOTAL_EMAIL_FISCAL_YEAR_TO_YESTERDAY
    }

    # Seed with partial data
    mock_annual_limit_client.seed_annual_limit_notifications(mocked_service_id, partial_mapping)

    # Verify seeded_at is set
    assert mock_annual_limit_client.was_seeded_today(mocked_service_id) is True

    # Verify the fields we provided are stored
    counts = mock_annual_limit_client.get_all_notification_counts(mocked_service_id)
    assert counts[EMAIL_DELIVERED_TODAY] == 10
    assert counts[SMS_DELIVERED_TODAY] == 5

    # Missing fields should be zero or None, but not error
    assert EMAIL_FAILED_TODAY in counts
    assert TOTAL_EMAIL_FISCAL_YEAR_TO_YESTERDAY in counts


@freeze_time("2024-10-25 12:00:00.000000")
def test_seed_annual_limit_notifications_with_extra_fields(mock_annual_limit_client, mocked_service_id):
    """Test that seeding works with extra fields beyond the expected ones."""
    # Create a mapping with all required fields plus an extra one
    complete_mapping = {
        EMAIL_DELIVERED_TODAY: 10,
        EMAIL_FAILED_TODAY: 2,
        SMS_DELIVERED_TODAY: 5,
        SMS_FAILED_TODAY: 1,
        TOTAL_EMAIL_FISCAL_YEAR_TO_YESTERDAY: 100,
        TOTAL_SMS_FISCAL_YEAR_TO_YESTERDAY: 50,
        "extra_field": 42,  # Field not in NOTIFICATION_FIELDS_V2
    }

    # Seed with extra data
    mock_annual_limit_client.seed_annual_limit_notifications(mocked_service_id, complete_mapping)

    # Verify all expected fields were stored
    counts = mock_annual_limit_client.get_all_notification_counts(mocked_service_id)
    assert counts[EMAIL_DELIVERED_TODAY] == 10
    assert counts[EMAIL_FAILED_TODAY] == 2
    assert counts[SMS_DELIVERED_TODAY] == 5
    assert counts[SMS_FAILED_TODAY] == 1
    assert counts[TOTAL_EMAIL_FISCAL_YEAR_TO_YESTERDAY] == 100
    assert counts[TOTAL_SMS_FISCAL_YEAR_TO_YESTERDAY] == 50

    # Extra field should be ignored without error
    assert "extra_field" not in counts


@freeze_time("2024-10-25 12:00:00.000000")
def test_seed_annual_limit_notifications_preserves_fields_on_reseeding(mock_annual_limit_client, mocked_service_id):
    """Test that reseeding preserves all fields, even ones not included in second seeding."""

    # First seed with complete data
    initial_mapping = {
        EMAIL_DELIVERED_TODAY: 10,
        EMAIL_FAILED_TODAY: 2,
        SMS_DELIVERED_TODAY: 5,
        SMS_FAILED_TODAY: 1,
        TOTAL_EMAIL_FISCAL_YEAR_TO_YESTERDAY: 100,
        TOTAL_SMS_FISCAL_YEAR_TO_YESTERDAY: 50,
    }
    mock_annual_limit_client.seed_annual_limit_notifications(mocked_service_id, initial_mapping)

    # Force reset of seeded_at to allow reseeding
    mock_annual_limit_client._redis_client.delete_hash_fields(annual_limit_notifications_v2_key(mocked_service_id), ["seeded_at"])

    # Reseed with only partial data
    partial_mapping = {
        EMAIL_DELIVERED_TODAY: 15,  # Updated value
        SMS_DELIVERED_TODAY: 7,  # Updated value
        # Omit other fields
    }
    mock_annual_limit_client.seed_annual_limit_notifications(mocked_service_id, partial_mapping)

    # Check that updated fields changed
    counts = mock_annual_limit_client.get_all_notification_counts(mocked_service_id)
    assert counts[EMAIL_DELIVERED_TODAY] == 15  # Updated
    assert counts[SMS_DELIVERED_TODAY] == 7  # Updated

    # Check that omitted fields were preserved, not deleted
    assert counts[EMAIL_FAILED_TODAY] == 2  # Original value preserved
    assert counts[SMS_FAILED_TODAY] == 1  # Original value preserved
    assert counts[TOTAL_EMAIL_FISCAL_YEAR_TO_YESTERDAY] == 100  # Original value preserved
    assert counts[TOTAL_SMS_FISCAL_YEAR_TO_YESTERDAY] == 50  # Original value preserved
