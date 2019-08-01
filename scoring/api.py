#!/usr/bin/env python
# -*- coding: utf-8 -*-

import abc
import json
import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

from . import fields
from . import scoring


SALT = "Otus"
ADMIN_SALT = "42"
ADMIN_LOGIN = "admin"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}


class RequestMeta(type):
    """Metaclass for classes that would use validation.

    Sets proper labels to instances of `Field` class. Saves fields
    for validation to `declared_fields` attribute.
    """

    def __new__(mcls, name, bases, attrs):
        declared_fields = []

        for key, value in attrs.items():
            if isinstance(value, fields.Field):
                if value.label is None:
                    value.label = key
                declared_fields.append((key, value))

        attrs["declared_fields"] = declared_fields
        cls = super(RequestMeta, mcls).__new__(mcls, name, bases, attrs)
        return cls


class Request(object):
    """Base class that uses fields validation.
    """

    __metaclass__ = RequestMeta

    def __init__(self, **kwargs):
        self.raw = {}
        for field_name, field_type in self.declared_fields:
            self.raw[field_name] = kwargs.get(field_name)

    def validate(self):
        """Run validation on an instance of the class.

        Raises
        ------
        fields.ValidationError
            If validation does not succeed.
        """
        for field, value in self.raw.items():
            value = setattr(self, field, value)


class ClientsInterestsRequest(Request):
    client_ids = fields.ClientIDsField(required=True)
    date = fields.DateField(required=False, nullable=True)


class OnlineScoreRequest(Request):
    first_name = fields.CharField(required=False, nullable=True)
    last_name = fields.CharField(required=False, nullable=True)
    email = fields.EmailField(required=False, nullable=True)
    phone = fields.PhoneField(required=False, nullable=True)
    birthday = fields.BirthDayField(required=False, nullable=True)
    gender = fields.GenderField(required=False, nullable=True)

    def validate(self):
        super(OnlineScoreRequest, self).validate()

        if not any(
            (
                self.first_name and self.last_name,
                self.email and self.phone,
                self.birthday and isinstance(self.gender, int),
            )
        ):
            raise fields.ValidationError("Insufficient data.")


class MethodRequest(Request):
    account = fields.CharField(required=False, nullable=True)
    login = fields.CharField(required=True, nullable=True)
    token = fields.CharField(required=True, nullable=True, max_len=512)
    arguments = fields.ArgumentsField(required=True, nullable=True)
    method = fields.CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


class Handler(object):
    """Parent class for all handlers.

    Attributes
    ----------
    request_class : RequestMeta
        Should be a subclass of Request.
    """

    __metaclass__ = abc.ABCMeta

    request_class = None

    def __init__(self, request, context, store):
        self.raw_request = request
        self.context = context
        self.store = store

    def check_auth(self, request):
        """Check if a request is authenticated.

        Parameters
        ----------
        request : Request
            Validated Request instance.
        """
        return True

    @abc.abstractmethod
    def process(self, request):
        """Returns a response.

        Parameters
        ----------
        request : Request
            Validated Request instance.

        Returns
        -------
        response: Tuple[dict, int]
            Tuple of response and status
        """
        NotImplemented

    def update_context(self, request):
        """
        Parameters
        ----------
        request : Request
            Validated Request instance.
        """
        pass

    def get_payload(self):
        """Get a dictionary with data for validation.
        """
        return self.raw_request

    def get_response(self):
        """
        Returns
        -------
        response: Tuple[dict, int]
            Tuple of response and status
        """
        payload = self.get_payload()
        request = self.request_class(**payload)

        try:
            request.validate()
        except fields.ValidationError as exc:
            return str(exc), INVALID_REQUEST

        if not self.check_auth(request):
            return None, FORBIDDEN

        self.update_context(request)
        return self.process(request)


class ClientsInterestsHandler(Handler):
    request_class = ClientsInterestsRequest

    def update_context(self, request):
        self.context["nclients"] = len(request.client_ids)

    def process(self, request):
        response = {
            str(cid): scoring.get_interests(cid) for cid in request.client_ids
        }
        return response, OK


class OnlineScoreHandler(Handler):
    request_class = OnlineScoreRequest

    def update_context(self, request):
        self.context["has"] = []
        for field_name, field_type in request.declared_fields:
            value = getattr(request, field_name)
            if value is not None and not field_type.is_nullable(value):
                self.context["has"].append(field_name)

    def process(self, request):
        if self.context.get("is_admin"):
            response = {"score": 42}
        else:
            score = scoring.get_score(
                phone=request.phone,
                email=request.email,
                birthday=request.birthday,
                gender=request.gender,
                first_name=request.first_name,
                last_name=request.last_name,
            )
            response = {"score": score}

        return response, OK


class MethodHandler(Handler):
    request_class = MethodRequest

    allowed_methods = {
        "online_score": OnlineScoreHandler,
        "clients_interests": ClientsInterestsHandler,
    }

    def check_auth(self, request):
        if request.is_admin:
            digest = hashlib.sha512(
                datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT
            ).hexdigest()
        else:
            digest = hashlib.sha512(
                request.account + request.login + SALT
            ).hexdigest()

        return digest == request.token

    def get_payload(self):
        return self.raw_request.get("body", {})

    def update_context(self, request):
        self.context["is_admin"] = request.is_admin

    def process(self, request):
        method = self.allowed_methods.get(request.method)

        if method is None:
            err = "Method is not allowed."
            return err, INVALID_REQUEST

        handler = method(request.arguments, self.context, self.store)
        return handler.get_response()


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {"method": MethodHandler}
    store = None

    def get_request_id(self, headers):
        return headers.get("HTTP_X_REQUEST_ID", uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None

        try:
            data_string = self.rfile.read(int(self.headers["Content-Length"]))
            request = json.loads(data_string)
        except Exception:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info(
                "%s: %s %s" % (self.path, data_string, context["request_id"])
            )
            if path in self.router:
                try:
                    response, code = self.router[path](
                        {"body": request, "headers": self.headers},
                        context,
                        self.store,
                    )
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {
                "error": response or ERRORS.get(code, "Unknown Error"),
                "code": code,
            }

        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r))


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()

    logging.basicConfig(
        filename=opts.log,
        level=logging.INFO,
        format="[%(asctime)s] %(levelname).1s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
    )

    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

    server.server_close()
