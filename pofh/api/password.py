# encoding: utf-8
""" API to list usernames. """
from __future__ import unicode_literals, absolute_import

from flask import request, jsonify
from flask import Blueprint
from marshmallow import fields, Schema

from .. import auth
from . import utils


API = Blueprint('password', __name__, url_prefix='/password')

AUTH_NAMESPACE = 'verified'


class NewPasswordSchema(Schema):
    """ Check if a password is good enough. """
    old_password = fields.String(required=True, allow_none=False)
    new_password = fields.String(required=True, allow_none=False)


class BasicAuthSchema(Schema):
    username = fields.String(required=True, allow_none=False)
    password = fields.String(required=True, allow_none=False)


@API.route('/auth', methods=['POST'])
@utils.validate_schema(BasicAuthSchema)
def authenticate():
    data = utils.get_request_data(request)
    # TODO: Check that data.username, data.password is correct

    # if not ok: raise HTTPError

    t = auth.token.JWTAuthToken.new(namespace=AUTH_NAMESPACE,
                                    identity=data.username)
    return jsonify({'token': auth.encode_token(t), })


@API.route('/set', methods=['POST'])
@auth.require_jwt(namespaces=[AUTH_NAMESPACE, ])
@utils.validate_schema(NewPasswordSchema)
def change_password():
    data = utils.get_request_data(request)

    # TODO: Try to update password with (data.old_password, data.new_password)
    return jsonify({})
