from typing import Any, List

from itsdangerous import URLSafeTimedSerializer

from notifications_utils.formatters import url_encode_full_stops


def generate_token(payload: Any, secret: str | List[str]) -> str:
    """Create a signed token containing a payload. The token contains the creation time.

    Parameters:
    payload: The payload to be signed
    secret: The secret to sign the payload with

    Returns:
    A signed token containing the payload

    """
    return url_encode_full_stops(URLSafeTimedSerializer(secret).dumps(payload, "token"))


def check_token(token: str, secret: str | List[str], max_age_seconds: int = 60 * 60 * 24) -> Any:
    """
    Check that a token is valid and return the payload.

    Parameters:
    token: The token to be checked
    secret: The secret to check the token with
    max_age_seconds: The maximum age of the token in seconds

    Returns:
    The payload of the token if it is not too old and is valid
    raises SignatureExpired if the token is too old
    raises BadSignature if the token is invalid

    """
    return URLSafeTimedSerializer(secret).loads(token, max_age=max_age_seconds, salt="token")
