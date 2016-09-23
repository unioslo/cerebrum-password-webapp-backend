# encoding: utf-8
""" SMS Gateway module.

Configuration
-------------

SMS_DISPATCHER (str)
    Chooses the SMS backend.
    Currently supported:
     - mock
     - uio-gateway

SMS_WHITELIST (list)
    A list of regular expressions. Phone numbers must match one of the
    expressions in the list, if it is to be sent.

"""
from __future__ import absolute_import, unicode_literals

from warnings import warn
from . import dispatcher


def _default_dispatch(*args, **kwargs):
    warn(RuntimeWarning, "No sms dispatcher configured (SMS_DISPATCHER)")
    dispatcher.MockSmsDispatcher()(*args, **kwargs)


_dispatcher = _default_dispatch


def send_sms(number, message):
    """ Send SMS to 'number' with 'message'

    This will send an SMS message using whatever backend that is configured
    with the app settings.
    """
    return _dispatcher(number, message)


def get_sms_dispatcher(config):
    """ Fetch sms dispatcher from config. """
    # TODO: Implement better module loading.

    # mock sms dispatcher
    if config['SMS_DISPATCHER'] == 'mock':
        return dispatcher.MockSmsDispatcher()

    # uio_gateway sms dispatcher
    if config['SMS_DISPATCHER'] == 'uio-gateway':
        from . import uio_gateway
        return uio_gateway.from_config(config)

    raise ValueError(
        "Invalid SMS_DISPATCHER '{!s}'".format(config['SMS_DISPATCHER']))


def init_app(app):
    """ Use app configuration to set up session backend. """
    global _dispatcher
    if app.config.get('SMS_DISPATCHER'):
        _dispatcher = get_sms_dispatcher(app.config)

    # Configure whitelist
    whitelist = app.config.get('SMS_WHITELIST')
    if not whitelist:
        whitelist = ['^.*$', ]
    elif not isinstance(whitelist, list):
        whitelist = [whitelist, ]
    for r in whitelist:
        _dispatcher.add_whitelist(r)
