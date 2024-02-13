from flask import current_app
from functools import wraps


def requires_feature(flag):
    def decorator_feature_flag(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if current_app.config[flag]:
                return func(*args, **kwargs)
            return None

        return wrapper

    return decorator_feature_flag
