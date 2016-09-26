# encoding: utf-8
""" Flask token authorization.

Settings
--------
JWT_ISSUER
    'iss' (issuer) claim value for auth tokens.

JWT_ALGORITHM
    override the default signing algorithm used in jwt tokens

JWT_AUTH_SCHEME
    Identitfy tokens in Authorization headers

JWT_EXPIRATION_SECONDS
    Default 'exp' claim, relative to 'iat' (issued at)

JWT_NOT_BEFORE_SECONDS
    Default 'nbf' claim, relative to 'iat' (issued at)

JWT_LEEWAY
    Leeway when checking the 'nbf' and 'exp' claims.

JWT_SECRET_KEY
    Secret key for signing tokens, and checking token signatures.


Example
-------

    app = Flask('foo')
    init_app(app)

    @app.route('/require')
    @require_jwt(namespaces=['foo', 'bar'])
    def test():
        return "Hello {!s}!\n".format(g.current_token.sub)

    @app.route('/auth/foo/<str:identity>')
    def auth_foo(identity):
        token = JWTAuthToken.new(namespace='foo', identity=identity)
        return jsonify(
            {'token': token.jwt_encode(app.config['JWT_SECRET_KEY'])})

"""

from datetime import timedelta
from flask import current_app, request, g
from functools import wraps
from jwt.exceptions import InvalidTokenError
from werkzeug.exceptions import Unauthorized, Forbidden
from .token import JWTAuthToken


DEFAULTS = {
    'JWT_ISSUER': None,
    'JWT_AUTH_SCHEME': 'JWT',
    'JWT_LEEWAY': timedelta(seconds=1),
    'JWT_ALGORITHM': JWTAuthToken.JWT_ALGORITHM,
    'JWT_EXPIRATION': JWTAuthToken.DEFAULT_EXP,
    'JWT_NOT_BEFORE': JWTAuthToken.DEFAULT_NBF,
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
    """
    def wrap(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if g.current_token is None:
                raise Challenge("Needs authentication",
                                current_app.config['JWT_AUTH_SCHEME'])
            if namespaces and g.current_token.namespace not in namespaces:
                raise Forbidden("No access")

            # TODO: Check blacklist, etc?
            return func(*args, **kwargs)
        return wrapper
    return wrap


def encode_token(token):
    """ Sign and encode a token using the current app secret. """
    return token.jwt_encode(get_secret(current_app))


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
        current_app.logger.info("Non-JWT auth header ({!s})".format(scheme))
        return

    try:
        g.current_token = JWTAuthToken.jwt_decode(
            data, get_secret(current_app),
            leeway=current_app.config['JWT_LEEWAY'])
        current_app.logger.info(
            "Valid JWT ({!r}))".format(g.current_token))
    except InvalidTokenError as e:
        try:
            token_data = JWTAuthToken.jwt_debug(data)
        except Exception as e:
            token_data = dict(error=str(e))
        current_app.logger.info(
            "Invalid JWT ({!s}, data={!r})".format(e, token_data))
        raise Forbidden("Invalid token: {!s}".format(e))


def init_app(app):
    """ Set up authorization. """
    for k, v in DEFAULTS.items():
        app.config.setdefault(k, v)
    app.config.setdefault('JWT_SECRET_KEY', app.config['SECRET_KEY'])

    def _seconds(app, key, default):
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
