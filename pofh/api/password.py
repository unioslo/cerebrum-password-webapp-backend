# encoding: utf-8
""" Change password.

This module presents an API that lets users change their passord if they have a
JWT that allows them to do so.

"""
from __future__ import unicode_literals, absolute_import

from flask import g, Blueprint
from marshmallow import fields, Schema

from ..auth import require_jwt
from ..auth.token import JWTAuthToken
from ..idm import get_idm_client
from . import utils


API = Blueprint('password', __name__)

NS_SET_PASSWORD = 'allow-set-password'


class ResetPasswordSchema(Schema):
    """ Set new password schema. """
    password = fields.String(required=True, allow_none=False)


class InvalidNewPassword(utils.ApiError):
    code = 400
    error_type = 'weak-password'


def create_password_token(username):
    return JWTAuthToken.new(namespace=NS_SET_PASSWORD, identity=username)


@API.route('/password', methods=['POST'])
@require_jwt(namespaces=[NS_SET_PASSWORD, ])
@utils.input_schema(ResetPasswordSchema)
def change_password(data):
    """ Set a new password.

    Request
        Request headers should include a valid JWT.
        Request body should include one attribute, ``password``.

    Response
        Returns an empty 204 response if password gets changed.

    Errors
        400: schema-error
        400: weak-password
        401: missing or invalid jwt
        403: invalid jwt namespace

    """
    username = g.current_token.identity
    client = get_idm_client()

    # Check if new password is good enough
    if not client.check_new_password(username, data["password"]):
        # TODO: Include errors (broken rules) from idm?
        raise InvalidNewPassword()

    client.set_new_password(username, data["password"])

    # TODO: Invalidate token?
    #  - we should keep a blacklist with used tokens in our redis store

    # TODO: Record stats:
    #  - score?
    #  - time from start?

    return ('', 204)


def init_api(app):
    """ Register API blueprint. """
    app.register_blueprint(API)
