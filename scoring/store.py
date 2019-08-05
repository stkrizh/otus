import functools
import logging
import time

import redis

from . import settings


class StorageError(Exception):
    pass


def retry(raise_on_failure=True):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, settings.RETRY_N_TIMES + 1):
                try:
                    return func(*args, **kwargs)
                except redis.ConnectionError:
                    msg = "Can't connect to Redis-server. Attempt {} of {}."
                    logging.debug(msg.format(attempt, settings.RETRY_N_TIMES))
                    time.sleep(settings.RETRY_DELAY)

            if raise_on_failure:
                raise StorageError("Storage is not available.")
            return None

        return wrapper

    return decorator


class Storage(object):
    """Emulate cache / persistent key-value storage.
    """

    def __init__(
        self,
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=settings.REDIS_DB,
        socket_timeout=settings.REDIS_CONNECTION_TIMEOUT,
    ):
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            socket_timeout=socket_timeout,
        )

    @retry(raise_on_failure=False)
    def cache_set(self, key, value, exp):
        """Save a key-value pair to storage.
        """
        return self.redis_client.set(key, value, ex=exp)

    @retry(raise_on_failure=False)
    def cache_get(self, key):
        """Get value by specified key from the storage.
        """
        return self.redis_client.get(key)

    @retry(raise_on_failure=True)
    def get(self, key):
        """Get value by specified key from the storage.

        Raises
        ------
        StorageError
            If the storage is not available.
        """
        return self.redis_client.get(key)
