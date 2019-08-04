# -*- coding: utf-8 -*-

import datetime as dt
import unittest

from scoring import fields
from scoring.tests.helpers import cases


class TestFieldClass(unittest.TestCase):
    def test_required(self):
        field = fields.Field()
        self.assertIs(True, field.required)
        value = None
        with self.assertRaises(fields.ValidationError):
            field.clean(value)

    def test_not_required(self):
        field = fields.Field(required=False)
        value = None
        self.assertIs(None, field.clean(value))

    @cases(
        [
            {"allowed_type": str, "value": " "},
            {"allowed_type": int, "value": 1},
            {"allowed_type": float, "value": -1.0},
            {"allowed_type": (int, float), "value": 3.1415},
            {"allowed_type": (int, float), "value": -1},
            {"allowed_type": list, "value": [1, 2, 3]},
        ]
    )
    def test_allowed_type_valid(self, case):
        field = fields.Field(required=True, nullable=False)
        field.allowed_type = case["allowed_type"]
        value = case["value"]

        try:
            self.assertEqual(value, field.clean(value))
        except fields.ValidationError:
            self.fail(case)

    @cases(
        [
            {"allowed_type": str, "value": None},
            {"allowed_type": int, "value": 1.0},
            {"allowed_type": (int, float), "value": "3.1415"},
            {"allowed_type": list, "value": (1, 2, 3)},
        ]
    )
    def test_allowed_type_invalid(self, case):
        field = fields.Field(required=True, nullable=False)
        field.allowed_type = case["allowed_type"]
        value = case["value"]

        with self.assertRaises(fields.ValidationError):
            field.clean(value)
            self.fail(case)

    @cases([0, "", []])
    def test_nullable_required(self, value):
        not_nullable_field = fields.Field()
        self.assertIs(True, not_nullable_field.required)
        self.assertIs(False, not_nullable_field.nullable)

        with self.assertRaises(fields.ValidationError):
            not_nullable_field.clean(value)
            self.fail(value)

        nullable_field = fields.Field(nullable=True)
        self.assertIs(True, nullable_field.required)
        self.assertIs(value, nullable_field.clean(value), value)

    def test_nullable_not_required(self):
        not_nullable_field = fields.Field(required=False)
        nullable_field = fields.Field(required=False, nullable=True)

        value = None
        self.assertIs(None, not_nullable_field.clean(value))
        self.assertIs(None, nullable_field.clean(value))

        value = ""
        with self.assertRaises(fields.ValidationError):
            not_nullable_field.clean(value)
        self.assertEqual(value, nullable_field.clean(value))

    @cases(
        [
            {"choices": "abc", "value": "a"},
            {"choices": (1, 2, 3), "value": 2},
            {"choices": {1.01, 2.02}, "value": 2.02},
            {"choices": xrange(10), "value": 7},
        ]
    )
    def test_choices_valid(self, case):
        field = fields.Field(required=True, nullable=False)
        field.choices = case["choices"]
        value = case["value"]

        try:
            self.assertEqual(value, field.clean(value), case)
        except fields.ValidationError:
            self.fail(case)

    @cases(
        [
            {"choices": "abc", "value": " "},
            {"choices": (1, 2, 3), "value": 10 * (0.1 + 0.1 + 0.1)},
            {"choices": {1.01, 2.02}, "value": "1.01"},
            {"choices": xrange(10), "value": -1},
        ]
    )
    def test_choices_invalid(self, case):
        field = fields.Field(required=True, nullable=False)
        field.choices = case["choices"]
        value = case["value"]

        with self.assertRaises(fields.ValidationError):
            field.clean(value)
            self.fail(case)

    @cases(
        [
            [False, False, str, "abc", None],
            [False, True, str, "abc", ""],
            [False, False, int, {1, 2, 3}, None],
            [False, True, int, {1, 2, 3}, 0],
            [False, False, list, ([1, 2], [3, 4]), None],
            [False, True, list, ([1, 2], [3, 4]), []],
            [True, True, None, (5, "a"), 0],
            [True, True, None, (5, "a"), ""],
        ]
    )
    def test_valid(self, case):
        required, nullable, allowed_type, choices, value = case

        field = fields.Field(required=required, nullable=nullable)
        field.allowed_type = allowed_type
        field.choices = choices

        try:
            self.assertEqual(value, field.clean(value), case)
        except fields.ValidationError:
            self.fail(case)

    @cases(
        [
            [True, False, str, "abc", None],
            [True, False, int, "abc", "a"],
            [False, False, str, "abc", ""],
            [False, False, None, None, ""],
            [False, False, None, None, 0],
            [True, False, None, None, None],
            [True, True, str, [""], " "],
        ]
    )
    def test_invalid(self, case):
        required, nullable, allowed_type, choices, value = case

        field = fields.Field(required=required, nullable=nullable)
        field.allowed_type = allowed_type
        field.choices = choices

        with self.assertRaises(fields.ValidationError):
            field.clean(value)
            self.fail(case)


