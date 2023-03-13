import urllib

from itsdangerous import BadSignature, BadTimeSignature, SignatureExpired
from pytest import fail

from notifications_utils.url_safe_token import generate_token, check_token


def test_works_without_salt():
    payload = "email@something.com"
    token = generate_token(payload, "secret-key")
    token = urllib.parse.unquote(token)
    assert payload == check_token(token, "secret-key")


def test_fails_for_incorrect_salt():
    payload = "email@something.com"
    token = generate_token(payload, "secret-key")
    token = urllib.parse.unquote(token)
    try:
        assert payload == check_token(token, "secret-key", salt="wrong-salt")
        fail("Expected a BadTimeSignature exception")
    except BadTimeSignature:
        pass


def test_should_return_payload_from_signed_token():
    payload = "email@something.com"
    token = generate_token(payload, "secret-key", "dangerous-salt")
    token = urllib.parse.unquote(token)
    assert payload == check_token(token, "secret-key", "dangerous-salt", 30)


def test_should_throw_exception_when_token_is_tampered_with():
    import uuid

    token = generate_token(str(uuid.uuid4()), "secret-key", "dangerous-salt")
    try:
        check_token(token + "qerqwer", "secret-key", "dangerous-salt", 30)
        fail()
    except BadSignature:
        pass


def test_return_none_when_token_is_expired():
    max_age = -1000
    payload = "some_payload"
    token = generate_token(payload, "secret-key", "dangerous-salt")
    token = urllib.parse.unquote(token)
    try:
        assert check_token(token, "secret-key", "dangerous-salt", max_age) is None
        fail("Expected a SignatureExpired exception")
    except SignatureExpired:
        pass
