import logging
import time

import redis

from . import settings


class StorageError(Exception):
    pass


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

    def cache_set(self, key, value, exp):
        """Save a key-value pair in storage.

        Parameters
        ----------
        key : str

        value : str

        exp : int
            Expiration time in seconds.
        """
        for attempt in range(1, settings.RETRY_N_TIMES + 1):
            try:
                return self.redis_client.set(key, value, ex=exp)
            except redis.ConnectionError:
                msg = "Can't connect to Redis-server. Attempt {} of {}."
                logging.debug(msg.format(attempt, settings.RETRY_N_TIMES))
                time.sleep(settings.RETRY_DELAY)

        logging.debug("Cache is not available.")
        return None

    def cache_get(self, key):
        """Get value by specified key from the storage.

        Parameters
        ----------
        key : str
    
        Returns
        -------
        value : Any
            Returns `None` if there is no `key` in the storage
            or storage is not available.
        """
        for attempt in range(1, settings.RETRY_N_TIMES + 1):
            try:
                return self.redis_client.get(key)
            except redis.ConnectionError:
                msg = "Can't connect to Redis-server. Attempt {} of {}."
                logging.debug(msg.format(attempt, settings.RETRY_N_TIMES))
                time.sleep(settings.RETRY_DELAY)

        logging.debug("Cache is not available.")
        return None

    def get(self, key):
        """Get value by specified key from the storage.

        Parameters
        ----------
        key : str

        Returns
        -------
        value : Any

        Raises
        ------
        StorageError
            If the storage is not available.
        """
        for attempt in range(1, settings.RETRY_N_TIMES + 1):
            try:
                return self.redis_client.get(key)
            except redis.ConnectionError:
                msg = "Can't connect to Redis-server. Attempt {} of {}."
                logging.debug(msg.format(attempt, settings.RETRY_N_TIMES))
                time.sleep(settings.RETRY_DELAY)

        raise StorageError("Storage is not available.")
