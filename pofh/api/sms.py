# encoding: utf-8
""" Authenticate and change password.

This module presents an API that lets users change their passord by
identifying themselves, and verifying their identity by using a nonce sent to
their mobile phone.

"""
from __future__ import unicode_literals, absolute_import

from flask import request, g, jsonify
from flask import Blueprint
from marshmallow import fields, Schema

from ..auth import require_jwt, encode_token
from ..auth.token import JWTAuthToken
from ..idm import get_idm_client
from ..sms import send_sms
from . import utils


API = Blueprint('sms', __name__, url_prefix='/sms')

NS_SMS_SENT = 'sms-sent'
NS_CODE_VERIFIED = 'code-verified'


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


def save_nonce(identifier, nonce):
    """ Store a new issued nonce value. """
    # TODO
    pass


def check_nonce(identifier, nonce):
    """ Check if a given nonce value is valid. """
    # TODO
    return False


def clear_nonce(identifier):
    """ Clear a used nonce value. """
    # TODO
    pass


@API.route('/identify', methods=['POST'])
@utils.input_schema(SmsIdentitySchema)
def authenticate(data):
    """ Check submitted person info and send sms nonce. """
    # TODO: Check recaptcha
    client = get_idm_client()
    person_id = client.get_person(data["identifier_type"], data["identifier"])

    if person_id is None:
        # TODO: Proper exception
        raise Exception("Invalid person id")

    # Check username
    if data["username"] not in client.get_usernames(person_id):
        # TODO: Proper exception
        raise Exception("Invalid username")
    if not client.can_use_sms_service(data["username"]):
        # TODO: Proper exception
        raise Exception("User is reserved from SMS service")

    # Check mobile number
    if data["mobile"] not in client.get_mobile_numbers(person_id):
        # TODO: Proper exception
        raise Exception("Invalid mobile number")

    # Everything is OK, store and send nonce
    identifier = '{!s}:{!s}'.format(data["username"], data["mobile"])

    # TODO: generate code and send SMS
    nonce = 'foo'
    save_nonce(identifier, nonce)
    # TODO: Proper template system? Language?
    message = "Your code: {!s}".format(nonce)
    send_sms(data["mobile"], message)

    # TODO: Record stats?

    # TODO: Re-use existing jti?
    t = JWTAuthToken.new(namespace=NS_SMS_SENT,
                         identity="{!s}:{!s}".format(identifier))
    return jsonify({'token': encode_token(t), })


@API.route('/verify')
@require_jwt(namespaces=[NS_SMS_SENT, ])
@utils.input_schema(NonceSchema)
def verify_code(data):
    """ Check submitted sms nonce. """
    data = utils.get_request_data(request)
    identifier = g.current_token.identity

    if not check_nonce(identifier, data["nonce"]):
        raise Exception("Invalid code")

    username, mobile = identifier.split(':')

    # TODO: Record stats?
    # TODO: Re-use existing jti?
    # TODO: Invalidate previous token?
    t = JWTAuthToken.new(namespace=NS_CODE_VERIFIED,
                         identity=username)
    return jsonify({'token': encode_token(t), })


@API.route('/set')
@require_jwt(namespaces=[NS_CODE_VERIFIED, ])
@utils.input_schema(ResetPasswordSchema)
def change_password():
    """ Set a new password. """
    data = utils.get_request_data(request)
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
