import functools
import logging
import time

import redis

from . import settings


_CLIENT = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    db=settings.REDIS_DB,
    socket_timeout=settings.REDIS_CONNECTION_TIMEOUT,
)


def retry(times=5, wait=1, exception_class=redis.ConnectionError):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exception_class as error:
                    msg = "Retrying exception: {} of {}"
                    logging.debug(msg.format(attempt, times))
                    time.sleep(wait)

            raise error

        return wrapper

    return decorator


@retry()
def cache_set(key, value, ex=None):
    """Save a key-value pair in Redis.
    """
    return _CLIENT.set(key, value, ex=ex)


@retry()
def cache_get(key):
    """Get a value by key from Redis.
    """
    return _CLIENT.get(key)


get = cache_get
set = cache_set
