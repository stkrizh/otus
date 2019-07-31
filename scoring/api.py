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
        for key, value in attrs.items():
            if isinstance(value, fields.Field) and value.label is None:
                value.label = key

        cls = super(RequestMeta, mcls).__new__(mcls, name, bases, attrs)
        return cls

    def __call__(cls, *args, **kwargs):
        """Run validation on each instance of `Field` class.
        """
        if args:
            raise ValueError("Positional arguments are not allowed.")

        instance = super(RequestMeta, cls).__call__()

        for key, value in cls.__dict__.items():
            if isinstance(value, fields.Field):
                setattr(instance, key, kwargs.get(key))

        if hasattr(cls, "validate"):
            instance.validate()

        return instance


class Request(object):
    """Base class to use validation mechanism.
    """

    __metaclass__ = RequestMeta

    def validation(self):
        """Class-wide validation on fields.
        """
        pass


class ClientsInterestsRequest(Request):
    client_ids = fields.ClientIDsField(required=True)
    date = fields.DateField(required=False, nullable=True)

    def __call__(self, ctx, is_admin=False):
        ctx["nclients"] = len(self.client_ids)

        interests = {
            str(cid): scoring.get_interests(cid) for cid in self.client_ids
        }
        return interests


class OnlineScoreRequest(Request):
    first_name = fields.CharField(required=False, nullable=True)
    last_name = fields.CharField(required=False, nullable=True)
    email = fields.EmailField(required=False, nullable=True)
    phone = fields.PhoneField(required=False, nullable=True)
    birthday = fields.BirthDayField(required=False, nullable=True)
    gender = fields.GenderField(required=False, nullable=True)

    def validate(self):
        if not any(
            (
                self.first_name and self.last_name,
                self.email and self.phone,
                self.birthday and isinstance(self.gender, int),
            )
        ):
            raise fields.ValidationError("Insufficient data.")

    def __call__(self, ctx, is_admin=False):
        for key, attr in self.__class__.__dict__.items():
            if not isinstance(attr, fields.Field):
                continue

            value = getattr(self, key)
            if value is not None and not attr.is_nullable(value):
                ctx.setdefault("has", [])
                ctx["has"].append(key)

        if is_admin:
            return {"score": 42}

        score = scoring.get_score(
            phone=self.phone,
            email=self.email,
            birthday=self.birthday,
            gender=self.gender,
            first_name=self.first_name,
            last_name=self.last_name,
        )

        return {"score": score}


class MethodRequest(Request):
    ALLOWED_METHODS = {
        "online_score": OnlineScoreRequest,
        "clients_interests": ClientsInterestsRequest,
    }

    account = fields.CharField(required=False, nullable=True)
    login = fields.CharField(required=True, nullable=True)
    token = fields.CharField(required=True, nullable=True, max_len=512)
    arguments = fields.ArgumentsField(required=True, nullable=True)
    method = fields.CharField(
        required=True, nullable=False, choices=ALLOWED_METHODS
    )

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

    def __call__(self, ctx):
        method = self.ALLOWED_METHODS[self.method]
        request = method(**self.arguments)
        response = request(ctx, self.is_admin)
        return response


def method_handler(raw_request, ctx, store):
    payload = raw_request.get("body", {})

    try:
        request = MethodRequest(**payload)
    except fields.ValidationError as exc:
        return str(exc), INVALID_REQUEST

    if not request.check_auth():
        return None, FORBIDDEN

    try:
        response = request(ctx)
    except fields.ValidationError as exc:
        return str(exc), INVALID_REQUEST

    return response, OK


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
