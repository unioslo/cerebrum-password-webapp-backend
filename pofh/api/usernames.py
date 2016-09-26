# encoding: utf-8
""" API to list usernames. """
from __future__ import unicode_literals, absolute_import

from flask import request, g, jsonify
from flask import Blueprint
from marshmallow import fields, Schema

from .. import auth
from . import utils


API = Blueprint('usernames', __name__, url_prefix='/usernames')

AUTH_NAMESPACE = 'id_exists'


class UsernamesAuthSchema(Schema):
    """ Check if a password is good enough. """
    identifier_type = fields.String(required=True, allow_none=True)
    identifier = fields.String(required=True, allow_none=False)


@API.route('/auth', methods=['POST'])
@utils.validate_schema(UsernamesAuthSchema)
def authenticate():
    data = utils.get_request_data(request)
    # TODO: Look up accounts for (data.identifier_type, data.identifier)
    person_id = 0

    # if not ok: raise HTTPError

    t = auth.token.JWTAuthToken.new(namespace=AUTH_NAMESPACE,
                                    identity=str(person_id))

    return jsonify({'token': auth.encode_token(t), })


@API.route('/usernames', methods=['GET', ])
@auth.require_jwt(namespaces=[AUTH_NAMESPACE, ])
def list_usernames():
    """ List usernames for the current JWT token. """
    person_id = g.current_token.identity
    # TODO: Lookup usernames
    usernames = ['foo', 'bar', 'baz', 'person_id:{!s}'.format(person_id)]

    return jsonify({'usernames': usernames, })
