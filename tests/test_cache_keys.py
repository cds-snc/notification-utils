import pytest
from notifications_utils.clients.redis.cache_keys import CACHE_KEYS, CACHE_KEYS_ALL

# Ensure the CACHE_KEYS and CACHE_KEYS_ALL are provided since they are used by both ADMIN and API
def test_ensure_CACHE_KEYS_is_provided():
    assert len(CACHE_KEYS) > 0

def test_ensure_CACHE_KEYS_ALL_is_provided():
    assert len(CACHE_KEYS_ALL) > 0