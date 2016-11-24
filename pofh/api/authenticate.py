# encoding: utf-8
""" Authenticate with username and password.

This module presents an API that lets users authenticate with their username
and password, and get a JWT that allows them to set a new password.

"""
from __future__ import unicode_literals, absolute_import

from flask import jsonify, url_for, Blueprint
from marshmallow import fields, Schema

from ..auth import encode_token
from ..idm import get_idm_client
from ..recaptcha import require_recaptcha
from .utils import input_schema
from ..apierror import ApiError
from .password import create_password_token


API = Blueprint('authenticate', __name__)


class BasicAuthSchema(Schema):
    """ Basic auth form. """
    username = fields.String(required=True, allow_none=False)
    password = fields.String(required=True, allow_none=False)


class BasicAuthError(ApiError):
    code = 401
    error_type = 'invalid-creds'


@API.route('/authenticate', methods=['POST'])
@require_recaptcha()
@input_schema(BasicAuthSchema)
def authenticate(data):
    """ Authenticate using username and password.

    Request
        Request body should include two attributes, ``username`` and
        ``password``.

    Response
        The response includes a JSON document with a JWT that can be used to
        set a new password: ``{"token": "..."}``

    Errors
        400: schema-error
        400: invalid recapthca
        401: invalid-creds

    """
    # TODO: Record start time for stats?
    # TODO: Should we implement rate limiting here?
    client = get_idm_client()

    if not client.can_authenticate(data["username"]):
        raise BasicAuthError()

    if not client.verify_current_password(data["username"], data["password"]):
        raise BasicAuthError()

    token = create_password_token(data["username"])

    return jsonify({
        'token': encode_token(token),
        'href': url_for('password.change_password')
    })


def init_api(app):
    """ Register API blueprint. """
    app.register_blueprint(API)
