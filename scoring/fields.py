import datetime as dt
import re


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
    label: Optional[unicode]
        Name of the field.
    required : bool
        Raise a `ValidationError` if the field value is `None`.
        False by default.
    nullable : bool
        Set this to `True` to consider nullable values as valid ones.
        True by default.
    """

    allowed_type = None
    choices = None

    def __init__(self, label=None, required=True, nullable=False, choices=None):
        self.label = label
        self.required = required
        self.nullable = nullable
        self.choices = choices if choices is not None else self.choices

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

    def clean(self, value):
        """Validate the given value and return its "cleaned" value.
        Raise ValidationError for any errors.

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
                err = u"Field `{}` is required."
                raise ValidationError(err.format(self.label))

            return value

        if isinstance(self.allowed_type, (type, tuple)):
            if not isinstance(value, self.allowed_type):
                err = u"Field `{}` must be an instance of `{}` type / types."
                err = err.format(self.label, self.allowed_type)
                raise ValidationError(err)

        if self.is_nullable(value):
            if not self.nullable:
                err = u"Field `{}` may not be nullable."
                raise ValidationError(err.format(self.label))

            return value

        if self.choices:
            if value not in self.choices:
                err = u"Invalid value for field `{}`. Choices are: `{}`."
                choices = ", ".join(self.choices)
                raise ValidationError(err.format(self.label, choices))

            return value

        return self.validate(value)

    def validate(self, value):
        """Additional validation of non-empty value.
        """
        return value

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        if self.label is None:
            raise ValueError(
                u"Label of an instance of `Field` class may not be None."
            )
        return instance.__dict__[self.label]

    def __set__(self, instance, value):
        if self.label is None:
            raise ValueError(
                u"Label of an instance of `Field` class may not be None."
            )

        cleaned = self.clean(value)
        instance.__dict__[self.label] = cleaned


class CharField(Field):
    """Represents a string.

    Parameters
    ----------
    max_len: int
        Max length of the string.
    + from Field
    """

    allowed_type = unicode, str

    def __init__(self, max_len=128, **kwargs):
        super(CharField, self).__init__(**kwargs)
        self.max_len = max_len

    def validate(self, value):
        if len(value) > self.max_len:
            err = u"Field `{}` must contain less than {} characters."
            raise ValidationError(err.format(self.label, self.max_len))

        return value


class RegexField(CharField):
    """ Represents a string that match specified pattern.

    Parameters
    ----------
    patter: Optional[unicode]
        Regular expression pattern.
    + from CharField
    """

    pattern = r".*"
    error_message = u"Field `{}` doesn't match `{}` pattern."

    def __init__(self, pattern=None, **kwargs):
        super(RegexField, self).__init__(**kwargs)

        self.pattern = self.pattern if pattern is None else pattern
        self.compiled_pattern = re.compile(self.pattern)

    def validate(self, value):
        value = super(RegexField, self).validate(value)

        if not self.compiled_pattern.match(value):
            raise ValidationError(
                self.error_message.format(self.label, self.pattern)
            )

        return value


class ArgumentsField(Field):
    """Represents a dictionary.
    """

    allowed_type = dict


class EmailField(RegexField):
    """Represents an email address.
    """

    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    error_message = u"Field `{}` is not a valid email address."


class PhoneField(RegexField):
    """Represents a phone number.
    """

    allowed_type = unicode, str, int
    pattern = r"^7\d{10}$"
    error_message = u"Field `{}` is not a valid phone number."

    @staticmethod
    def is_nullable(value):
        return not bool(str(value))

    def validate(self, value):
        value = str(value)
        return super(PhoneField, self).validate(value)


class DateField(Field):
    """Represents a date in `DD.MM. YYYY` format.
    """

    allowed_type = unicode, str

    def validate(self, value):
        try:
            date = dt.datetime.strptime(value, "%d.%m.%Y")
        except ValueError:
            err = u"Field `{}` doesn't match date format `DD.MM.YYYY`."
            raise ValidationError(err.format(self.label))

        return date


class BirthDayField(DateField):
    """Represents a date of birth in `DD.MM. YYYY` format.
    """

    def validate(self, value):
        date = super(BirthDayField, self).validate(value)

        if date < dt.datetime.now() - dt.timedelta(days=(365.25 * 70)):
            err = u"Field `{}` is not a valid birthday."
            raise ValidationError(err.format(self.label))

        return date


class GenderField(Field):
    """Represents a gender.
    """

    UNKNOWN = 0
    MALE = 1
    FEMALE = 2
    GENDERS = {UNKNOWN: u"unknown", MALE: u"male", FEMALE: u"female"}

    allowed_type = unicode, str, int
    choices = GENDERS

    @staticmethod
    def is_nullable(value):
        return not bool(unicode(value))


class ClientIDsField(Field):
    """Represents a non-empty list of integers.
    """

    allowed_type = list

    def validate(self, value):
        if all(isinstance(item, int) and item >= 0 for item in value):
            return value

        err = u"Field `{}` must be a non-empty list with non-negative integers"
        raise ValidationError(err.format(self.label))
