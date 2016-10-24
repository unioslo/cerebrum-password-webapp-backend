# encoding: utf-8
""" Simple api utils. """
from __future__ import unicode_literals, absolute_import

from flask import request, jsonify
from functools import wraps


class ApiError(Exception):
    """ Api Error. """

    code = 400
    error_type = "generic-api-error"

    def __init__(self, details=None):
        super(ApiError, self).__init__(self.error_type)
        self.details = details or None

    def __repr__(self):
        return "{!s}(details={!r})".format(
            self.__class__.__name__,
            self.details)


def handle_api_error(error):
    """ Error handler for errors of type ApiError. """
    response = jsonify(
        error=error.error_type,
        details=error.details or {},
    )
    response.status_code = error.code
    return response


def get_request_data(req):
    """ Get request data. """
    if req.is_json:
        return req.get_json()
    else:
        return req.form


class SchemaError(ApiError):
    """ Schema validation error."""
    code = 400
    error_type = "schema-error"


def validate_schema(schema_type):
    """ automatically validate schema. """
    schema = schema_type()

    def wrap(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            errors = schema.validate(get_request_data(request))
            if (errors):
                raise SchemaError(errors)
            return func(*args, **kwargs)
        # TODO: Auto-document schema.
        wrapper.__doc__ += (
            "\nThe request body should include form data encoded as "
            " ``application/json`` or ``application/x-www-from-urlencoded``\n")
        return wrapper
    return wrap


def input_schema(schema_type):
    """ automatically validate and deserialize schema.

    The deserialized schema will be given as the first argument to the wrapped
    handler.

    Example:
        @input_schema(SomeSchemaClass)
        def foo(data):
            return jsonify(data)
    """
    schema = schema_type()

    def wrap(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = schema.load(get_request_data(request))
            if (result.errors):
                raise SchemaError(result.errors)
            return func(result.data, *args, **kwargs)
        # TODO: Auto-document schema.
        wrapper.__doc__ += (
            "The request body should include form data encoded as "
            " ``application/json`` or ``application/x-www-from-urlencoded``\n")
        return wrapper
    return wrap
