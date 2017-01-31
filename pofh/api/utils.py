# encoding: utf-8
""" Simple api utils. """
from __future__ import unicode_literals, absolute_import

from flask import request
from functools import wraps
from .. import apierror


def get_request_data(req):
    """ Get request data.

    Gets request data from the following Content-Types:

    - application/json
    - multipart/form-data
    - application/x-www-form-urlencoded
    - application/x-url-encoded

    """
    if req.is_json:
        return req.get_json()
    else:
        return req.form


class SchemaError(apierror.ApiError):
    """ Schema validation error."""
    code = 400


def route_value_validator(val):
    return val != '' and '/' not in val


def not_empty_validator(val):
    return val != ''


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
