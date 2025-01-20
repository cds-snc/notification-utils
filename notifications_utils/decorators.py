import math
from collections.abc import Generator, Iterable
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from itertools import islice

from flask import current_app


def requires_feature(flag):
    def decorator_feature_flag(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if current_app.config[flag]:
                return func(*args, **kwargs)
            return None

        return wrapper

    return decorator_feature_flag


# Helper function to chunk a list
def chunk_iterable(iterable_collection: Iterable, chunk_size: int) -> Generator:
    """Helper function to chunk an iterable collection in preparation for parallel processing.

    Args:
        iterable_collection (Iterable): The collection to be chunked
        chunk_size (int): The size of each chunk

    Yields:
        list: The next chunk of the iterable
    """
    iterable = iter(iterable_collection)
    while True:
        chunk = list(islice(iterable, chunk_size))
        if not chunk:
            break
        yield chunk


# Parallel processing decorator
def parallel_process_iterable(chunk_size=10000, max_workers=None, break_condition=None):
    """Decorator to split processing an iterable into chunks and execute in parallel. This should decorate the function responsible for processing each chunk.

    Args:
        chunk_size (int, optional): _description_. Defaults to 10000.
        max_workers (_type_, optional): _description_. Defaults to None.
        break_condition (_type_, optional): _description_. Defaults to None.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            data = args[0]

            # Dynamically size worker / thread count. Default to 6 when data exceeds
            nonlocal max_workers
            if max_workers is None:
                max_workers = math.ceil(len(data) / chunk_size)
                max_workers = min(max_workers, 4)

            def process_chunk(chunk):
                return func(chunk, *args[1:])

            # Execute in parallel
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(process_chunk, chunk) for chunk in chunk_iterable(data, chunk_size)]

                # Combine results
                results = []
                for future in futures:
                    result = future.result()
                    results.append(result)
                    if break_condition and break_condition(result):
                        return results

                return results

        return wrapper

    return decorator
