import numbers
import uuid
from time import time
from typing import Any, Dict

from flask import current_app
from flask_redis import FlaskRedis

# expose redis exceptions so that they can be caught
from redis.exceptions import RedisError  # noqa


def prepare_value(val):
    """
    Only bytes, strings and numbers (ints, longs and floats) are acceptable
    for keys and values. Previously redis-py attempted to cast other types
    to str() and store the result. This caused must confusion and frustration
    when passing boolean values (cast to 'True' and 'False') or None values
    (cast to 'None'). It is now the user's responsibility to cast all
    key names and values to bytes, strings or numbers before passing the
    value to redis-py.
    """
    # things redis-py natively supports
    if isinstance(
        val,
        (
            bytes,
            str,
            numbers.Number,
        ),
    ):
        return val
    # things we know we can safely cast to string
    elif isinstance(val, (uuid.UUID,)):
        return str(val)
    else:
        raise ValueError("cannot cast {} to a string".format(type(val)))


class RedisClient:
    redis_store = FlaskRedis()
    active = False
    scripts: Dict[str, Any] = {}

    def init_app(self, app):
        self.active = app.config.get("REDIS_ENABLED")
        if self.active:
            self.redis_store.init_app(app)

            self.register_scripts()

    def register_scripts(self):
        # delete keys matching a pattern supplied as a parameter. Does so in batches of 5000 to prevent unpack from
        # exceeding lua's stack limit, and also to prevent errors if no keys match the pattern.
        # Inspired by https://gist.github.com/ddre54/0a4751676272e0da8186
        self.scripts["delete-keys-by-pattern"] = self.redis_store.register_script(
            """
            local keys = redis.call('keys', ARGV[1])
            local deleted = 0
            for i=1, #keys, 5000 do
                deleted = deleted + redis.call('del', unpack(keys, i, math.min(i + 4999, #keys)))
            end
            return deleted
            """
        )

    def delete_cache_keys_by_pattern(self, pattern):
        r"""
        Deletes all keys matching a given pattern, and returns how many keys were deleted.
        Pattern is defined as in the KEYS command: https://redis.io/commands/keys

        * h?llo matches hello, hallo and hxllo
        * h*llo matches hllo and heeeello
        * h[ae]llo matches hello and hallo, but not hillo
        * h[^e]llo matches hallo, hbllo, ... but not hello
        * h[a-b]llo matches hallo and hbllo

        Use \ to escape special characters if you want to match them verbatim
        """
        if self.active:
            return self.scripts["delete-keys-by-pattern"](args=[pattern])
        return 0

    # TODO: Refactor and simplify this to use HEXPIRE when we upgrade Redis to 7.4.0
    def delete_hash_fields(self, hashes: (str | list), fields: list, raise_exception=False):
        """Deletes fields from the specified hashes. if fields is `None`, then all fields from the hashes are deleted, deleting the hash entirely.

        Args:
            hashes (str|list): The hash pattern or list of hash keys to delete fields from.
            fields (list): A list of fields to delete from the hashes. If `None`, then all fields are deleted.

        Returns:
            _type_: _description_
        """
        if self.active:
            try:
                hashes = [prepare_value(h) for h in hashes] if isinstance(hashes, list) else prepare_value(hashes)
                # When fields are passed in, use the list as is
                # When hashes is a list, and no fields are passed in, fetch the fields from the first hash in the list
                # otherwise we know we're going scan iterate over a pattern so we'll fetch the fields on the first pass in the loop below
                fields = [prepare_value(f) for f in fields]
                # Use a pipeline to atomically delete fields from each hash.
                pipe = self.redis_store.pipeline()
                # if hashes is not a list, we're scan iterating over keys matching a pattern
                for key in hashes if isinstance(hashes, list) else self.redis_store.scan_iter(hashes):
                    if not fields:
                        fields = self.redis_store.hkeys(key)
                    key = prepare_value(key)
                    pipe.hdel(key, *fields)
                result = pipe.execute()
                # TODO: May need to double check that the pipeline result count matches the number of hashes deleted
                # and retry any failures
                return result
            except Exception as e:
                self.__handle_exception(e, raise_exception, "expire_hash_fields", hashes)
        return False

    def bulk_set_hash_fields(self, mapping, pattern=None, key=None, raise_exception=False):
        """
        Bulk set hash fields.
        :param pattern: the pattern to match keys
        :param mapping: the mapping of fields to set
        :param raise_exception: True if we should allow the exception to bubble up
        """
        if self.active:
            try:
                if pattern:
                    current_app.logger.info(
                        f"[alimit-debug-redis] bulk_set_hash_fields - Pattern branch. pattern: {pattern}, key: {key}, mapping: {mapping}"
                    )
                    for key in self.redis_store.scan_iter(pattern):
                        self.redis_store.hmset(key, mapping)
                    return True
                if key:
                    current_app.logger.info(
                        f"[alimit-debug-redis] bulk_set_hash_fields - key branch. pattern: {pattern}, key: {key}, mapping: {mapping}"
                    )
                    return self.redis_store.hmset(key, mapping)
            except Exception as e:
                self.__handle_exception(e, raise_exception, "bulk_set_hash_fields", pattern)
        return False

    def exceeded_rate_limit(self, cache_key, limit, interval, raise_exception=False):
        """
        Rate limiting.
        - Uses Redis sorted sets
        - Also uses redis "multi" which is abstracted into pipeline() by FlaskRedis/PyRedis
        - Sends all commands to redis as a group to be executed atomically

        Method:
        (1) Add event, scored by timestamp (zadd). The score determines order in set.
        (2) Use zremrangebyscore to delete all set members with a score between
            - Earliest entry (lowest score == earliest timestamp) - represented as '-inf'
                and
            - Current timestamp minus the interval
            - Leaves only relevant entries in the set (those between now and now - interval)
        (3) Count the set
        (4) If count > limit fail request
        (5) Ensure we expire the set key to preserve space

        Notes:
        - Failed requests count. If over the limit and keep making requests you'll stay over the limit.
        - The actual value in the set is just the timestamp, the same as the score. We don't store any requets details.
        - return value of pipe.execute() is an array containing the outcome of each call.
            - result[2] == outcome of pipe.zcard()
        - If redis is inactive, or we get an exception, allow the request

        :param cache_key:
        :param limit: Number of requests permitted within interval
        :param interval: Interval we measure requests in
        :param raise_exception: Should throw exception
        :return:
        """
        cache_key = prepare_value(cache_key)
        if self.active:
            try:
                pipe = self.redis_store.pipeline()
                when = time()
                pipe.zadd(cache_key, {when: when})
                pipe.zremrangebyscore(cache_key, "-inf", when - interval)
                pipe.zcard(cache_key)
                pipe.expire(cache_key, interval)
                result = pipe.execute()
                return result[2] > limit
            except Exception as e:
                self.__handle_exception(e, raise_exception, "rate-limit-pipeline", cache_key)
                return False
        else:
            return False

    def add_data_to_sorted_set(self, cache_key: str, sorted_set_data: dict, raise_exception=False) -> None:
        """
        Add data to a sorted set
        :param cache_key: the Redis key for the sorted set to add to
        :param sorted_set_data: the data to add to the sorted set, in the form {key1: score1, key2: score2}
        :param raise_exception: True if we should allow the exception to bubble up
        """
        cache_key = prepare_value(cache_key)
        if self.active:
            try:
                self.redis_store.zadd(cache_key, sorted_set_data)
            except Exception as e:
                self.__handle_exception(e, raise_exception, "add-key-to-ordered-set", cache_key)

    def delete_from_sorted_set(self, cache_key, min_score, max_score, raise_exception=False):
        """
        Delete data from a sorted set from inside the range (min_score, max_score)
        :param cache_key: the Redis key for the sorted set to add to
        :param min_score: the minimum score to delete
        :param max_score: the maximum score to delete
        :param raise_exception: True if we should allow the exception to bubble up
        """
        cache_key = prepare_value(cache_key)
        if self.active:
            try:
                self.redis_store.zremrangebyscore(cache_key, min_score, max_score)
            except Exception as e:
                self.__handle_exception(e, raise_exception, "delete-key-from-ordered-set", cache_key)

    def get_length_of_sorted_set(self, cache_key: str, min_score, max_score, raise_exception=False) -> int:
        """
        Get the number of items from a sorted set between min_score and max_score.
        :param cache_key: the Redis key for the sorted set to add to
        :param min_score: defines the minimum of the range to count
        :param max_score: defines the maximum of the range to count
        :param raise_exception: True if we should allow the exception to bubble up
        :return: int
        """
        cache_key = prepare_value(cache_key)
        if self.active:
            try:
                count = self.redis_store.zcount(cache_key, min_score, max_score)
                return count if count else 0
            except Exception as e:
                self.__handle_exception(e, raise_exception, "get_length_of_sorted_set", cache_key)
                return 0
        else:
            return 0

    def set(self, key, value, ex=None, px=None, nx=False, xx=False, raise_exception=False):
        key = prepare_value(key)
        value = prepare_value(value)
        if self.active:
            try:
                self.redis_store.set(key, value, ex, px, nx, xx)
            except Exception as e:
                self.__handle_exception(e, raise_exception, "set", key)

    def incr(self, key, raise_exception=False):
        key = prepare_value(key)
        if self.active:
            try:
                return self.redis_store.incr(key)
            except Exception as e:
                self.__handle_exception(e, raise_exception, "incr", key)

    def incrby(self, key, by, raise_exception=False):
        key = prepare_value(key)
        if self.active:
            try:
                return self.redis_store.incrby(key, by)
            except Exception as e:
                self.__handle_exception(e, raise_exception, "incrby", key)

    def decrby(
        self,
        key,
        by,
        raise_exception=False,
    ):
        key = prepare_value(key)
        if self.active:
            try:
                return self.redis_store.decrby(key, by)
            except Exception as e:
                self.__handle_exception(e, raise_exception, "decrby", key)

        return None

    def get(self, key, raise_exception=False):
        key = prepare_value(key)
        if self.active:
            try:
                return self.redis_store.get(key)
            except Exception as e:
                self.__handle_exception(e, raise_exception, "get", key)

        return None

    def set_hash_value(self, key, field, value, raise_exception=False):
        key = prepare_value(key)
        field = prepare_value(field)
        value = prepare_value(value)

        if self.active:
            try:
                return self.redis_store.hset(key, field, value)
            except Exception as e:
                self.__handle_exception(e, raise_exception, "set_hash_value", key)

        return None

    def decrement_hash_value(self, key, value, raise_exception=False):
        return self.increment_hash_value(key, value, raise_exception, incr_by=-1)

    def increment_hash_value(self, key, value, raise_exception=False, incr_by=1):
        key = prepare_value(key)
        value = prepare_value(value)

        if self.active:
            try:
                return self.redis_store.hincrby(key, value, incr_by)
            except Exception as e:
                self.__handle_exception(e, raise_exception, "increment_hash_value", key)
        return None

    def get_hash_field(self, key, field, raise_exception=False):
        key = prepare_value(key)
        field = prepare_value(field)

        if self.active:
            try:
                return self.redis_store.hget(key, field)
            except Exception as e:
                self.__handle_exception(e, raise_exception, "get_hash_field", key)

        return None

    def get_all_from_hash(self, key, raise_exception=False):
        key = prepare_value(key)
        if self.active:
            try:
                return self.redis_store.hgetall(key)
            except Exception as e:
                self.__handle_exception(e, raise_exception, "get_all_from_hash", key)

        return None

    def set_hash_and_expire(self, key, values, expire_in_seconds, raise_exception=False):
        key = prepare_value(key)
        values = {prepare_value(k): prepare_value(v) for k, v in values.items()}
        if self.active:
            try:
                self.redis_store.hmset(key, values)
                return self.redis_store.expire(key, expire_in_seconds)
            except Exception as e:
                self.__handle_exception(e, raise_exception, "set_hash_and_expire", key)

        return None

    def expire(self, key, expire_in_seconds, raise_exception=False):
        key = prepare_value(key)
        if self.active:
            try:
                self.redis_store.expire(key, expire_in_seconds)
            except Exception as e:
                self.__handle_exception(e, raise_exception, "expire", key)

    def delete(self, *keys, raise_exception=False):
        _keys = [prepare_value(k) for k in keys]
        if self.active:
            try:
                self.redis_store.delete(*_keys)
            except Exception as e:
                self.__handle_exception(e, raise_exception, "delete", ", ".join(_keys))

    def __handle_exception(self, e, raise_exception, operation, key_name):
        current_app.logger.exception("Redis error performing {} on {}".format(operation, key_name))
        if raise_exception:
            raise e
