# encoding: utf-8
""" List usernames.

This module presents an API that lets users list all their user accounts by
identifying themselves.

"""
from __future__ import unicode_literals, absolute_import

from flask import Blueprint, jsonify, render_template, g
from marshmallow import fields, Schema

from ..idm import get_idm_client
from ..recaptcha import require_recaptcha
from ..template import add_template, get_localized_template
from ..sms import send_sms
from ..stats import statsd
from .utils import input_schema, not_empty_validator
from .limits import exponential_ratelimit, get_limiter
from ..apierror import ApiError


API = Blueprint('usernames', __name__)
USERNAME_METRIC_INIT = "kpi.username.init"


class IdentitySchema(Schema):
    """ Person identity form. """
    identifier_type = fields.String(required=True,
                                    allow_none=True,
                                    validate=not_empty_validator)
    identifier = fields.String(required=True,
                               allow_none=False,
                               validate=not_empty_validator)


class NotFoundError(ApiError):
    code = 400


# Template for usernames by SMS
add_template('sms-usernames',
             "Your usernames:\n{{ usernames }}")


@API.route('/list-usernames', methods=['POST'])
@exponential_ratelimit()
@require_recaptcha()
@input_schema(IdentitySchema)
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
        raise NotFoundError()

    g.log.bind(person_id=person_id)
    usernames = client.get_usernames(person_id)

    if not usernames:
        raise NotFoundError()

    if not client.can_show_usernames(person_id):
        template = get_localized_template('sms-usernames')
        message = render_template(template, usernames="\n".join(usernames))
        recipient = client.get_preferred_mobile_number(person_id)
        if recipient:
            try:
                send_sms(recipient, message)
                g.log.info('list-usernames', method='sms', recipient=recipient)
            except:
                pass
        raise NotFoundError()

    statsd.incr(USERNAME_METRIC_INIT)
    g.log.info('list-usernames', method='app')
    return jsonify({'usernames': usernames, })


def init_api(app):
    """ Register blueprint. """
    app.register_blueprint(API)

    limiter = get_limiter(app)
    limiter.limit('10/minute')(list_for_person)
