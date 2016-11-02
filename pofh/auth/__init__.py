# encoding: utf-8
""" Flask JWT token authorization.

Settings
--------
When ``init_app`` is called on an application, the following config values are
read from the application config dict:

``JWT_ISSUER`` (:py:class:`str`)
    Default 'iss' (issuer) claim value for auth tokens.

``JWT_ALGORITHM`` (:py:class:`str`)
    Override the default signing algorithm used for JWT tokens.

``JWT_AUTH_SCHEME`` (:py:class:`str`)
    Identitfy tokens in Authorization headers. The default is ``"JWT"``.

``JWT_EXPIRATION`` (:py:class:`int`, :py:class:`datetime.timedelta`)
    Default 'exp' claim, relative to 'iat' (issued at)

``JWT_NOT_BEFORE`` (:py:class:`int`, :py:class:`datetime.timedelta`)
    Default 'nbf' claim, relative to 'iat' (issued at).

``JWT_LEEWAY`` (:py:class:`int`, :py:class:`datetime.timedelta`)
    Leeway when checking the 'nbf' and 'exp' claims. If given as integer, we
    will assume seconds.

``JWT_SECRET_KEY`` (:py:class:`str`)
    Secret key for signing tokens, and checking token signatures. Defaults to
    the Flask ``SECRET_KEY`` value.

"""

import blinker
from datetime import timedelta
from flask import current_app, request, g
from functools import wraps
from jwt.exceptions import InvalidTokenError, DecodeError
from werkzeug.exceptions import Unauthorized, Forbidden
from .token import JWTAuthToken


signal_token_read = blinker.signal('auth.token.read')
""" Signals that a valid token has been accepted.

The sender is the token that was read from the request. Additional keywords:

value
    The encoded and signed input value
"""

signal_token_error = blinker.signal('auth.token.error')
""" Signals that an invalid token has been submitted.

The sender is the error that occured. Additional keywords:

raw
    The raw input token string (signed, encoded).
payload
    The token payload, if we were able to decode it.
decode_error
    DecodeError, if unable to extract a payload from the token.
"""

signal_token_sign = blinker.signal('auth.token.sign')
""" Signals that a token has been signed.

The sender is the token that was signed. Additional keywords:

value
    The signed, encoded value.
"""


DEFAULTS = {
    'JWT_ISSUER': None,
    'JWT_ALGORITHM': JWTAuthToken.JWT_ALGORITHM,
    'JWT_AUTH_SCHEME': 'JWT',
    'JWT_EXPIRATION': JWTAuthToken.DEFAULT_EXP,
    'JWT_NOT_BEFORE': JWTAuthToken.DEFAULT_NBF,
    'JWT_LEEWAY': timedelta(seconds=1),
}


class Challenge(Unauthorized):
    """ Unauthorized HTTP error with WWW-Authenticate data.

    >>> e = Unauthorized()
    >>> 'WWW-Authenticate' in e.get_response().headers
    False

    >>> e.realm = 'foo'
    >>> 'WWW-Authenticate' in e.get_response().headers
    True
    >>> 'Basic realm="foo"' in e.get_response().headers.get('WWW-Authenticate')
    True
    """

    def __init__(self, message, scheme=None, realm=None):
        self.realm = realm
        self.scheme = scheme
        super(Challenge, self).__init__(message)

    def get_response(self, *args, **kwargs):
        response = super(Challenge, self).get_response(*args, **kwargs)
        if self.scheme is not None:
            response.www_authenticate.type = self.scheme
        if self.realm is not None:
            response.www_authenticate.realm = self.realm
        return response


def get_secret(app):
    """ Get the JWT signing key for a given app.

    :param Flask app: A Flask application.
    :raise RuntimeError: If no secret can be fetched.
    :return str: Returns the secret.
    """
    try:
        s = app.config['JWT_SECRET_KEY']
        if not s:
            raise KeyError()
        return s
    except KeyError:
        raise RuntimeError(
            "No 'JWT_SECRET_KEY' or 'SECRET_KEY' set, "
            "unable to sign or verify JSON Web Tokens.")


