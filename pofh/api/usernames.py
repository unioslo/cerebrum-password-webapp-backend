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
from ..recaptcha import require_recaptcha
from . import utils


API = Blueprint('usernames', __name__, url_prefix='/usernames')

NS_IDENTITY_FOUND = 'identity-found'


class IdentitySchema(Schema):
    """ Person identity form. """
    identifier_type = fields.String(required=True, allow_none=True)
    identifier = fields.String(required=True, allow_none=False)


@API.route('/identify', methods=['POST'])
@require_recaptcha()
@utils.input_schema(IdentitySchema)
def authenticate(data):
    """ Authenticate using person info.

    Request
        Request body should include two attributes, ``identifier_type`` and
        ``identifier``.

    Response
        The response includes a JSON document with a JWT that can be used to
        list usernames owned by that person: ``{"token": "..."}``

    """
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
    """ List usernames owned by a person.

    Request
        Request headers should include a JWT that identifies the person.

    Response
        The response includes a JSON document with a list of usernames:
        ``{"usernames": [...]}``

    """
    person_id = g.current_token.identity
    client = idm.get_idm_client()
    usernames = client.get_usernames(person_id)
    # TODO: Record stats?
    return jsonify({'usernames': usernames, })
