class ValidationError(Exception):
    pass


class Field(object):
    """Base class for fields validation.

    Attributes
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
        return bool(value)

    def validate(self, value, *args, **kwargs):
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
        value : Any
            Validated `value`.
        """
        if self.required and value is None:
            err = "Field `{}` is required."
            raise ValidationError(err.format(self.label))

        if not self.nullable and not self.is_nullable(value):
            err = "Field `{}` may not be nullable."
            raise ValidationError(err.format(self.label))

        return value

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

        cleaned_value = self.validate(value)
        instance.__dict__[self.label] = cleaned_value


class CharField(Field):
    pass


class ArgumentsField(Field):
    pass


class EmailField(CharField):
    pass


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

    