class TestCharField(unittest.TestCase):
    @cases(
        [
            [True, False, 5, None, " "],
            [True, False, 5, None, " " * 5],
            [False, False, 0, None, None],
            [False, True, 5, ("a", "b"), None],
            [False, True, 5, ("a", "b"), ""],
            [False, False, 1, ("aa", "bb"), "aa"],
        ]
    )
    def test_valid(self, case):
        required, nullable, max_len, choices, value = case

        field = fields.CharField(
            required=required, nullable=nullable, max_len=max_len
        )
        field.choices = choices

        try:
            self.assertEqual(value, field.clean(value), case)
        except fields.ValidationError:
            self.fail(case)

    @cases(
        [
            [True, False, 5, None, ""],
            [True, False, 5, None, " " * 6],
            [False, True, 0, None, " "],
            [False, True, 5, ("a", "b"), "b "],
            [False, True, 5, None, 42],
        ]
    )
    def test_invalid(self, case):
        required, nullable, max_len, choices, value = case

        field = fields.CharField(
            required=required, nullable=nullable, max_len=max_len
        )
        field.choices = choices

        with self.assertRaises(fields.ValidationError):
            field.clean(value)
            self.fail(case)


class TestRegexField(unittest.TestCase):
    @cases(
        [
            [True, False, 5, None, r"^1+$", "11"],
            [True, False, 5, ("a", "b"), r"^1+$", "a"],
            [False, False, 5, ("a", "b"), r"^1+$", None],
            [True, True, 5, ("a", "b"), r"^1+$", ""],
            [True, False, 5, None, r"abc", "abc  "],
            [True, False, 128, None, ur"^привет", u"приветик"],
        ]
    )
    def test_valid(self, case):
        required, nullable, max_len, choices, pattern, value = case

        field = fields.RegexField(
            required=required,
            nullable=nullable,
            max_len=max_len,
            pattern=pattern,
        )
        field.choices = choices

        try:
            self.assertEqual(value, field.clean(value), case)
        except fields.ValidationError:
            self.fail(case)

    @cases(
        [
            [True, False, 3, None, r"^1+$", "11111"],
            [True, False, 5, ("a", "b"), r"^1+$", "11111"],
            [True, False, 5, None, ur"^привет", u"нет"],
            [True, False, 5, None, r"abc", "  abc"],
        ]
    )
    def test_invalid(self, case):
        required, nullable, max_len, choices, pattern, value = case

        field = fields.RegexField(
            required=required,
            nullable=nullable,
            max_len=max_len,
            pattern=pattern,
        )
        field.choices = choices

        with self.assertRaises(fields.ValidationError):
            field.clean(value)
            self.fail(case)


class TestEmailField(unittest.TestCase):
    @cases(
        [
            [True, False, "a" * 124 + "@a.a"],
            [True, True, ""],
            [False, False, None],
            [True, False, u"email@test.com"],
        ]
    )
    def test_valid(self, case):
        required, nullable, value = case

        field = fields.EmailField(required=required, nullable=nullable)

        try:
            self.assertEqual(value, field.clean(value), case)
        except fields.ValidationError:
            self.fail(case)

    @cases(
        [
            [True, False, None],
            [True, False, ""],
            [True, False, " aaa@aaa.aa"],
            [True, False, "aaa@aaa.aa "],
            [True, False, u"емэйл@почта.ру"],
            [True, False, "a" * 256 + "@mail.com"],
        ]
    )
    def test_invalid(self, case):
        required, nullable, value = case

        field = fields.EmailField(required=required, nullable=nullable)

        with self.assertRaises(fields.ValidationError):
            field.clean(value)
            self.fail(case)


