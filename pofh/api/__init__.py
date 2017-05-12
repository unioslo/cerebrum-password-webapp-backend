# encoding: utf-8
""" The password app API. """
from __future__ import unicode_literals, absolute_import

from flask import g, jsonify, request
import werkzeug.exceptions as _exc
from blinker import signal
from .. import auth

from . import usernames
from . import authenticate
from . import password
from . import sms


api_error = signal('api.error')


def handle_error(error):
    """ Handle errors.

    This handler attempts to jsonify uncaught exceptions.
    """
    api_error.send(type(error), exc=error)

    if isinstance(error, _exc.HTTPException):
        r = error.get_response()
        response = jsonify(
            message=error.description,
            error=error.name)
        response.www_authenticate.realm = r.www_authenticate.realm
        response.www_authenticate.type = r.www_authenticate.type
    else:
        response = jsonify(
            message=str(error),
            error=str("unknown")
        )

    response.status_code = getattr(error, 'code', 500)
    return response


def log_request():
    jti = ''
    if g.current_token is not None:
        jti = g.current_token.jti

    g.log.info("request", method=request.method, url=str(request.url_rule),
               jti=jti, remote_addr=request.remote_addr)


def init_app(app):
    """ Bootstrap the API. """
    # functionality
    usernames.init_api(app)
    password.init_api(app)

    # auth methods
    authenticate.init_api(app)
    sms.init_api(app)

    app.before_request(log_request)

    # Workaround for https://github.com/pallets/flask/issues/941
    if not app.config.get('DEBUG', False):
        for code in _exc.default_exceptions:
            app.errorhandler(code)(handle_error)

    @app.route('/renew', methods=['POST', ])
    @auth.require_jwt()
    def renew_session_jwt():
        """ Renew the current JSON Web Token.

        Request
            Request body should be empty. Request headers should include a
            valid JWT.

        Response
            Response includes a JSON document with the updated JWT:
            ``{"token": "..."}``

        """
        g.current_token.renew()
        g.log.info("token-renewed", jti=g.current_token.jti)
        return jsonify({'token': auth.encode_token(g.current_token), })
