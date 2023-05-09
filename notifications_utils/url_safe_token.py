from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from notifications_utils.formatters import url_encode_full_stops


# currently api sends in a salt, we can stop doing that, and then remove the salt from the generate_token()
def generate_token(payload, secret, salt="token"):
    return url_encode_full_stops(URLSafeTimedSerializer(secret).dumps(payload, "token"))


# After a day, all valid tokens will be signed with the salt "token" instead of DANGEROUS_SALT.
# So we can:
#  - stop passing the salt to check_token() in api
#  - remove the "try / except" block below (and just return the ser.loads())
#  - tweak the tests to not pass in the salt
def check_token(token, secret, salt="token", max_age_seconds=60 * 60 * 24):
    ser = URLSafeTimedSerializer(secret)
    try:
        return ser.loads(token, max_age=max_age_seconds, salt="token")
    except SignatureExpired:
        raise
    except BadSignature:
        return ser.loads(token, max_age=max_age_seconds, salt=salt)
