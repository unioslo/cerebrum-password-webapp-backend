# encoding: utf-8
"""
This module contains the package version number, and factory methods for
bootstrapping the pofh application.

"""
from __future__ import print_function, unicode_literals, absolute_import

import os
from flask import app as flask_app_module
from flask_cors import CORS
import logging
import logging.config

from . import api
from . import auth
from . import sms
from . import idm
from . import recaptcha
from . import language
from . import template
from . import redis
from . import stats

__VERSION__ = '0.1.0'


CONFIG_ENVIRON_NAME = 'POFH_CONFIG'
""" Name of an environmet variable to read config file name from.

This is a useful method to set a config file if the application is started
through a third party application server like *gunicorn*.
"""

APP_CONFIG_FILE_NAME = 'pofh.cfg'
""" Config filename in the Flask application instance path. """

LOG_CONFIG_FILE_NAME = 'logging.ini'
""" Logging config filename in the Flask application instance path. """


class DefaultConfig(object):
    """ Default configuration. """
    pass


DEFAULT_LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'stderr': {
            'class': 'logging.StreamHandler',
            'level': 'NOTSET',
            'formatter': 'default',
        },
    },
    'loggers': {
        'pofh': {
            'handlers': ['stderr'],
            'level': 'NOTSET',
            'propagate': False,
        },
    }
}


class Flask(flask_app_module.Flask):

    # Removes the flask create_logger logic
    @property
    def logger(self):
        # Already set up?
        if self._logger and self._logger.name == self.logger_name:
            return self._logger
        # No, lets create a logger
        with flask_app_module._logger_lock:
            if self._logger and self._logger.name == self.logger_name:
                return self._logger
            self._logger = rv = logging.getLogger(self.logger_name)
            return rv


def init_config(app, config):
    """ Initialize app config.

    Loads app config from the first available source:

    1. ``config`` argument, if not ``None``
    2. ``app.instance_path``/``APP_CONFIG_FILE_NAME``, if it exists

    """
    # Load default config
    app.config.from_object(DefaultConfig)

    # Read config
    if config and os.path.splitext(config)[1] in ('.py', '.cfg'):
        # <config>.py, <config>.cfg
        if app.config.from_pyfile(config, silent=False):
            print("Config: Loading config from argument ({!s})".format(config))
    elif config and os.path.splitext(config)[1] == '.json':
        # <config>.json
        with open(config, 'r') as config_file:
            if app.config.from_json(config_file.read(), silent=False):
                print("Config: Loading config from argument ({!s})".format(
                    config))
    elif config:
        # <config>.<foo>
        raise RuntimeError(
            "Unknown config file format '{!s}' ({!s})".format(
                os.path.splitext(config)[1], config))
    else:
        if app.config.from_envvar(CONFIG_ENVIRON_NAME, silent=True):
            print("Config: Loading config from ${!s} ({!s})".format(
                CONFIG_ENVIRON_NAME, os.environ[CONFIG_ENVIRON_NAME]))
        if app.config.from_pyfile(APP_CONFIG_FILE_NAME, silent=True):
            print("Config: Loading config from intance path ({!s})".format(
                os.path.join(app.instance_path, APP_CONFIG_FILE_NAME)))


def init_logging(app):
    """ Init logging.

    Loads log config from the first available source:

    1. ``app.config["LOG_CONFIG"]`` setting, if set
    2. ``app.instance_path``/``LOG_CONFIG_FILE_NAME``, if it exists
    3. ``DEFAULT_LOG_CONFIG``

    """
    log_config = app.config.get('LOG_CONFIG')

    def _load_config_file(filename):
        logging.config.fileConfig(filename,
                                  defaults=None,
                                  disable_existing_loggers=False)

    if log_config is None:
        # No log file setting in config
        log_config = os.path.join(app.instance_path, LOG_CONFIG_FILE_NAME)
        if os.path.isfile(log_config):
            print("Logging: Loading config from instance path ({!s})".format(
                log_config))
            _load_config_file(log_config)
        else:
            print("Logging: Using default log settings")
            logging.config.dictConfig(DEFAULT_LOG_CONFIG)
    else:
        if not os.path.isabs(log_config):
            log_config = os.path.join(app.instance_path, log_config)
        # Log file given in config
        if os.path.isfile(log_config):
            print("Logging: Loading config from LOG_CONFIG='{!s}'".format(
                log_config))
            _load_config_file(log_config)
        else:
            raise RuntimeError(
                "LOG_CONFIG '{!s}' doesn't exist".format(log_config))

    # Set default logger level based on app debug setting
    if app.logger.level == logging.NOTSET:
        level = logging.DEBUG if app.debug else logging.INFO
        print(
            "Logging: Setting level to {!s}".format(
                logging.getLevelName(level)))
        app.logger.setLevel(level)
    else:
        print(
            "Logging: Level {!s}".format(
                logging.getLevelName(app.logger.getEffectiveLevel())))


class WsgiApp(object):
    """ Wsgi app proxy object. """

    # TODO: Is this really needed?

    @staticmethod
    def create(config=None, flask_class=Flask):
        """ Create application.

        :rtype: Flask
        :return: The assembled and configured Flask application.
        """
        # setup flask app
        app = flask_class(
            __name__,
            static_folder=None,
            instance_relative_config=True)

        init_config(app, config)
        init_logging(app)

        # setup CORS support
        cors = CORS()
        cors.init_app(app)

        # setup storage
        redis.init_app(app)

        # setup api
        stats.init_app(app)
        recaptcha.init_app(app)
        auth.init_app(app)
        sms.init_app(app)
        idm.init_app(app)
        language.init_app(app)
        template.init_app(app)
        api.init_app(app)

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
