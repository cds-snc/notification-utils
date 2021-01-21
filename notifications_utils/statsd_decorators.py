import functools

from flask import current_app
from monotonic import monotonic


def statsd(namespace):
    def time_function(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = monotonic()
            current_app.statsd_client.incr(f'{namespace}.{func.__name__}')
            try:
                res = func(*args, **kwargs)
            except Exception as e:
                current_app.statsd_client.incr(f'{namespace}.{func.__name__}.exception')
                raise e
            else:
                elapsed_time = monotonic() - start_time

                current_app.statsd_client.incr(f'{namespace}.{func.__name__}.success')
                current_app.statsd_client.timing(f'{namespace}.{func.__name__}.success.elapsed_time', elapsed_time)

                current_app.logger.debug(f"{namespace} call {func.__name__} took {'{0:.4f}'.format(elapsed_time)}")

                return res
        wrapper.__wrapped__.__name__ = func.__name__
        return wrapper

    return time_function
