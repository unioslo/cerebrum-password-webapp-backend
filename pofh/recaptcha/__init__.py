# encoding: utf-8
""" This sub-package includes functionality for verifying a Google reCAPTCHA
response included in forms.

Settings
--------
The following settings are used from the Flask configuration:

``USE_RECAPTCHA`` (:py:class:`bool`)
    Set to True to enable Google ReCAPTCHA.

``RECAPTCHA_SITE_KEY`` (:py:class:`str`)
    The site key for ReCAPTCHA.

``RECAPTCHA_SECRET_KEY`` (:py:class:`str`)
    The secret key for ReCAPTCHA.

``RECAPTCHA_VERIFY_URL`` (:py:class:`str`)
    The URL used to verify a CAPTCHA field.

"""
from __future__ import unicode_literals

from flask import request, abort, jsonify
from functools import wraps
import requests
import blinker


DEFAULTS = {
    'USE_RECAPTCHA': False,
    'RECAPTCHA_SITE_KEY': '',
    'RECAPTCHA_SECRET_KEY': '',
    'RECAPTCHA_VERIFY_URL': 'https://www.google.com/recaptcha/api/siteverify',
}


def from_config(config):
    for setting in ('RECAPTCHA_SITE_KEY',
                    'RECAPTCHA_SECRET_KEY',
                    'RECAPTCHA_VERIFY_URL'):
        if not config.get(setting, None):
            raise RuntimeError(
                "Missing setting '{!s}'".format(setting))
    return ReCaptcha(
        config['RECAPTCHA_SITE_KEY'],
        config['RECAPTCHA_SECRET_KEY'],
        config['RECAPTCHA_VERIFY_URL']
    )


class ReCaptcha(object):
    """ Google reCAPTCHA validator. """

    signal_start = blinker.Signal('recaptcha.start')
    signal_done = blinker.Signal('recaptcha.done')
    signal_error = blinker.Signal('recaptcha.error')

    def __init__(self, site_key, secret_key, verify_url):
        self.site_key = site_key
        self.secret_key = secret_key
        self.verify_url = verify_url

    @property
    def enabled(self):
        """ If recaptcha is enabled or not. """
        # TODO: The class doesn't even look at this?
        try:
            return self._enabled
        except AttributeError:
            return False

    @enabled.setter
    def enabled(self, value):
        self._enabled = bool(value)

    def _check(self, data):
        r = requests.post(self.verify_url, data=data)
        r.raise_for_status()
        return r.json()["success"]

    def verify(self, value, remoteip):
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


_recaptcha = ReCaptcha(None, None, None)


def require_recaptcha(field="g-recaptcha-response"):
    """ Require a recaptcha field in requests.

    :param str field: Which field to look for a recaptcha response in.
    """
    def wrap(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if _recaptcha.enabled:
                if request.is_json:
                    data = request.json()
                else:
                    data = request.form
                if not _recaptcha.verify(
                    data.get(field),
                    request.environ.get('REMOTE_ADDR')
                ):
                    abort(400, jsonify({'msg': 'Invalid reCAPTCHA value', }))
            return func(*args, **kwargs)
        return wrapper
    return wrap


def init_app(app):
    """ Configure reCAPTCHA. """
    global _recaptcha
    for k, v in DEFAULTS.items():
        app.config.setdefault(k, v)

    if app.config['USE_RECAPTCHA']:
        _recaptcha = from_config(app.config)
        _recaptcha.enabled = True
