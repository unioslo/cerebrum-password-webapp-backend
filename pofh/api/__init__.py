# encoding: utf-8
""" Assembled API. """
from __future__ import unicode_literals

from flask import g, jsonify
from .. import auth

from . import usernames
from . import password
from . import sms


def init_app(app):
    app.register_blueprint(usernames.API)
    app.register_blueprint(password.API)
    app.register_blueprint(sms.API)

    @app.route('/refresh', methods=['POST', ])
    @auth.require_jwt()
    def renew_session_jwt():
        """ Renew the current session token. """
        g.current_token.renew()
        return jsonify({'token': auth.encode_token(g.current_token), })
