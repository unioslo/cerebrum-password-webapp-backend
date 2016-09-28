# encoding: utf-8
""" List usernames.

This module presents an API that lets users list all their user accounts by
identifying themselves.

"""
from __future__ import unicode_literals, absolute_import

from flask import request, g, jsonify
from flask import Blueprint
from marshmallow import fields, Schema

from .. import auth
from .. import idm
from . import utils


API = Blueprint('usernames', __name__, url_prefix='/usernames')

NS_IDENTITY_FOUND = 'identity-found'


class IdentitySchema(Schema):
    identifier_type = fields.String(required=True, allow_none=True)
    identifier = fields.String(required=True, allow_none=False)


@API.route('/identify', methods=['POST'])
@utils.input_schema(IdentitySchema)
def authenticate(data):
    """ Identify person. """
    data = utils.get_request_data(request)

    # TODO: Check recaptcha
    client = idm.get_idm_client()
    person_id = client.get_person(data["identifier_type"], data["identifier"])

    if person_id is None:
        # TODO: Proper exception
        raise Exception("Invalid person id")

    t = auth.token.JWTAuthToken.new(namespace=NS_IDENTITY_FOUND,
                                    identity=str(person_id))

    # TODO: Record stats?
    return jsonify({'token': auth.encode_token(t), })


@API.route('/list', methods=['GET', ])
@auth.require_jwt(namespaces=[NS_IDENTITY_FOUND, ])
def list_usernames():
    """ List usernames for the current JWT token. """
    person_id = g.current_token.identity
    client = idm.get_idm_client()
    usernames = client.get_usernames(person_id)
    # TODO: Record stats?
    return jsonify({'usernames': usernames, })
