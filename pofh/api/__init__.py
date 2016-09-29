# encoding: utf-8
""" Assembled API. """
from __future__ import unicode_literals, absolute_import

from flask import g, jsonify
import werkzeug.exceptions as _exc
from blinker import signal
from .. import auth

from . import usernames
from . import password
from . import sms


api_error = signal('api.error')


def handle_api_error(error):
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


def init_app(app):
    """ Bootstrap the API. """
    app.register_blueprint(usernames.API)
    app.register_blueprint(password.API)
    app.register_blueprint(sms.API)

    app.errorhandler(Exception)(handle_api_error)
    # Workaround for https://github.com/pallets/flask/issues/941
    for code in _exc.default_exceptions:
        app.errorhandler(code)(handle_api_error)

    @app.route('/refresh', methods=['POST', ])
    @auth.require_jwt()
    def renew_session_jwt():
        """ Renew the current session token. """
        g.current_token.renew()
        return jsonify({'token': auth.encode_token(g.current_token), })
