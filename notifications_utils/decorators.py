from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Callable, Optional

from flask import current_app

from notifications_utils.iterable import chunk_iterable
from notifications_utils.parallel import control_chunk_and_worker_size


def requires_feature(flag):
    def decorator_feature_flag(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if current_app.config[flag]:
                return func(*args, **kwargs)
            return None

        return wrapper

    return decorator_feature_flag


# Parallel processing decorator
def parallel_process_iterable(
    chunk_size=10000, max_workers=None, is_atomic=True, break_condition: Optional[Callable[..., bool]] = None
):
    """Decorator to split processing an iterable into chunks and execute in parallel. This should decorate the function responsible for processing each chunk.
    If processing can be stopped early, this condition should be defined in the processing function, and the `break_condition` parameter should be provided.

    `chunk_size` and `max_workers` are managed internally to optimize performance based on the size of the data to be processed, but can be overridden if necessary.

    Args:
        chunk_size (int, optional): Defaults to 10,000
        max_workers (_type_, optional): Defaults to the number of CPU cores
        is_atomic (bool, optional): Defaults to True. If False, any exceptions raised during processing will be caught and logged but will not stop other threads from
        continuing.
        break_condition (function, optional): A lambda function that defines when parallel execution can be stopped. This applies to the entire iterable, not just the
        current chunk. When any of the threads returns a result that satisfies the break condition, the processing is stopped and the results are returned.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            data = args[0]
            data_size = len(data)
            nonlocal chunk_size, max_workers
            chunk_size, max_workers = control_chunk_and_worker_size(data_size, chunk_size, max_workers)

            def process_chunk(chunk):
                return func(chunk, *args[1:])

            # Execute in parallel
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(process_chunk, chunk) for chunk in chunk_iterable(data, chunk_size)]
                current_app.logger.info(
                    f"Beginning parallel processing of {data_size} items in {len(futures)} chunks for {func.__name__} across {max_workers} workers."
                )
                # Combine results
                results = []
                for future in futures:
                    result = future.result()
                    results.append(result)
                    if break_condition:
                        try:
                            if break_condition(result):
                                return results
                        except Exception as e:
                            current_app.logger.warning(f"Break condition exception: {e}")
                            if is_atomic:
                                raise e
                            else:
                                continue
                return results

        return wrapper

    return decorator
