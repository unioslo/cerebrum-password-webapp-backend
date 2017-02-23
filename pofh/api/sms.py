# encoding: utf-8
""" SMS nonce API.

This module presents an API that lets users identify themselves, and verify
their identity by using a one time code (nonce) sent to their mobile phone.

Settings
--------
``NONCE_EXPIRE_MINUTES`` (:py:class:`int`)
    How long the one time code is valid, in minutes. Defaults to
    `NONCE_DEFAULT_EXPIRE_MINUTES`.

``NONCE_LENGTH`` (:py:class:`int`)
    Number of characters in the one time code. Defaults to
    `NONCE_DEFAULT_LENGTH`.


SMS templates
-------------
The SMS will contain text from an internal default template, ``sms-code``. To
customize this template, place a template named ``sms-code`` and/or one or more
localized templates named ``sms-code.<language-tag>`` in the application
templates folder.

The templates folder defaults to a directory named ``templates`` in the
application instance path.

Templates will receive two context variables:

``minutes``
    How many minutes the template is valid for.

``code``
    The one time code that matches the issued JWT.

In debug mode, an additional route for testing the templates is added to the
API.

"""
from __future__ import unicode_literals, absolute_import, division

import string
import random

from flask import g, jsonify, current_app, url_for
from flask import render_template
from flask import Blueprint
from marshmallow import fields, Schema
from datetime import timedelta

from .. import auth
from ..auth.token import JWTAuthToken
from ..idm import get_idm_client, IdmClientException
from ..sms import send_sms, parse_number, filter_number
from ..sms.dispatcher import FilterException
from ..recaptcha import require_recaptcha
from ..template import add_template, get_localized_template
from .utils import input_schema, route_value_validator, not_empty_validator
from .limits import exponential_ratelimit, get_limiter
from ..apierror import ApiError
from ..redisclient import store
from ..stats import statsd
from .password import create_password_token, NS_SET_PASSWORD


API = Blueprint('sms', __name__, url_prefix='/sms')

NS_VERIFY_NONCE = 'allow-verify-nonce'

NONCE_PREFIX = 'sms-nonce:'
NONCE_DEFAULT_LENGTH = 6
NONCE_DEFAULT_EXPIRE_MINUTES = 10

SMS_METRIC_TIME = "kpi.sms.time_used"
SMS_METRIC_INIT = "kpi.sms.init"
SMS_METRIC_DONE = "kpi.sms.done"
SMS_METRIC_DIFF = "kpi.sms.diff"


class InvalidMobileNumber(ApiError):
    code = 400


class NotFoundError(ApiError):
    code = 400


class ServiceUnavailable(ApiError):
    code = 403


class InvalidNonce(ApiError):
    code = 401
    error_type = 'invalid-nonce'


# default sms template
add_template('sms-code',
             "Code: {{ code }}\nValid for {{ minutes }} minutes\n")


class SmsIdentitySchema(Schema):
    """ Verify identity schema. """
    identifier_type = fields.String(required=False,
                                    allow_none=False,
                                    validate=not_empty_validator)
    identifier = fields.String(required=True,
                               allow_none=False,
                               validate=not_empty_validator)
    username = fields.String(required=True,
                             allow_none=False,
                             validate=route_value_validator)
    mobile = fields.String(required=True,
                           allow_none=False,
                           validate=not_empty_validator)


class NonceSchema(Schema):
    """ Verify nonce schema. """
    nonce = fields.String(required=True, allow_none=False)


def get_nonce_length(app):
    """ Get nonce length for current app. """
    return int(app.config['NONCE_LENGTH'])


def get_nonce_expire(app):
    """ Get nonce expire time for current app. """
    return timedelta(minutes=int(app.config['NONCE_EXPIRE_MINUTES']))


def generate_nonce(length):
    """ Generate a nonce of a given length. """
    ambiguous = 'B8G6I1l0OQDS5Z2'
    alphanum = string.digits + string.ascii_letters
    choices = [c for c in alphanum if c not in ambiguous]
    return ''.join(random.choice(choices) for n in range(length))


def save_nonce(identifier, nonce, duration):
    """ Store a new issued nonce value. """
    name = '{!s}{!s}'.format(NONCE_PREFIX, identifier)
    store.setex(name, duration, nonce)  # NOTE: StrictRedis argument order


def check_nonce(identifier, nonce):
    """ Check if a given nonce value is valid. """
    name = '{!s}{!s}'.format(NONCE_PREFIX, identifier)
    return nonce and store.get(name) == nonce


def clear_nonce(identifier):
    """ Clear a used nonce value. """
    name = '{!s}{!s}'.format(NONCE_PREFIX, identifier)
    store.delete(name)


