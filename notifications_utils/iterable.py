# Helper function to chunk a list
from itertools import islice
from typing import Generator, Iterable


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
