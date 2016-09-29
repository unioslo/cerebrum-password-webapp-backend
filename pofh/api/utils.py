# encoding: utf-8
""" Simple api utils. """
from __future__ import unicode_literals, absolute_import

# from werkzeug.exceptions import BadRequest

from flask import current_app
from flask import request
from flask import abort
from functools import wraps


def get_request_data(req):
    """ Get request form data. """
    if req.is_json:
        return req.get_json()
    else:
        return req.form


def validate_schema(schema_type):
    """ automatically validate schema. """
    schema = schema_type()

    def wrap(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            errors = schema.validate(get_request_data(request))
            if (errors):
                # TODO: Render better error message
                abort(400, {'msg': 'Invalid request data', 'errors': errors})
            return func(*args, **kwargs)
        return wrapper
    return wrap


def input_schema(schema_type):
    schema = schema_type()

    def wrap(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = schema.load(get_request_data(request))
            if (result.errors):
                # TODO: Render better error message
                abort(400, {'msg': 'Invalid request data', 'errors': result.errors})
            return func(result.data, *args, **kwargs)
        return wrapper
    return wrap
