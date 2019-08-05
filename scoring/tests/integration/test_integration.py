import datetime
import hashlib
import multiprocessing as mp
import socket
import unittest

from contextlib import closing

import requests

from scoring import api
from scoring.store import Storage
from scoring.tests.helpers import cases


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class TestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = find_free_port()
        server = api.HTTPServer(("localhost", cls.port), api.MainHTTPHandler)
        cls.server = mp.Process(target=server.serve_forever)
        cls.server.daemon = True
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()

    def get_response(self, request):
        endpoint = "http://127.0.0.1:{}/method/".format(self.port)
        response = requests.post(endpoint, json=request)
        return response

    def set_valid_auth(self, request):
        if request.get("login") == api.ADMIN_LOGIN:
            request["token"] = hashlib.sha512(
                datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT
            ).hexdigest()
        else:
            msg = (
                request.get("account", "")
                + request.get("login", "")
                + api.SALT
            )
            request["token"] = hashlib.sha512(msg).hexdigest()

    def test_empty_request(self):
        response = self.get_response({})
        self.assertEqual(api.INVALID_REQUEST, response.status_code)

    @cases(
        [
            {
                "account": "horns&hoofs",
                "login": "h&f",
                "method": "online_score",
                "token": "",
                "arguments": {},
            },
            {
                "account": "horns&hoofs",
                "login": "h&f",
                "method": "online_score",
                "token": "sdd",
                "arguments": {},
            },
            {
                "account": "horns&hoofs",
                "login": "admin",
                "method": "online_score",
                "token": "",
                "arguments": {},
            },
        ]
    )
    def test_bad_auth(self, request):
        response = self.get_response(request)
        self.assertEqual(api.FORBIDDEN, response.status_code)

    @cases(
        [
            {
                "account": "horns&hoofs",
                "login": "h&f",
                "method": "online_score",
            },
            {"account": "horns&hoofs", "login": "h&f", "arguments": {}},
            {
                "account": "horns&hoofs",
                "method": "online_score",
                "arguments": {},
            },
        ]
    )
    def test_invalid_method_request(self, request):
        self.set_valid_auth(request)
        response = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, response.status_code)
        self.assertTrue(response.json())

    @cases(
        [
            {},
            {"phone": "79175002040"},
            {"phone": "89175002040", "email": "stupnikov@otus.ru"},
            {"phone": "79175002040", "email": "stupnikovotus.ru"},
            {
                "phone": "79175002040",
                "email": "stupnikov@otus.ru",
                "gender": -1,
            },
            {
                "phone": "79175002040",
                "email": "stupnikov@otus.ru",
                "gender": "1",
            },
            {
                "phone": "79175002040",
                "email": "stupnikov@otus.ru",
                "gender": 1,
                "birthday": "01.01.1890",
            },
            {
                "phone": "79175002040",
                "email": "stupnikov@otus.ru",
                "gender": 1,
                "birthday": "XXX",
            },
            {
                "phone": "79175002040",
                "email": "stupnikov@otus.ru",
                "gender": 1,
                "birthday": "01.01.2000",
                "first_name": 1,
            },
            {
                "phone": "79175002040",
                "email": "stupnikov@otus.ru",
                "gender": 1,
                "birthday": "01.01.2000",
                "first_name": "s",
                "last_name": 2,
            },
            {
                "phone": "79175002040",
                "birthday": "01.01.2000",
                "first_name": "s",
            },
            {"email": "stupnikov@otus.ru", "gender": 1, "last_name": 2},
        ]
    )
    def test_invalid_score_request(self, arguments):
        request = {
            "account": "horns&hoofs",
            "login": "h&f",
            "method": "online_score",
            "arguments": arguments,
        }
        self.set_valid_auth(request)
        response = self.get_response(request)

        self.assertEqual(api.INVALID_REQUEST, response.status_code, arguments)
        self.assertTrue(response.json())

    @cases(
        [
            {"phone": "79175002040", "email": "stupnikov@otus.ru"},
            {"phone": 79175002040, "email": "stupnikov@otus.ru"},
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
                "phone": "79175002040",
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

        self.assertEqual(api.OK, response.status_code, arguments)

        data = response.json()
        score = float(data["response"]["score"])
        self.assertTrue(score >= 0, arguments)

        key_parts = [
            arguments.get("first_name", ""),
            arguments.get("last_name", ""),
            str(arguments.get("phone", "")),
            "20000101" if arguments.get("birthday") else "",
        ]
        key = "uid:" + hashlib.md5("".join(key_parts)).hexdigest()

        storage = Storage()
        self.assertEqual(float(storage.cache_get(key)), score)

    def test_ok_score_admin_request(self):
        arguments = {"phone": "79175002040", "email": "stupnikov@otus.ru"}
        request = {
            "account": "horns&hoofs",
            "login": "admin",
            "method": "online_score",
            "arguments": arguments,
        }
        self.set_valid_auth(request)
        response = self.get_response(request)

        self.assertEqual(api.OK, response.status_code)
        data = response.json()
        self.assertEqual(int(data["response"]["score"]), 42)

    @cases(
        [
            {},
            {"date": "20.07.2017"},
            {"client_ids": [], "date": "20.07.2017"},
            {"client_ids": {1: 2}, "date": "20.07.2017"},
            {"client_ids": ["1", "2"], "date": "20.07.2017"},
            {"client_ids": [1, 2], "date": "XXX"},
        ]
    )
    def test_invalid_interests_request(self, arguments):
        request = {
            "account": "horns&hoofs",
            "login": "h&f",
            "method": "clients_interests",
            "arguments": arguments,
        }
        self.set_valid_auth(request)
        response = self.get_response(request)

        self.assertEqual(api.INVALID_REQUEST, response.status_code, arguments)
        self.assertTrue(response.json())

    @cases(
        [
            {
                "client_ids": [1, 2, 3],
                "date": datetime.datetime.today().strftime("%d.%m.%Y"),
            },
            {"client_ids": [1, 2], "date": "19.07.2017"},
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
        self.set_valid_auth(request)
        response = self.get_response(request)

        self.assertEqual(api.OK, response.status_code, arguments)

        data = response.json()
        self.assertEqual(len(arguments["client_ids"]), len(data["response"]))
        self.assertTrue(
            all(
                isinstance(v, list)
                and all(isinstance(i, basestring) for i in v)
                for v in data["response"].values()
            ),
            data["response"]
        )
