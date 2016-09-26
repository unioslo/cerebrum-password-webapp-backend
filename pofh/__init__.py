# encoding: utf-8
""" TODO: docstring. """
from __future__ import unicode_literals

import os

__VERSION__ = '0.1.0'


class DefaultConfig(object):
    """ Default config. """

    FOO = 1
    BAR = 2
    SESSION_INTERFACE = 'test'


def create_app(instance_path=None):
    """ Create application.

    :param str instance_path:
        Full path to a directory with app files (config, etc...).

    """
    from flask import Flask
    from flask_cors import CORS
    from . import api
    from . import auth

    # set up flask app args
    flask_kwargs = {
        'instance_relative_config': True,
    }
    if instance_path:
        flask_kwargs['instance_path'] = os.path.abspath(
            os.path.expanduser(instance_path))

    # setup flask app
    app = Flask(__name__, **flask_kwargs)
    app.config.from_object(DefaultConfig())
    app.config.from_pyfile('pofh.cfg', silent=True)

    # setup CORS support
    cors = CORS()
    cors.init_app(app)

    # setup api
    api.init_app(app)
    auth.init_app(app)

    return app
