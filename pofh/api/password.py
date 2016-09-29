# encoding: utf-8
""" API to list usernames. """
from __future__ import unicode_literals, absolute_import

from flask import request, g, jsonify
from flask import Blueprint
from marshmallow import fields, Schema

from ..auth import require_jwt, encode_token
from ..auth.token import JWTAuthToken
from ..idm import get_idm_client
from ..recaptcha import require_recaptcha
from . import utils


API = Blueprint('password', __name__, url_prefix='/password')

NS_BASIC_AUTH = 'basic-auth'


class ChangePasswordSchema(Schema):
    """ Check if a password is good enough. """
    old_password = fields.String(required=True, allow_none=False)
    new_password = fields.String(required=True, allow_none=False)


class BasicAuthSchema(Schema):
    """ Basic auth form. """
    username = fields.String(required=True, allow_none=False)
    password = fields.String(required=True, allow_none=False)


@API.route('/auth', methods=['POST'])
@require_recaptcha()
@utils.validate_schema(BasicAuthSchema)
def authenticate():
    """ Authenticate using username and password. """
    data = utils.get_request_data(request)

    client = get_idm_client()
    if not client.verify_current_password(data["username"], data["password"]):
        # TODO: Proper exception
        raise Exception("Invalid username or password")

    t = JWTAuthToken.new(namespace=NS_BASIC_AUTH,
                         identity=data["username"])
    # TODO: Record stats?
    return jsonify({'token': encode_token(t), })


@API.route('/set', methods=['POST'])
@require_jwt(namespaces=[NS_BASIC_AUTH, ])
@utils.validate_schema(ChangePasswordSchema)
def change_password():
    data = utils.get_request_data(request)
    username = g.current_token.identity
    client = get_idm_client()

    # Check if new password is good enough
    if not client.check_new_password(username, data["new_password"]):
        # TODO: Proper error? Return value?
        raise Exception("Not good enough")

    # Re-check current password
    if not client.verify_current_password(username, data["old_password"]):
        # TODO: Proper exception
        raise Exception("Invalid password")

    client.set_new_password(username, data["new_password"])
    # TODO: Record stats?
    # TODO: Return value?
    return jsonify({})
