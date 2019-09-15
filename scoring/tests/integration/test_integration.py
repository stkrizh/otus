import datetime as dt
import hashlib
import logging
import multiprocessing as mp
import os
import socket
import sys
import time
import unittest

from contextlib import closing

import redis
import requests

from scoring import settings
from scoring import api
from scoring.scoring import build_score_key
from scoring.store import Storage, StorageError
from scoring.tests.helpers import cases


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class TestStorage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            socket_timeout=settings.REDIS_CONNECTION_TIMEOUT,
        )

    def test_cache_set(self):
        storage = Storage()
        key = hashlib.md5(os.urandom(10)).hexdigest()
        value = hashlib.md5(os.urandom(10)).hexdigest()

        is_set = storage.cache_set(key, value, 10)
        self.assertTrue(is_set)
        self.assertEqual(value, self.redis.get(key))

    def test_cache_set_expire(self):
        storage = Storage()
        key = hashlib.md5(os.urandom(10)).hexdigest()
        value = hashlib.md5(os.urandom(10)).hexdigest()

        is_set = storage.cache_set(key, value, 1)
        self.assertTrue(is_set)

        time.sleep(2)
        self.assertIs(None, self.redis.get(key))

    def test_cache_set_storage_not_available(self):
        storage = Storage(host="128.128.128.128")
        key = hashlib.md5(os.urandom(10)).hexdigest()
        value = hashlib.md5(os.urandom(10)).hexdigest()

        is_set = storage.cache_set(key, value, 100)
        self.assertIs(None, is_set)

    def test_cache_get(self):
        storage = Storage()
        key = hashlib.md5(os.urandom(10)).hexdigest()
        value = hashlib.md5(os.urandom(10)).hexdigest()
        self.redis.set(key, value)

        self.assertEqual(value, storage.cache_get(key))

    def test_cache_get_nonexistent_key(self):
        storage = Storage()
        key = hashlib.md5(os.urandom(10)).hexdigest()
        self.assertIs(None, storage.cache_get(key))

    def test_cache_get_expire(self):
        storage = Storage()
        key = hashlib.md5(os.urandom(10)).hexdigest()
        value = hashlib.md5(os.urandom(10)).hexdigest()
        self.redis.set(key, value, ex=1)

        time.sleep(2)
        self.assertIs(None, storage.cache_get(key))

    def test_cache_get_storage_not_available(self):
        storage = Storage(host="128.128.128.128")
        key = hashlib.md5(os.urandom(10)).hexdigest()
        self.assertIs(None, storage.cache_get(key))

    def test_get(self):
        storage = Storage()
        key = hashlib.md5(os.urandom(10)).hexdigest()
        values = map(str, range(10))
        self.redis.sadd(key, *values)

        self.assertEqual(values, sorted(storage.get(key)))

    def test_get_nonexistent_key(self):
        storage = Storage()
        key = hashlib.md5(os.urandom(10)).hexdigest()
        self.assertEqual([], storage.get(key))

    def test_get_storage_not_available(self):
        storage = Storage(host="128.128.128.128")
        key = hashlib.md5(os.urandom(10)).hexdigest()

        with self.assertRaises(StorageError):
            storage.get(key)


class TestServerStorageInteraction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logger = logging.getLogger()
        logger.disabled = True

        cls.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            socket_timeout=settings.REDIS_CONNECTION_TIMEOUT,
        )

        # Suppress output of `api.HTTPServer`
        cls.stderr = sys.stderr
        sys.stderr = open(os.devnull, "w")

        cls.port = find_free_port()
        server = api.HTTPServer(("localhost", cls.port), api.MainHTTPHandler)
        cls.server = mp.Process(target=server.serve_forever)
        cls.server.daemon = True
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        cls.redis.flushdb()
        sys.stderr.close()
        sys.stderr = cls.stderr

    def setUp(self):
        self.redis.flushdb()

    def get_response(self, request):
        endpoint = "http://127.0.0.1:{}/method/".format(self.port)
        response = requests.post(endpoint, json=request)
        return response

    def set_valid_auth(self, request):
        if request.get("login") == api.ADMIN_LOGIN:
            request["token"] = hashlib.sha512(
                dt.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT
            ).hexdigest()
        else:
            msg = (
                request.get("account", "")
                + request.get("login", "")
                + api.SALT
            )
            request["token"] = hashlib.sha512(msg).hexdigest()

    @cases(
        [
            {"phone": "70123456789", "email": "stupnikov@otus.ru"},
            {"phone": 70123456789, "email": "stupnikov@otus.ru"},
            {
                "gender": 1,
                "birthday": "01.01.2000",
                "first_name": "a",
                "last_name": "b",
            },
            {"gender": 0, "birthday": "01.01.2000"},
            {"gender": 2, "birthday": "01.01.2000"},
            {"first_name": "a", "last_name": "b"},
            {
                "phone": "70123456789",
                "email": "stupnikov@otus.ru",
                "gender": 1,
                "birthday": "01.01.2000",
                "first_name": "a",
                "last_name": "b",
            },
        ]
    )
    def test_ok_score_request(self, arguments):
        request = {
            "account": "horns&hoofs",
            "login": "h&f",
            "method": "online_score",
            "arguments": arguments,
        }
        self.set_valid_auth(request)
        response = self.get_response(request)

        self.assertEqual(api.OK, response.status_code)

        data = response.json()
        score = data["response"]["score"]
        self.assertTrue(score >= 0)

        key = build_score_key(
            arguments.get("first_name", ""),
            arguments.get("last_name", ""),
            arguments.get("email", ""),
            str(arguments.get("phone", "")),
            arguments.get("gender", ""),
            dt.datetime.strptime("20000101", "%Y%m%d")
            if arguments.get("birthday")
            else None,
        )
        self.assertEqual(self.redis.get(key), str(score))

    @cases(
        [
            {
                "phone": "70123456789",
                "email": "stupnikov@otus.ru",
                "score": 777,
            },
            {
                "first_name": "First",
                "last_name": "Last",
                "phone": "70123456789",
                "email": "stupnikov@otus.ru",
                "score": 0.001,
            },
        ]
    )
    def test_cached_score(self, arguments):
        score = arguments.pop("score")
        request = {
            "account": "horns&hoofs",
            "login": "h&f",
            "method": "online_score",
            "arguments": arguments,
        }
        key = build_score_key(**arguments)
        self.redis.set(key, score)

        self.set_valid_auth(request)
        response = self.get_response(request)
        self.assertEqual(api.OK, response.status_code)

        data = response.json()
        self.assertEqual(str(score), data["response"]["score"])

    @cases(
        [
            {
                "client_ids": [1, 2, 3],
                "date": dt.datetime.today().strftime("%d.%m.%Y"),
            },
            {"client_ids": [999999, 111111], "date": "19.07.2017"},
            {"client_ids": [0]},
        ]
    )
    def test_ok_interests_request(self, arguments):
        request = {
            "account": "horns&hoofs",
            "login": "h&f",
            "method": "clients_interests",
            "arguments": arguments,
        }

        for client_id in arguments["client_ids"]:
            key = "i:{}".format(client_id)
            interests = {"{}-{}".format(client_id, i) for i in range(5)}
            self.redis.sadd(key, *interests)

        self.set_valid_auth(request)
        response = self.get_response(request)

        self.assertEqual(api.OK, response.status_code)

        data = response.json()
        self.assertEqual(len(arguments["client_ids"]), len(data["response"]))

        for client_id, interests in data["response"].items():
            expected_interests = {
                "{}-{}".format(client_id, i) for i in range(5)
            }
            self.assertEqual(expected_interests, set(interests))