@API.route('', methods=['POST'])
@exponential_ratelimit()
@require_recaptcha()
@input_schema(SmsIdentitySchema)
def identify(data):
    """ Check submitted person info and send sms nonce.

    Request
        The request should include fields:

        ``identifier_type``
            A person identifier type.
        ``identifier``
            An person identifier.
        ``username``
            Username of a user to change passwords for.
        ``mobile``
            A mobile number to send the nonce to.

    Response
        The response includes a JSON document with a JWT that can be used to
        verify the sent nonce: ``{"token": "..."}``

    Errors
        400: schema error
        400: not found
        400: invalid number
        401: invalid recapthca
        403: service-unavailable

    """
    client = get_idm_client()
    person_id = client.get_person(data["identifier_type"], data["identifier"])

    if person_id is None:
        raise NotFoundError()

    # Check username
    if data["username"] not in client.get_usernames(person_id):
        raise NotFoundError()

    # Check mobile number
    mobile = parse_number(data["mobile"])
    valid_numbers = [parse_number(x)
                     for x in client.get_mobile_numbers(
                     person_id=person_id, username=data["username"])]

    if mobile is None:
        # record stats?
        raise InvalidMobileNumber(
            details={'reason': 'unparseable-phone-number'})

    if mobile not in valid_numbers:
        # record stats?
        raise NotFoundError()

    # Check for eligibility
    try:
        if not client.can_use_sms_service(person_id=person_id,
                                          username=data["username"]):
            # record stats?
            raise ServiceUnavailable()
    except IdmClientException as e:
        raise ServiceUnavailable(details={'reason': str(e)})

    # Check if mobile number will be filtered
    try:
        filter_number(mobile)
    except FilterException as e:
        raise InvalidMobileNumber(details={'reason': str(e)})

    # Everything is OK, store and send nonce
    identifier = '{!s}:{!s}'.format(data["username"], data["mobile"])

    expire = get_nonce_expire(current_app)
    nonce = generate_nonce(get_nonce_length(current_app))
    save_nonce(identifier, nonce, expire)

    template = get_localized_template('sms-code')
    message = render_template(
        template,
        code=nonce,
        minutes=expire.total_seconds()//60)
    if not send_sms(data["mobile"], message):
        raise ServiceUnavailable(details={'reason': 'cannot-send-sms'})

    # TODO: Re-use existing jti?
    token = JWTAuthToken.new(namespace=NS_VERIFY_NONCE,
                             identity=identifier)
    return jsonify({
        'token': auth.encode_token(token),
        'href': url_for('.verify_code'),
    })


@API.route('/verify', methods=['POST', ])
@exponential_ratelimit()
@auth.require_jwt(namespaces=[NS_VERIFY_NONCE, ])
@input_schema(NonceSchema)
def verify_code(data):
    """ Check submitted sms nonce.

    Request
        The request should include a field with the ``nonce`` to verify.

    Response
        The response includes a JSON document with a JWT that can be used to
        set a new password: ``{"token": "..."}``

    Errors
        400: schema error
        401: invalid nonce
        401: missing jwt
        403: invalid jwt

    """
    identifier = g.current_token.identity

    if not check_nonce(identifier, data["nonce"]):
        # record stats?
        raise InvalidNonce()

    username, mobile = identifier.split(':')

    # TODO: Invalidate previous token?

    token = create_password_token(username)

    return jsonify({
        'token': auth.encode_token(token),
        'href': url_for('password.change_password')
    })


def test_template():
    """ Render a test template. """
    template = get_localized_template('sms-code')
    expire = get_nonce_expire(current_app)
    length = get_nonce_length(current_app)
    return render_template(
        template,
        code=generate_nonce(length),
        minutes=expire.total_seconds()//60)


@auth.signal_token_sign.connect
def _record_metric_init(token, **kwargs):
    """ Records usage metrics. """
    # Whenever a *new* token with namespace `NS_VERIFY_NONCE` is signed, we
    # assume new "sms session" has been started.
    if (token.namespace != NS_VERIFY_NONCE or
            (g.current_token is not None and
             g.current_token.jti == token.jti)):
        # ignore unrelated tokens and token renewal
        return
    statsd.incr(SMS_METRIC_INIT)
    statsd.incr(SMS_METRIC_DIFF)


@auth.signal_token_sign.connect
def _record_metric_done(token, **kwargs):
    """ Records usage metrics. """
    # This is intended as a receiver for `auth.signal_token_sign`. Whenever a
    # *new* token with namespace `NS_SET_PASSWORD` is signed, using a
    # `NS_VERIFY_NONCE` token, we regard the "sms session" to be over.
    if (g.current_token is None or
            g.current_token.namespace != NS_VERIFY_NONCE or
            token.namespace != NS_SET_PASSWORD):
        # unrelated event
        return
    try:
        time_used_ms = int(
            (token.iat - g.current_token.iat).total_seconds() * 1000)
    except:
        return
    statsd.timing(SMS_METRIC_TIME, time_used_ms)
    statsd.incr(SMS_METRIC_DONE)
    statsd.decr(SMS_METRIC_DIFF)


def init_api(app):
    """ Read config and register SMS API blueprint. """
    app.config.setdefault('NONCE_EXPIRE_MINUTES', NONCE_DEFAULT_EXPIRE_MINUTES)
    app.config.setdefault('NONCE_LENGTH', NONCE_DEFAULT_LENGTH)
    if app.debug:
        API.route('/test-template')(test_template)
    app.register_blueprint(API)

    limiter = get_limiter(app)
    limiter.limit('10/minute')(verify_code)
    limiter.limit('10/minute')(identify)
