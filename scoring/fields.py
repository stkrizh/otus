import re

from collections import namedtuple


ValidationResult = namedtuple(
    "ValidationResult", ["value", "skip_further_validation"]
)


class ValidationError(Exception):
    pass


class Field(object):
    """Base class for fields validation.

    Attributes
    ----------
    allowed_type : Optional[type or Tuple[type]]
        Allowed field's type.

    Parameters
    ----------
    label: Optional[str]
        Name of the field.
    required : bool
        Raise a `ValidationError` if the field value is `None`.
        False by default.
    nullable : bool
        Set this to `True` to consider nullable values as valid ones.
        True by default.
    """

    allowed_type = None

    def __init__(self, label=None, required=False, nullable=True):
        self.label = label
        self.required = required
        self.nullable = nullable

    @staticmethod
    def is_nullable(value):
        """Check nullability of the value.

        Parameters
        ----------
        value : Any
            Actual field value.

        Returns
        -------
        bool
            `True` if `value` may be considered as a nullable,
            `False` otherwise.
        """
        return not bool(value)

    def validate(self, value):
        """Perform validation on `value`.

        Parameters
        ----------
        value : Any
            Actual field value.

        Raises
        ------
        ValidationError
            If validation does not succeed.

        Returns
        -------
        result : ValidationResult
        """

        if value is None:
            if self.required:
                err = "Field `{}` is required."
                raise ValidationError(err.format(self.label))

            return ValidationResult(
                value=value, skip_further_validation=True
            )

        if self.allowed_type is not None and not isinstance(
            value, self.allowed_type
        ):
            err = "Field `{}` must be an instance of {} type."
            raise ValidationError(err.format(self.label, self.allowed_type))

        if self.is_nullable(value):
            if not self.nullable:
                err = "Field `{}` may not be nullable."
                raise ValidationError(err.format(self.label))

            return ValidationResult(
                value=value, skip_further_validation=True
            )

        return ValidationResult(value=value, skip_further_validation=False)

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        if self.label is None:
            raise ValueError(
                "Label of an instance of `Field` class may not be None."
            )
        return instance.__dict__[self.label]

    def __set__(self, instance, value):
        if self.label is None:
            raise ValueError(
                "Label of an instance of `Field` class may not be None."
            )

        validated = self.validate(value)
        instance.__dict__[self.label] = validated.value


class CharField(Field):
    """Represents a string.

    Attributes
    ----------
    pattern : Optional[str]
        Regular expression pattern.
    + Field

    Parameters
    ----------
    max_len: int
        Max length of the string.
    + Field
    """

    allowed_type = str
    pattern = None

    def __init__(self, max_len=128, **kwargs):
        super(CharField, self).__init__(**kwargs)

        self.max_len = max_len
        self._compiled_pattern = (
            re.compile(self.pattern) if self.pattern is not None else None
        )

    def validate(self, value):
        validated = super(CharField, self).validate(value)

        if validated.skip_further_validation:
            return validated

        if len(value) > self.max_len:
            err = "Field `{}` is longer than {}."
            raise ValidationError(err.format(self.label, self.max_len))

        if self._compiled_pattern is not None:
            if not self._compiled_pattern.match(value):
                custom_err = getattr(self, "errors", {}).get("invalid")
                err = (
                    "Field `{}` doesn't match {} pattern."
                    if custom_err is None
                    else custom_err
                )
                raise ValidationError(err.format(self.label, self.pattern))

        return ValidationResult(value=value, skip_further_validation=False)


class ArgumentsField(Field):
    """Represents a dictionary.
    """

    allowed_type = dict


class EmailField(CharField):
    """Represents an email address.
    """

    allowed_type = str
    pattern = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    errors = {"invalid": "Field `{}` is invalid email address."}


class PhoneField(Field):
    pass


class DateField(Field):
    pass


class BirthDayField(Field):
    pass


class GenderField(Field):
    pass


class ClientIDsField(Field):
    pass


class UseValidationMeta(type):
    """Metaclass for classes that would use validation.

    Set proper labels to instances of `Field` class.
    """

    def __new__(mcls, name, bases, attrs):
        for key, value in attrs.items():
            if isinstance(value, Field) and value.label is None:
                value.label = key

        cls = super(UseValidationMeta, mcls).__new__(mcls, name, bases, attrs)
        return cls

    def __call__(cls, *args, **kwargs):
        """Run validation on each instance of `Field` class.
        """
        if args:
            raise ValueError("Positional arguments are not allowed.")

        instance = super(UseValidationMeta, cls).__call__()

        for key, value in cls.__dict__.items():
            if isinstance(value, Field):
                setattr(instance, key, kwargs.get(key))

        return instance


class UseValidation(object):
    """Base class to use validation mechanism.
    """

    __metaclass__ = UseValidationMeta
