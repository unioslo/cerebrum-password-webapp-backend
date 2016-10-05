# encoding: utf-8
"""
This module contains the package version number, and factory methods for
bootstrapping the module.
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
""" Name of an environmet variable to read config file name from.

This is a useful method to set a config file if the application is started
through a third party application server like *guincorn*.
"""

CONFIG_FILE_NAME = 'pofh.cfg'
""" Name of the config file name in the Flask application instance path. """


class DefaultConfig(object):
    """ Default configuration. """

    # TODO: Is this needed?
    pass


class WsgiApp(object):
    """ Wsgi app proxy object. """

    # TODO: Is this really needed?

    @staticmethod
    def create(config=None):
        """ Create application.

        :rtype: Flask
        :return: The assembled and configured Flask application.
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
""" WSGI app. """
