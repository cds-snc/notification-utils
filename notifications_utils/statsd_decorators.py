import functools

from flask import current_app
from time import monotonic
from typing import Type, no_type_check


def statsd(namespace):
    def time_function(func):
        @no_type_check #noqa
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = monotonic()
            try:
                res = func(*args, **kwargs)
                elapsed_time = monotonic() - start_time
                current_app.statsd_client.incr("{namespace}.{func}".format(namespace=namespace, func=func.__name__))
                current_app.statsd_client.timing(
                    "{namespace}.{func}".format(namespace=namespace, func=func.__name__), elapsed_time
                )

            except Exception as e:
                raise e
            else:
                current_app.logger.debug(
                    "{namespace} call {func} took {time}".format(
                        namespace=namespace, func=func.__name__, time="{0:.4f}".format(elapsed_time)
                    )
                )
                return res

        wrapper.__wrapped__.__name__ = func.__name__  # type: ignore
        return wrapper

    return time_function


def statsd_catch(namespace: str, counter_name: str, exception: Type[Exception]):
    """Increases a statsd counter when a given exception is raised.

    When the expected exception is raised, the statsd counter will be
    incremented and the initial exception re-raised again.

    When a non-expected exception is raised, no counter increment
    occurs and nothing is caught: it should go through with no problem.

    All parameters are required.

    Parameters
    ----------
    namespace : str, required
        The statsd counter namespace.

    counter_name : str, required
        The statsd counter name.

    exception : Type[Exception]
        The exception to catch and raise the counter upon.

    Raises
    ------
    BaseException
        Any parameter that is thrown by the decorated method.
    """

    def catch_function(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception as e:
                current_app.statsd_client.incr(f"{namespace}.{counter_name}")
                raise e

        wrapper.__wrapped__.__name__ = func.__name__  # type: ignore
        return wrapper

    return catch_function