def require_jwt(namespaces=None):
    """ Decorator that checks for valid JWT.

    This wrapper makes sure that a JWT with the proper subject has been
    presented in the request.

    :type namespaces: NoneType, list
    :param namespaces:
        A list of token namespaces allowed access to the wrapped resource.

    """
    def wrap(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if g.current_token is None:
                raise Challenge("Needs authentication",
                                current_app.config['JWT_AUTH_SCHEME'])
            if namespaces and g.current_token.namespace not in namespaces:
                raise Forbidden(
                    "Invalid token: Cannot be used for this resource.")

            # TODO: Check blacklist, etc?

            return func(*args, **kwargs)
        wrapper.__doc__ += (
            "\nThe request needs to include an ``Authorization`` header "
            " with a valid JSON Web Token\n")
        return wrapper
    return wrap


def encode_token(token):
    """ Sign and encode a token using the current app secret. """
    signed_token = token.jwt_encode(get_secret(current_app))
    signal_token_sign.send(token, value=signed_token)
    return signed_token


def _get_auth_data(req):
    """ Extract Authorization header from request.

    :return tuple:
        Returns a tuple, (scheme, creds)
    """
    def _pop(l):
        try:
            return l.pop(0) or None
        except IndexError:
            return None
    parts = req.headers.get('Authorization', "").split(" ", 1)
    return _pop(parts), _pop(parts)


def _check_for_jwt():
    """ Request handler.

    This callback should run on any request, to detect and validate JSON Web
    Tokens. If a valid JWT is presented, it is stored as
    `flask.g.current_token`.

    """
    g.current_token = None
    scheme, data = _get_auth_data(request)
    if not scheme:
        return
    if scheme != current_app.config['JWT_AUTH_SCHEME']:
        current_app.logger.debug("Non-JWT auth header ({!s})".format(scheme))
        return

    try:
        g.current_token = JWTAuthToken.jwt_decode(
            data,
            get_secret(current_app),
            leeway=current_app.config['JWT_LEEWAY'])
        current_app.logger.info(
            "Valid JWT ({!r}))".format(g.current_token))
        signal_token_read.send(g.current_token, value=data)
    except InvalidTokenError as e:
        current_app.logger.info("Invalid JWT: {!s}".format(e))
        error_info = {'raw': data, 'payload': None, 'decode_error': None, }
        try:
            error_info['payload'] = JWTAuthToken.jwt_debug(data)
        except DecodeError as decode_error:
            error_info['decode_error'] = decode_error
        current_app.logger.debut(
            "JWT payload={payload!r}, {decode_error!s}".format(**error_info))
        signal_token_error.send(e, **error_info)
        raise Forbidden("Invalid token: {!s})".format(e))


def init_app(app):
    """ Set up authorization. """
    for k, v in DEFAULTS.items():
        app.config.setdefault(k, v)
    app.config.setdefault('JWT_SECRET_KEY', app.config['SECRET_KEY'])

    def _seconds(app, key):
        if isinstance(app.config[key], timedelta):
            return app.config[key]
        else:
            return timedelta(seconds=app.config[key])

    if app.config['JWT_EXPIRATION'] != DEFAULTS['JWT_EXPIRATION']:
        JWTAuthToken.DEFAULT_EXP = _seconds(app, 'JWT_EXPIRATION')

    if app.config['JWT_NOT_BEFORE'] != DEFAULTS['JWT_NOT_BEFORE']:
        JWTAuthToken.DEFAULT_NBF = _seconds(app, 'JWT_NOT_BEFORE')

    if app.config['JWT_ALGORITHM'] != DEFAULTS['JWT_ALGORITHM']:
        JWTAuthToken.JWT_ALGORITHM = app.config['JWT_ALGORITHM']

    app.before_request(_check_for_jwt)
