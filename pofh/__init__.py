# encoding: utf-8
"""
This module contains the package version number, and factory methods for
bootstrapping the pofh application.

"""
from __future__ import print_function, unicode_literals, absolute_import

import os
from flask import app as flask_app_module
from flask import g
from flask_cors import CORS
from werkzeug.contrib.fixers import ProxyFix
import logging
import logging.config
import structlog
import uuid

from . import api
from . import auth
from . import sms
from . import idm
from . import recaptcha
from . import language
from . import template
from . import redisclient
from . import stats
from . import apierror

__VERSION__ = '0.1.0'


APP_CONFIG_ENVIRON_NAME = 'POFH_CONFIG'
""" Name of an environmet variable to read config file name from.

This is a useful method to set a config file if the application is started
through a third party application server like *gunicorn*.
"""

LOG_CONFIG_ENVIRON_NAME = 'POFH_LOG_CONFIG'
""" Name of an environment variable to read a log config file from.

It can also instruct the app to *not* configure logging, if set to a
non-existing file.
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
        if app.config.from_envvar(APP_CONFIG_ENVIRON_NAME, silent=True):
            print("Config: Loading config from ${!s} ({!s})".format(
                APP_CONFIG_ENVIRON_NAME, os.environ[APP_CONFIG_ENVIRON_NAME]))
        if app.config.from_pyfile(APP_CONFIG_FILE_NAME, silent=True):
            print("Config: Loading config from intance path ({!s})".format(
                os.path.join(app.instance_path, APP_CONFIG_FILE_NAME)))


def init_logging(app):
    """ Init logging.

    Loads log config from the first available source:

    1. LOG_CONFIG_ENVIRON_NAME environment var, if set
    2. ``app.config["LOG_CONFIG"]`` setting, if set
    3. ``app.instance_path``/``LOG_CONFIG_FILE_NAME``, if it exists
    4. ``DEFAULT_LOG_CONFIG``

    """
    log_config = app.config.get('LOG_CONFIG')

    def _load_config_file(filename):
        if os.path.isfile(filename):
            logging.config.fileConfig(filename,
                                      defaults=None,
                                      disable_existing_loggers=False)
            return True
        return False

    if LOG_CONFIG_ENVIRON_NAME in os.environ:
        # 1. From environment
        env_config = os.environ[LOG_CONFIG_ENVIRON_NAME]
        if _load_config_file(env_config):
            print("Logging: Loading config from ${!s} ({!s})".format(
                LOG_CONFIG_ENVIRON_NAME, env_config))
        else:
            print("Logging: Ignoring config from ${!s} ({!s})".format(
                LOG_CONFIG_ENVIRON_NAME, env_config))
    elif log_config:
        # 2. From config
        if not os.path.isabs(log_config):
            log_config = os.path.join(app.instance_path, log_config)
        print("Logging: Loading config from LOG_CONFIG='{!s}'".format(
            log_config))
        # Log file given in config
        if not _load_config_file(log_config):
            raise RuntimeError(
                "LOG_CONFIG '{!s}' doesn't exist".format(log_config))
    else:
        log_config = os.path.join(app.instance_path, LOG_CONFIG_FILE_NAME)
        if _load_config_file(log_config):
            # 3. From instance path
            print("Logging: Loading config from instance path ({!s})".format(
                log_config))
        else:
            # 4. Default
            print("Logging: Using default log settings")
            logging.config.dictConfig(DEFAULT_LOG_CONFIG)

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

    logger = structlog.get_logger()

    structlog.configure(
        processors=[
            structlog.processors.KeyValueRenderer(
                key_order=["event", "request_id"],
            ),
        ],
        context_class=structlog.threadlocal.wrap_dict(dict),
        logger_factory=structlog.stdlib.LoggerFactory()
    )

    @app.before_request
    def before_request():
        g.log = logger.new(request_id=str(uuid.uuid4()))


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

        if app.config.get('NUMBER_OF_PROXIES', None):
            app.wsgi_app = ProxyFix(app.wsgi_app,
                                    num_proxies=app.config.get(
                                        'NUMBER_OF_PROXIES'))

        init_logging(app)

        # setup CORS support
        cors = CORS()
        cors.init_app(app)

        # setup storage
        redisclient.init_app(app)

        # Handle custom API errors
        apierror.init_app(app)

        # setup modules
        stats.init_app(app)
        recaptcha.init_app(app)
        auth.init_app(app)
        sms.init_app(app)
        idm.init_app(app)
        language.init_app(app)
        template.init_app(app)

        api.init_app(app)

        # Add cache headers to all responses
        @app.after_request
        def set_cache_headers(response):
            response.headers['Pragma'] = 'no-cache'
            response.headers['Cache-Control'] = 'no-cache'
            return response

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
