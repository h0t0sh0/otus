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
import scoring

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"

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

UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class Field(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, required=False, nullable=False):
        self.required = required
        self.nullable = nullable

    @abc.abstractmethod
    def parse_validate(self, value):
        return value

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Field:
            if any("parse_validate" in B.__dict__ for B in C.__mro__):
                return True

        return NotImplemented


class CharField(Field):
    def parse_validate(self, value):
        if isinstance(value, basestring):
            return value if isinstance(value, unicode) else value.decode("utf-8")
        raise ValueError("value is not a string")


class ArgumentsField(Field):
    def parse_validate(self, value):
        if isinstance(value, dict):
            return value
        raise ValueError("value is not a dictionary")


class EmailField(CharField):
    def parse_validate(self, value):
        value = super(EmailField, self).parse_validate(value)
        if "@" in value:
            return value
        raise ValueError("value is not an email")


class PhoneField(Field):
    def parse_validate(self, value):
        value = str(value)
        if value and value.isdigit() and value[0] == "7":
            return value


class DateField(Field):
    def parse_validate(self, value):
        try:
            d = datetime.datetime.strptime(value, "%d.%m.%Y")
            return d
        except:
            raise ValueError("value is not a date")


class BirthDayField(DateField):
    def parse_validate(self, value):
        bd = super(BirthDayField, self).parse_validate(value)
        diff = datetime.datetime.now() - bd
        if (diff.days / 365) > 70:
            raise ValueError("age is greater then 70")
        return bd


class GenderField(Field):
    def parse_validate(self, value):
        if isinstance(value, int) and value in GENDERS:
            return value
        raise ValueError("value is not valid gender")


class ClientIDsField(Field):
    def parse_validate(self, value):
        if isinstance(value, list) and all(isinstance(cid, int) for cid in value):
            return value
        raise ValueError("value is not a client ids list")

    def length(self):
        return len(self.value)


class RequestHandler(object):
    def validate_handle(self, request, arguments, ctx, store):
        if not request.is_valid():
            return request.errfmt(), INVALID_REQUEST
        return self.handle(request, arguments, ctx, store)

    def handle(request, arguments, ctx, store):
        return {}, OK


class RequestMeta(type):
    def __new__(mcs, name, bases, attrs):
        fields_list = []

        for k, v in attrs.items():
            if isinstance(v, Field):
                v.name = k
                fields_list.append(v)

        cls = super(RequestMeta, mcs).__new__(mcs, name, bases, attrs)
        cls.fields = fields_list

        return cls


class Request(object):
    __metaclass__ = RequestMeta

    def __init__(self, request):
        self.errors = []
        self.request = request
        self.is_cleaned = False

    def clean(self):

        for f in self.fields:
            value = None

            try:
                value = self.request[f.name]
            except (KeyError, TypeError):
                if f.required:
                    self.errors.append("{} field not found".format(f.name))
                    continue

            if not value and value != 0:
                if f.nullable:
                    setattr(self, f.name, value)
                else:
                    self.errors.append("{} field is empty".format(f.name))
                continue

            try:
                setattr(self, f.name, f.parse_validate(value))
            except ValueError:
                self.errors.append("{} field validation error".format(f.name))

        self.is_cleaned = True

    def is_valid(self):

        if not self.is_cleaned:
            self.clean()

        return not self.errors

    def errfmt(self):
        return ", ".join(self.errors)


class ClientsInterestsRequest(Request):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class ClientsInterestsHandler(RequestHandler):
    request_type = ClientsInterestsRequest

    def handle(self, request, arguments, ctx, store):
        ctx["nclients"] = len(arguments.client_ids)
        return {
            cid: scoring.get_interests(store, cid) for cid in arguments.client_ids}, OK


class OnlineScoreRequest(Request):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def is_valid(self):

        default_valid = super(OnlineScoreRequest, self).is_valid()
        if not default_valid:
            return default_valid

        cond = []
        cond.append(bool(self.phone and self.email))
        cond.append(bool(self.first_name and self.last_name))
        cond.append(bool(self.gender is not None and self.birthday))

        if not any(cond):
            self.errors.append("Needed one of phone-email, first_name-last_name, "
                               "gender-birthday")
            return False

        return True


class OnlineScoreHandler(RequestHandler):
    request_type = OnlineScoreRequest

    def handle(self, request, arguments, ctx, store):
        if request.is_admin:
            score = 42
        else:
            score = scoring.get_score(store,
                                      arguments.phone,
                                      arguments.email,
                                      arguments.birthday,
                                      arguments.gender,
                                      arguments.first_name,
                                      arguments.last_name)
        ctx["has"] = [
            f.name for f in self.request_type.fields if (getattr(arguments, f.name) or
                                                         getattr(arguments, f.name) == 0)
        ]

        return {"score": score}, OK


class MethodRequest(Request):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    if request.is_admin:
        datenow = datetime.datetime.now().strftime("%Y%m%d%H")
        digest = hashlib.sha512(datenow + ADMIN_SALT).hexdigest()
    else:
        digest = hashlib.sha512(request.account + request.login + SALT).hexdigest()

    if digest == request.token:
        return True
    return False


def method_handler(request, ctx, store):

    method_map = {
        "online_score": OnlineScoreHandler,
        "clients_interests": ClientsInterestsHandler}

    method_request = MethodRequest(request["body"])
    if not method_request.is_valid():
        return method_request.errfmt(), INVALID_REQUEST

    if not check_auth(method_request):
        return None, FORBIDDEN

    handler_cls = method_map.get(method_request.method, None)
    if not handler_cls:
        return "Method not found", NOT_FOUND

    arguments = handler_cls().request_type(method_request.arguments)
    if not arguments.is_valid():
        return arguments.errfmt(), INVALID_REQUEST

    response, code = handler_cls().validate_handle(
        method_request,
        arguments,
        ctx, store)
    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path](
                        {"body": request, "headers": self.headers},
                        context,
                        self.store)
                except Exception, e:
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
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r))
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log,
                        level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
