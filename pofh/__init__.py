# encoding: utf-8
""" pofh application

Configuration
-------------
Config is loaded from:

1. Default configuration.
2. ``pofh.cfg`` in the instance folder
   (http://flask.pocoo.org/docs/0.11/config/#instance-folders).
3. File specified in the ``POFH_CONFIG`` environment variable.


Run
---
To run the server using gunicorn: ::

    $ gunicorn pofh:wsgi


To run the server using flask: ::

    $ python -m pofh
    $ # OR
    $ pofhd

"""
from __future__ import print_function, unicode_literals

import os
from flask import Flask
from flask_cors import CORS
from . import api
from . import auth
from . import recaptcha


__VERSION__ = '0.1.0'


CONFIG_ENVIRON_NAME = 'POFH_CONFIG'
CONFIG_FILE_NAME = 'pofh.cfg'


class DefaultConfig(object):
    """ Default config. """
    # TODO
    pass


class WsgiApp(object):
    """ Wsgi app proxy.

    Delays app init until called.
    """
    @staticmethod
    def create(config=None):
        """ Create application.

        :return Flask: The assembled and configured Flask application.
        """
        # set up flask app args
        kwargs = {
            'instance_relative_config': True,
        }

        # setup flask app
        app = Flask(__name__, **kwargs)
        app.config.from_object(DefaultConfig())

        # Read config
        if config:
            if app.config.from_pyfile(config, silent=True):
                print("Loaded config from argument ({!s})".format(config))
        else:
            if app.config.from_envvar(CONFIG_ENVIRON_NAME, silent=True):
                print("Loaded config from ${!s} ({!s})".format(
                    CONFIG_ENVIRON_NAME, os.environ[CONFIG_ENVIRON_NAME]))
            if app.config.from_pyfile(CONFIG_FILE_NAME, silent=True):
                print("Loaded config from intance folder ({!s})".format(
                    os.path.join(app.instance_path, CONFIG_FILE_NAME)))

        # setup CORS support
        cors = CORS()
        cors.init_app(app)
        recaptcha.init_app(app)

        # setup api
        api.init_app(app)
        auth.init_app(app)

        return app

    @property
    def app(self):
        """ Lazily create the application. """
        if not hasattr(self, '_app'):
            self._app = self.create()
        return self._app

    def __call__(self, *args, **kwargs):
        """ Run the application on a request. """
        return self.app(*args, **kwargs)


wsgi = WsgiApp()
