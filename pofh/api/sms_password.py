# encoding: utf-8
""" API to list usernames. """
from __future__ import unicode_literals, absolute_import

from flask import request, g, jsonify
from flask import Blueprint
from marshmallow import fields, Schema

from .. import auth
from . import utils
from . import password


API = Blueprint('sms', __name__, url_prefix='/sms')

AUTH_NAMESPACE = 'sms'


class SMSPasswordAuthSchema(Schema):
    """ Check if a password is good enough. """
    identifier_type = fields.String(required=False, allow_none=False)
    identifier = fields.String(required=True, allow_none=False)
    username = fields.String(required=True, allow_none=False)
    mobile = fields.String(required=True, allow_none=False)


class SMSPasswordVerifySchema(Schema):
    username = fields.String(required=True, allow_none=False)
    nonce = fields.String(required=True, allow_none=False)


@API.route('/auth', methods=['POST'])
@utils.validate_schema(SMSPasswordAuthSchema)
def authenticate():
    data = utils.get_request_data(request)
    # TODO: Look up accounts for (data.identifier_type, data.identifier)
    # TODO: Verify that data.username is in that set
    # TODO: Get contacts for person
    # TODO: Verify that data.mobile is in that set
    identifier = 'fhl:97709133'

    # if not ok: raise HTTPError

    t = auth.token.JWTAuthToken.new(namespace=AUTH_NAMESPACE,
                                    identity="{!s}:{!s}".format(identifier))

    return jsonify({'token': auth.encode_token(t), })


@API.route('/verify')
@utils.validate_schema(SMSPasswordVerifySchema)
@auth.require_jwt(namespaces=[AUTH_NAMESPACE, ])
def verify_code():
    data = utils.get_request_data(request)
    # TODO: verify that code is OK
    username = 'fhl'

    # of not OK

    t = auth.token.JWTAuthToken.new(namespace=password.AUTH_NAMESPACE,
                                    identity=username)

    return jsonify({'token': auth.encode_token(t), })


@API.route('/usernames', methods=['GET', ])
@auth.require_jwt(namespaces=[AUTH_NAMESPACE, ])
def list_usernames():
    """ List usernames for the current JWT token. """
    person_id = g.current_token.identity
    # TODO: Lookup usernames
    usernames = ['foo', 'bar', 'baz', 'person_id:{!s}'.format(person_id)]

    return jsonify({'usernames': usernames, })
