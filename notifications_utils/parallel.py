import math
import multiprocessing


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
    worker_count = min(math.ceil(data_size / ideal_chunk_size), MAX_WORKERS)  # noqa: F821
    chunk_size = math.ceil(data_size / worker_count)

    # Ensure chunk size remains within min and max chunk size bounds
    chunk_size = max(MIN_CHUNK_SIZE, min(chunk_size, MAX_CHUNK_SIZE))
    worker_count = math.ceil(data_size / chunk_size)

    # Suppress workers for larger chunks to avoid memory and/or context switching overhead
    if chunk_size > MAX_CHUNK_SIZE * 0.8:
        worker_count = min(worker_count, MAX_WORKERS // 2)
    else:
        worker_count = min(worker_count, MAX_WORKERS)

    if worker_count < 1:
        worker_count = 1

    return chunk_size, worker_count
