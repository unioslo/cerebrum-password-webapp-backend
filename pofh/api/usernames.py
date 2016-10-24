# encoding: utf-8
""" List usernames.

This module presents an API that lets users list all their user accounts by
identifying themselves.

"""
from __future__ import unicode_literals, absolute_import

from flask import jsonify
from flask import Blueprint
from marshmallow import fields, Schema

from ..idm import get_idm_client
from ..recaptcha import require_recaptcha
from . import utils


API = Blueprint('usernames', __name__)


class IdentitySchema(Schema):
    """ Person identity form. """
    identifier_type = fields.String(required=True, allow_none=True)
    identifier = fields.String(required=True, allow_none=False)


class IdentityError(utils.ApiError):
    code = 400
    error_type = 'person-not-found'


@API.route('/list-usernames', methods=['POST'])
@require_recaptcha()
@utils.input_schema(IdentitySchema)
def list_for_person(data):
    """ Authenticate using person info.

    Request
        Request body should include two attributes, ``identifier_type`` and
        ``identifier``.

    Response
        The response contains a JSON document with a list of usernames:
        ``{"usernames": [...]}``

    Errors
        - 400: schema error
        - 401: invalid recaptcha

    """
    client = get_idm_client()
    person_id = client.get_person(data["identifier_type"], data["identifier"])

    if person_id is None:
        raise IdentityError()

    usernames = client.get_usernames(person_id)

    # TODO: Record stats?

    return jsonify({'usernames': usernames, })


def init_api(app):
    """ Register blueprint. """
    app.register_blueprint(API)
