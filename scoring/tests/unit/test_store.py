import unittest

from mock import Mock, patch
from redis import ConnectionError

from scoring.store import Storage, StorageError


class TestStorage(unittest.TestCase):
    @patch("scoring.settings.RETRY_DELAY", 0.01)
    def test_connection_error(self):
        storage = Storage()
        storage.redis_client = Mock(
            **{
                "get.side_effect": ConnectionError,
                "set.side_effect": ConnectionError,
                "smembers.side_effect": ConnectionError
            }
        )

        self.assertIs(None, storage.cache_set("a", 42, 60))
        self.assertIs(None, storage.cache_get("a"))

        with self.assertRaises(StorageError):
            storage.get("a")
