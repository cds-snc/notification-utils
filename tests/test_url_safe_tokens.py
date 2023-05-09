import urllib

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
import pytest

from notifications_utils.formatters import url_encode_full_stops
from notifications_utils.url_safe_token import generate_token, check_token


def test_works_without_salt():
    payload = "email@something.com"
    token = generate_token(payload, "secret-key")
    token = urllib.parse.unquote(token)
    assert payload == check_token(token, "secret-key")


def test_generate_uses_salt_token():
    payload = "email@something.com"
    token = generate_token(payload, "secret-key", salt="s1")
    token = urllib.parse.unquote(token)
    assert payload == check_token(token, "secret-key", salt="token")


def test_check_verifies_if_generated_with_salt_parameter():
    payload = "email@something.com"
    token = url_encode_full_stops(URLSafeTimedSerializer("secret-key").dumps(payload, "s1"))
    token = urllib.parse.unquote(token)
    assert payload == check_token(token, "secret-key", salt="s1")


def test_should_return_payload_from_signed_token():
    payload = "email@something.com"
    token = generate_token(payload, "secret-key", "dangerous-salt")
    token = urllib.parse.unquote(token)
    assert payload == check_token(token, "secret-key", "dangerous-salt", 30)


def test_should_throw_exception_when_token_is_tampered_with():
    import uuid

    token = generate_token(str(uuid.uuid4()), "secret-key", "dangerous-salt")
    with pytest.raises(BadSignature):
        check_token(token + "qerqwer", "secret-key", "dangerous-salt", 30)


def test_return_none_when_token_is_expired():
    max_age = -1000
    payload = "some_payload"
    token = generate_token(payload, "secret-key", "dangerous-salt")
    token = urllib.parse.unquote(token)
    with pytest.raises(SignatureExpired):
        assert check_token(token, "secret-key", "dangerous-salt", max_age) is None
