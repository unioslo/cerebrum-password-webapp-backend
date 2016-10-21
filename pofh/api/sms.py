# encoding: utf-8
""" Authenticate and change password.

This module presents an API that lets users change their passord by
identifying themselves, and verifying their identity by using a nonce sent to
their mobile phone.

"""
from __future__ import unicode_literals, absolute_import, division

import string
import random

from werkzeug.exceptions import Forbidden
from flask import g, jsonify, current_app
from flask import render_template
from flask import Blueprint
from marshmallow import fields, Schema
from datetime import timedelta

from ..auth import require_jwt, encode_token
from ..auth.token import JWTAuthToken
from ..idm import get_idm_client
from ..sms import send_sms
from ..recaptcha import require_recaptcha
from ..template import add_template, get_localized_template
from . import utils
from ..redis import store


API = Blueprint('sms', __name__, url_prefix='/sms')

NS_SMS_SENT = 'sms-sent'
NS_CODE_VERIFIED = 'code-verified'

NONCE_PREFIX = 'sms-nonce:'
NONCE_DEFAULT_LENGTH = 6
NONCE_DEFAULT_EXPIRE_MINUTES = 10


add_template('sms-code',
             "Code: {{ code }}\nValid for {{ minutes }} minutes\n")


class SmsIdentitySchema(Schema):
    """ Verify identity schema. """
    identifier_type = fields.String(required=False, allow_none=False)
    identifier = fields.String(required=True, allow_none=False)
    username = fields.String(required=True, allow_none=False)
    mobile = fields.String(required=True, allow_none=False)


class NonceSchema(Schema):
    """ Verify nonce schema. """
    nonce = fields.String(required=True, allow_none=False)


class ResetPasswordSchema(Schema):
    """ Set new password schema. """
    new_password = fields.String(required=True, allow_none=False)


def get_nonce_length(app):
    return int(app.config['NONCE_LENGTH'])


def get_nonce_expire(app):
    return timedelta(minutes=int(app.config['NONCE_EXPIRE_MINUTES']))


def generate_nonce(length):
    # TODO: Mixed casing or longer length?
    alphanum = string.digits + string.ascii_letters
    return ''.join(random.choice(alphanum) for n in range(length))


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


@API.route('/identify', methods=['POST'])
@require_recaptcha()
@utils.input_schema(SmsIdentitySchema)
def authenticate(data):
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

    """
    client = get_idm_client()
    person_id = client.get_person(data["identifier_type"], data["identifier"])

    if person_id is None:
        raise Forbidden("Invalid person id")

    # Check username
    if data["username"] not in client.get_usernames(person_id):
        raise Forbidden("Invalid username")
    if not client.can_use_sms_service(data["username"]):
        raise Forbidden("User is reserved from SMS service")

    # Check mobile number
    # TODO: Use phonenumbers/dispatcher.parse to compare numbers?
    #       That way, end users don't have to guess the internal formatting in
    #       the IdM
    if data["mobile"] not in client.get_mobile_numbers(person_id):
        raise Forbidden("Invalid mobile number")

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
        return ("Unable to send SMS", 500)

    # TODO: Record stats?
    # TODO: Re-use existing jti?
    t = JWTAuthToken.new(namespace=NS_SMS_SENT,
                         identity=identifier)
    return jsonify({'token': encode_token(t), })


@API.route('/verify', methods=['POST', ])
@require_jwt(namespaces=[NS_SMS_SENT, ])
@utils.input_schema(NonceSchema)
def verify_code(data):
    """ Check submitted sms nonce.

    Request
        The request should include a field with the ``nonce`` to verify.

    Response
        The response includes a JSON document with a JWT that can be used to
        set a new password: ``{"token": "..."}``

    """
    identifier = g.current_token.identity

    if not check_nonce(identifier, data["nonce"]):
        raise Forbidden("Invalid nonce")

    username, mobile = identifier.split(':')

    # TODO: Record stats?
    # TODO: Re-use existing jti?
    # TODO: Invalidate previous token?
    t = JWTAuthToken.new(namespace=NS_CODE_VERIFIED,
                         identity=username)
    return jsonify({'token': encode_token(t), })


@API.route('/set', methods=['POST', ])
@require_jwt(namespaces=[NS_CODE_VERIFIED, ])
@utils.input_schema(ResetPasswordSchema)
def change_password(data):
    """ Check submitted sms nonce.

    Request
        The request should include a field with the ``nonce`` to verify.

    Response
        The response includes an empty JSON document.
    """
    username = g.current_token.identity
    client = get_idm_client()

    if not client.check_new_password(username, data["new_password"]):
        # TODO: Proper error
        raise Exception("Not good enough")

    client.set_new_password(username, data["new_password"])

    # TODO: Record stats?
    # TODO: Return value?
    # TODO: Invalidate token?
    return jsonify({})


def init_app(app):
    app.config.setdefault('NONCE_EXPIRE_MINUTES', NONCE_DEFAULT_EXPIRE_MINUTES)
    app.config.setdefault('NONCE_LENGTH', NONCE_DEFAULT_LENGTH)
