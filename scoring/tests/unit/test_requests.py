import unittest

from scoring.api import ClientsInterestsRequest, OnlineScoreRequest
from scoring.fields import GenderField, ValidationError
from scoring.tests.helpers import cases


class TestClientsInterestesRequest(unittest.TestCase):
    @cases(
        [
            {"client_ids": [1], "date": None},
            {"client_ids": [0], "date": ""},
            {"client_ids": [1, 1, 1], "date": "07.07.2007"},
        ]
    )
    def test_valid(self, case):
        request = ClientsInterestsRequest(**case)

        try:
            request.validate()
        except ValidationError:
            self.fail("ValidationError raised")

    @cases(
        [
            {"client_ids": [1], "date": "adasdasd"},
            {"client_ids": [], "date": "07.07.2007"},
            {"client_ids": [1, 1, 1], "date": "  07.07.2007"},
            {"client_ids": [-1, 2, 3], "date": "07.07.2007"},
            {"client_ids": [1, 2, 3], "date": "40.12.2007"},
            {"client_ids": (1, 2, 3), "date": "07.07.2007"},
        ]
    )
    def test_invalid(self, case):
        request = ClientsInterestsRequest(**case)

        with self.assertRaises(ValidationError):
            request.validate()


class TestOnlineScoreRequest(unittest.TestCase):
    @cases(
        [
            {
                "first_name": "Foo",
                "last_name": "Bar",
                "email": None,
                "phone": None,
                "birthday": None,
                "gender": None,
            },
            {
                "first_name": "",
                "last_name": "",
                "email": "mail@email.com",
                "phone": 70123456789,
                "birthday": None,
                "gender": None,
            },
            {
                "first_name": None,
                "last_name": None,
                "email": "",
                "phone": "",
                "birthday": "04.04.1994",
                "gender": GenderField.UNKNOWN,
            },
        ]
    )
    def test_valid(self, case):
        request = OnlineScoreRequest(**case)

        try:
            request.validate()
        except ValidationError:
            self.fail("ValidationError raised")

    @cases(
        [
            {
                "first_name": "",
                "last_name": "",
                "email": "",
                "phone": "",
                "birthday": None,
                "gender": None,
            },
            {
                "first_name": "",
                "last_name": "Bar",
                "email": None,
                "phone": None,
                "birthday": None,
                "gender": None,
            },
            {
                "first_name": "Foo",
                "last_name": None,
                "email": None,
                "phone": None,
                "birthday": None,
                "gender": None,
            },
            {
                "first_name": "",
                "last_name": "",
                "email": "",
                "phone": 70123456789,
                "birthday": None,
                "gender": None,
            },
            {
                "first_name": None,
                "last_name": None,
                "email": "",
                "phone": "",
                "birthday": "04.04.1994",
                "gender": None,
            },
            {
                "first_name": "Foo",
                "last_name": None,
                "email": "",
                "phone": 70123456789,
                "birthday": "04.04.1994",
                "gender": "",
            },
        ]
    )
    def test_invalid(self, case):
        request = OnlineScoreRequest(**case)

        with self.assertRaises(ValidationError):
            request.validate()
