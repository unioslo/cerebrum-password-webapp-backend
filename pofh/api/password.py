# encoding: utf-8
""" Change password.

This module presents an API that lets users change their passord if they have a
JWT that allows them to do so.

"""
from __future__ import unicode_literals, absolute_import

import datetime
import blinker
from flask import g, Blueprint
from marshmallow import fields, Schema

from .. import auth
from ..auth.token import JWTAuthToken
from ..idm import get_idm_client
from .apierror import ApiError
from .utils import input_schema


API = Blueprint('password', __name__)

NS_SET_PASSWORD = 'allow-set-password'

PASSWORD_METRIC_TIME = "kpi.password.time_used"
PASSWORD_METRIC_INIT = "kpi.password.init"
PASSWORD_METRIC_DONE = "kpi.password.done"
PASSWORD_METRIC_DIFF = "kpi.password.diff"

signal_password_changed = blinker.signal('pofh.api.password.password-changed')


class ResetPasswordSchema(Schema):
    """ Set new password schema. """
    password = fields.String(required=True, allow_none=False)


class InvalidNewPassword(ApiError):
    code = 400
    error_type = 'weak-password'


def create_password_token(username):
    return JWTAuthToken.new(namespace=NS_SET_PASSWORD, identity=username)


@API.route('/password', methods=['POST'])
@auth.require_jwt(namespaces=[NS_SET_PASSWORD, ])
@input_schema(ResetPasswordSchema)
def change_password(data):
    """ Set a new password.

    Request
        Request headers should include a valid JWT.
        Request body should include one attribute, ``password``.

    Response
        Returns an empty 204 response if password gets changed.

    Errors
        400: schema-error
        400: weak-password
        401: missing or invalid jwt
        403: invalid jwt namespace

    """
    username = g.current_token.identity
    client = get_idm_client()

    # Check if new password is good enough
    if not client.check_new_password(username, data["password"]):
        # TODO: Include errors (broken rules) from idm?
        raise InvalidNewPassword()

    client.set_new_password(username, data["password"])
    signal_password_changed.send(None)

    # TODO: Invalidate token?
    #  - we should keep a blacklist with used tokens in our redis store

    return ('', 204)


@auth.signal_token_sign.connect
def _record_metric_init(token, **kwargs):
    """ Records usage metrics. """
    # Whenever a *new* token with namespace `NS_SET_PASSWORD` is signed, we
    # assume new "password-change session" has been started.
    if (token.namespace != NS_SET_PASSWORD or
            (g.current_token is not None and
             g.current_token.jti == token.jti)):
        # ignore unrelated tokens and token renewal
        return
    statsd.incr(PASSWORD_METRIC_INIT)
    statsd.incr(PASSWORD_METRIC_DIFF)


@signal_password_changed.connect
def _record_metric_done(*args, **kwargs):
    """ Records usage metrics. """
    try:
        time_used_ms = int((datetime.datetime.utcnow() -
                            g.current_token.iat).total_seconds() * 1000)
    except:
        return
    statsd.timing(PASSWORD_METRIC_TIME, time_used_ms)
    statsd.incr(PASSWORD_METRIC_DONE)
    statsd.decr(PASSWORD_METRIC_DIFF)


def init_api(app):
    """ Register API blueprint. """
    app.register_blueprint(API)