class TestPhoneField(unittest.TestCase):
    @cases(
        [
            [False, False, None],
            [True, True, ""],
            [True, False, "71234567890"],
            [True, False, 71234567890],
            [True, False, u"71234567890"],
        ]
    )
    def test_valid(self, case):
        required, nullable, value = case

        field = fields.PhoneField(required=required, nullable=nullable)

        try:
            value = str(value) if value else value
            self.assertEqual(value, field.clean(value), case)
        except fields.ValidationError:
            self.fail(case)

    @cases(
        [
            [True, False, None],
            [True, False, ""],
            [True, False, "81234567890"],
            [True, False, "712345678901"],
            [True, False, " 71234567890"],
            [True, False, "71234567890 "],
            [True, False, 81234567890],
            [True, False, 7123456789],
        ]
    )
    def test_invalid(self, case):
        required, nullable, value = case

        field = fields.PhoneField(required=required, nullable=nullable)

        with self.assertRaises(fields.ValidationError):
            field.clean(value)
            self.fail(case)


class TestDateField(unittest.TestCase):
    @cases(
        [
            [False, False, None],
            [True, True, ""],
        ]
    )
    def test_valid_empty(self, case):
        required, nullable, value = case

        field = fields.DateField(required=required, nullable=nullable)

        try:
            self.assertEqual(value, field.clean(value), case)
        except fields.ValidationError:
            self.fail(case)

    @cases(
        [
            [True, False, "31.12.2017"],
            [True, False, "29.02.2016"],
            [True, False, "10.10.5016"],
            [True, False, u"15.03.2000"],
        ]
    )
    def test_valid(self, case):
        required, nullable, value = case

        field = fields.DateField(required=required, nullable=nullable)

        try:
            cleaned = field.clean(value)
            day, month, year = map(int, value.split("."))

            self.assertEqual(day, cleaned.day, case)
            self.assertEqual(month, cleaned.month, case)
            self.assertEqual(year, cleaned.year, case)

        except fields.ValidationError:
            self.fail(case)

    @cases(
        [
            [True, False, None],
            [False, False, ""],
            [False, False, "12.31.2017"],
            [False, False, " 31.12.2017"],
            [False, False, "29.02.2017"],
            [False, False, "10.10.10000"],
        ]
    )
    def test_invalid(self, case):
        required, nullable, value = case

        field = fields.DateField(required=required, nullable=nullable)

        with self.assertRaises(fields.ValidationError):
            field.clean(value)
            self.fail(case)


class TestBirthDayField(unittest.TestCase):
    @cases(
        [
            [False, False, None],
            [True, True, ""],
        ]
    )
    def test_valid_empty(self, case):
        required, nullable, value = case

        field = fields.BirthDayField(required=required, nullable=nullable)

        try:
            self.assertEqual(value, field.clean(value), case)
        except fields.ValidationError:
            self.fail(case)

    @cases(
        [
            [True, False, "31.12.2000"],
            [True, False, "29.02.1992"],
            [True, False, "10.10.1980"],
            [True, False, u"15.03.1960"],
        ]
    )
    def test_valid(self, case):
        required, nullable, value = case

        field = fields.BirthDayField(required=required, nullable=nullable)

        try:
            cleaned = field.clean(value)
            day, month, year = map(int, value.split("."))

            self.assertEqual(day, cleaned.day, case)
            self.assertEqual(month, cleaned.month, case)
            self.assertEqual(year, cleaned.year, case)

        except fields.ValidationError:
            self.fail(case)

    def test_invalid(self):
        now = dt.datetime.now()

        field = fields.BirthDayField()

        with self.assertRaises(fields.ValidationError):
            to_old = now - dt.timedelta(days=(70 * 365 + 18))
            to_old_str = to_old.strftime("%d.%m.%Y")
            field.clean(to_old_str)

        with self.assertRaises(fields.ValidationError):
            to_young = now + dt.timedelta(days=1)
            to_young_str = to_young.strftime("%d.%m.%Y")
            field.clean(to_young_str)
