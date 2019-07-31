#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

    Sets proper labels to instances of `Field` class. Also performs
    class-wide validation.
    """

    def __new__(mcls, name, bases, attrs):
        fields_for_validation = []

        for key, value in attrs.items():
            if isinstance(value, fields.Field):
                if value.label is None:
                    value.label = key
                fields_for_validation.append(key)

        attrs["fields_for_validation"] = fields_for_validation
        cls = super(RequestMeta, mcls).__new__(mcls, name, bases, attrs)
        return cls


class Request(object):
    """Base class to use validation mechanism.
    """

    __metaclass__ = RequestMeta

    def __init__(self, **kwargs):
        self.raw_fields = {}
        for field in self.fields_for_validation:
            self.raw_fields[field] = kwargs.get(field)

    def validate(self):
        """Run validation on an instance of the class.

        Raises
        ------
        fields.ValidationError
            If validation does not succeed.
        """
        for field, value in self.raw_fields.items():
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

    def check_auth(self):
        if self.is_admin:
            digest = hashlib.sha512(
                datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT
            ).hexdigest()
        else:
            digest = hashlib.sha512(
                self.account + self.login + SALT
            ).hexdigest()

        return digest == self.token


def online_score_handler(method_request, context, store):
    request = OnlineScoreRequest(**method_request.arguments)

    try:
        request.validate()
    except fields.ValidationError as exc:
        return str(exc), INVALID_REQUEST

    context["has"] = []
    for key, attr in OnlineScoreRequest.__dict__.items():
        if not isinstance(attr, fields.Field):
            continue
        value = getattr(request, key)
        if value is not None and not attr.is_nullable(value):
            context["has"].append(key)

    if method_request.is_admin:
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


def clients_interests_handler(method_request, context, store):
    request = ClientsInterestsRequest(**method_request.arguments)

    try:
        request.validate()
    except fields.ValidationError as exc:
        return str(exc), INVALID_REQUEST

    context["nclients"] = len(request.client_ids)

    response = {
        str(cid): scoring.get_interests(cid) for cid in request.client_ids
    }

    return response, OK


def method_handler(raw_request, ctx, store):
    payload = raw_request.get("body", {})
    request = MethodRequest(**payload)

    allowed_methods = {
        "online_score": online_score_handler,
        "clients_interests": clients_interests_handler,
    }

    try:
        request.validate()
    except fields.ValidationError as exc:
        return str(exc), INVALID_REQUEST

    if not request.check_auth():
        return None, FORBIDDEN

    method = allowed_methods.get(request.method)

    if method is None:
        err = "Method is not allowed."
        return err, INVALID_REQUEST

    return method(request, ctx, store)


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {"method": method_handler}
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
