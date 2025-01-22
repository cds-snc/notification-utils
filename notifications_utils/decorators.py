import math
import multiprocessing
from collections.abc import Generator, Iterable
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from itertools import islice
from typing import Callable, Optional

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


def control_chunk_and_worker_size(data_size=None, chunk_size=None, max_workers=None):
    """Attempts to optimize the chunk size and number of workers based on the size of the data to be processed. The following rules are applied:
    - Max concurrently allowed workers is the number of CPU cores
    - 1 worker is used when data sets <= 1000
    - Chunk sizes are capped at 10,000 and are calculated with: `data_size / max_chunk_size`
    - For chunk sizes < 10,000 worker counts are scaled up
    - For chunk sizes that would be >= 10,000 the concurrent workers scale down to 5 to limit CPU context switching

    Args:
        data_size (int, optional): Size of the iterable being chunked. Defaults to 40000.
        chunk_size (int, optional): Overrides default chunk_size of 10000. Defaults to None.
        max_workers (int, optional): Overrides default max workers of 10. Defaults to None.

    Returns:
        tuple[int, int]: The optimized chunk size and number of workers to execute in parallel.
    """
    MIN_CHUNK_SIZE = 1000
    MAX_CHUNK_SIZE = 10000 if not chunk_size else chunk_size
    MAX_WORKERS = multiprocessing.cpu_count() if not max_workers else max_workers

    if data_size <= MIN_CHUNK_SIZE:
        return MIN_CHUNK_SIZE, 1

    # Initial chunk size
    ideal_chunk_size = max(data_size // MAX_WORKERS, MIN_CHUNK_SIZE)
    ideal_chunk_size = min(ideal_chunk_size, MAX_CHUNK_SIZE)

    # Adjust the chunk size to ensure no leftovers
    worker_count = min(math.ceil(data_size / ideal_chunk_size), MAX_WORKERS)
    chunk_size = math.ceil(data_size / worker_count)

    # Ensure chunk size remains within min and max chunk size bounds
    chunk_size = max(MIN_CHUNK_SIZE, min(chunk_size, MAX_CHUNK_SIZE))
    worker_count = math.ceil(data_size / chunk_size)

    # Suppress workers for larger chunks to avoid memory and/or context switching overhead
    if chunk_size > MAX_CHUNK_SIZE * 0.8:
        worker_count = min(worker_count, MAX_WORKERS // 2)
    else:
        worker_count = min(worker_count, MAX_WORKERS)

    return chunk_size, worker_count


# Parallel processing decorator
def parallel_process_iterable(chunk_size=10000, max_workers=None, break_condition: Optional[Callable[..., bool]] = None):
    """Decorator to split processing an iterable into chunks and execute in parallel. This should decorate the function responsible for processing each chunk.
    If processing can be stopped early, this condition should be defined in the processing function, and the `break_condition` parameter should be provided.

    `chunk_size` and `max_workers` are managed internally to optimize performance based on the size of the data to be processed, but can be overridden if necessary.

    Args:
        chunk_size (int, optional): Defaults to 10,000
        max_workers (_type_, optional): Defaults to the number of CPU cores
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
                            raise e
                return results

        return wrapper

    return decorator
