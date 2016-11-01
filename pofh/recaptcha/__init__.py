# encoding: utf-8
""" This sub-package includes functionality for verifying a Google reCAPTCHA
response included in forms.

Settings
--------
The following settings are used from the Flask configuration:

``RECAPTCHA_ENABLE`` (:py:class:`bool`)
    Set to True to enable Google ReCAPTCHA.

``RECAPTCHA_SITE_KEY`` (:py:class:`str`)
    The site key for ReCAPTCHA.

``RECAPTCHA_SECRET_KEY`` (:py:class:`str`)
    The secret key for ReCAPTCHA.

``RECAPTCHA_VERIFY_URL`` (:py:class:`str`)
    The URL used to verify a ReCAPTCHA field.

"""
from __future__ import unicode_literals

from werkzeug.local import LocalProxy
from werkzeug.exceptions import BadRequest
from flask import request, current_app
from flask import Blueprint, url_for, render_template
from functools import wraps
import requests
import blinker
from warnings import warn


DEFAULT_FIELD_NAME = 'g-recaptcha-response'

DEFAULT_CONFIG = {
    'RECAPTCHA_ENABLE': False,
    'RECAPTCHA_SITE_KEY': '',
    'RECAPTCHA_SECRET_KEY': None,
    'RECAPTCHA_VERIFY_URL': 'https://www.google.com/recaptcha/api/siteverify',
}


class RecaptchaClient(object):
    """ Google ReCAPTCHA validator.

    Usage:

    ::

        secret_key = "6Le..."
        verify_url = "https://www.google.com/recaptcha/api/siteverify"
        response = "03AHJ..."
        remoteip = "127.0.0.1"
        validator = RecaptchaClient(secret_key, verify_url)
        validator(response, remoteip)
    """

    signal_start = blinker.signal('pofh.recaptcha.start')
    signal_done = blinker.signal('pofh.recaptcha.done')
    signal_error = blinker.signal('pofh.recaptcha.error')

    def __init__(self, secret_key, verify_url):
        self.secret_key = secret_key
        self.verify_url = verify_url

    def _check(self, data):
        r = requests.post(self.verify_url, data=data)
        r.raise_for_status()
        return r.json()["success"] is True

    def __call__(self, value, remoteip):
        """ Check a reCAPTHCA response.

        :param str value: The response to check
        :param str remoteip: An optional remoteip to include in the check

        :rtype: bool
        :return:
            Returns `True` if the response passed validation, `False` otherwise
        """
        self.signal_start.send(
            self, value=value, remoteip=remoteip)

        data = {
            "secret": self.secret_key,
            "response": value,
            "remoteip": remoteip,
        }
        try:
            status = self._check(data)
            self.signal_done.send(
                self, value=value, remoteip=remoteip, status=status)
            return status
        except Exception as e:
            self.signal_error.send(
                self, value=value, remoteip=remoteip, error=e)
            raise


class Recaptcha(object):
    """ Simple application wrapper for registering the Recaptcha class.

    Usage:

    ::

        app = Flask('foo')
        middleware = Recaptcha(app)
        # or
        middleware = Recaptcha()
        middleware.init_app(app)
    """

    recaptcha_ext_name = 'pofh.recaptcha'

    def __init__(self, app=None):
        self.__app = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """ Initialize app from app config. """
        for k, v in DEFAULT_CONFIG.items():
            app.config.setdefault(k, v)

        self.__app = app

        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions[self.recaptcha_ext_name] = self

    def __conf(self, name, default=None):
        value = default
        if self.__app is not None:
            value = self.__app.config.get(name, default)
        if value is None:
            raise AttributeError("No '{!s}' set".format(name))
        return value

    @property
    def enabled(self):
        """ If recaptcha is enabled in this middleware app. """
        return bool(self.__conf('RECAPTCHA_ENABLE', False))

    @property
    def site_key(self):
        """ The site key from the app configuration. """
        return self.__conf('RECAPTCHA_SITE_KEY', '')

    @property
    def secret_key(self):
        """ The secret key from the app configuration. """
        return self.__conf('RECAPTCHA_SECRET_KEY')

    @property
    def verify_url(self):
        """ The URL used to verify recaptcha responses. """
        return self.__conf('RECAPTCHA_VERIFY_URL')

    @property
    def client(self):
        """ The recaptcha client (RecaptchaClient). """
        try:
            return RecaptchaClient(self.secret_key, self.verify_url)
        except AttributeError as e:
            raise AttributeError(
                "RecaptchaClient not configured: {!s}".format(e))

    @classmethod
    def get_middleware(cls, app):
        """ Get the Recaptcha middleware app from a flask app object.

        :param flask.Flask app: The application.

        :return Recaptcha: The Recaptcha middleware app.

        :raises RuntimeError: If the recaptcha middleware has not been set up.
        """
        try:
            return app.extensions[cls.recaptcha_ext_name]
        except (AttributeError, KeyError):
            raise RuntimeError("Recaptcha not initialized")


recaptcha = LocalProxy(lambda: Recaptcha.get_middleware(current_app))
""" ``LocalProxy`` for ``Recaptcha.get_middleware(current_app).`` """


def require_recaptcha(field=DEFAULT_FIELD_NAME):
    """ Require a recaptcha field in requests.

    :param str field: Which field to look for a recaptcha response in.
    """
    def wrap(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if recaptcha.enabled:
                current_app.logger.debug(
                    "recaptcha: checking field '{!s}'".format(field))
                if request.is_json:
                    data = request.json()
                else:
                    data = request.form

                if recaptcha.client(
                        data.get(field),
                        request.environ.get('REMOTE_ADDR')):
                    current_app.logger.info("recaptcha: valid")
                else:
                    current_app.logger.info(
                        "recaptcha: invalid ({!s})".format(data.get(field)))
                    raise BadRequest("invalid recaptcha response")
            else:
                current_app.logger.debug("recaptcha: disabled")
            return func(*args, **kwargs)
        return wrapper
    return wrap


TEST_API = Blueprint('recaptcha', __name__,
                     url_prefix='/recaptcha',
                     template_folder='.')


@TEST_API.route('/', methods=['GET', ])
def render_page():
    """ Render a ReCAPTCHA test page. """
    return render_template(
        'recaptcha-test.tpl',
        recaptcha=recaptcha,
        action=url_for('.verify_response'),
        field=DEFAULT_FIELD_NAME)


@TEST_API.route('/verify', methods=['POST', ])
@require_recaptcha(field=DEFAULT_FIELD_NAME)
def verify_response():
    """ Validate a ReCAPTCHA response. """
    if not recaptcha.enabled:
        return ('Recaptcha disabled', 501)
    else:
        return ('', 204)


def init_app(app):
    """ Configure reCAPTCHA. """
    middleware = Recaptcha(app)

    if app.debug:
        app.register_blueprint(TEST_API)

    if not middleware.enabled:
        warn(RuntimeWarning("Recaptcha disabled"))
    else:
        middleware.client
