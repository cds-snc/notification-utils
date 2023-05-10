from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from notifications_utils.formatters import url_encode_full_stops
from typing import Any, List


def generate_token(payload: Any, secret: str | List[str], salt: str = "token") -> str:
    """Create a signed token containing a payload. The token contains the creation time.

    Note: After admin and api no longer pass a salt we can remove the salt parameter from this function
    and simplify the tests of these functions

    Parameters:
    payload: The payload to be signed
    secret: The secret to sign the payload with
    salt: The salt that is passed in but no longer used

    Returns:
    A signed token containing the payload

    """
    return url_encode_full_stops(URLSafeTimedSerializer(secret).dumps(payload, "token"))


def check_token(token: str, secret: str | List[str], salt: str = "token", max_age_seconds: int = 60 * 60 * 24) -> Any:
    """
    Check that a token is valid and return the payload.

    Note: We currently verify with either the passed in salt or the salt "token".
    After admin and api no longer pass a salt we can remove the salt parameter from this function
    and change the "try / except" block to a simple "return ser.loads(..)"

    Parameters:
    token: The token to be checked
    secret: The secret to check the token with
    salt: The salt that is passed in and may be used to check the token
    max_age_seconds: The maximum age of the token in seconds

    Returns:
    The payload of the token if it is not too old and is valid
    raises SignatureExpired if the token is too old
    raises BadSignature if the token is invalid

    """
    ser = URLSafeTimedSerializer(secret)
    try:
        return ser.loads(token, max_age=max_age_seconds, salt="token")
    except SignatureExpired:  # SignatureExpired is a subclass of BadSignature so we ensure it is raised first
        raise
    except BadSignature:
        return ser.loads(token, max_age=max_age_seconds, salt=salt)
