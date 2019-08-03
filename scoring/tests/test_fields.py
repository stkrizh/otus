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
