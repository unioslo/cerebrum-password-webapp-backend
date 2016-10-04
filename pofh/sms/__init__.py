# encoding: utf-8
"""
This sub-package includes functionality for communicating with an SMS
Gateway.

Configuration
-------------
The following settings are used from the Flask configuration:

``SMS_DISPATCHER`` (:py:class:`str`, :py:class:`unicode`)
    Chooses the SMS backend.
    Currently supported:

     - mock
     - uio-gateway

    Note that each module accepts additional configuration options.

``SMS_DEFAULT_REGION`` (:py:class:`str`, :py:class:`unicode`)
    A default region to use when parsing phone numbers. Phone numbers without
    country code prefix will be assumed to belong to this region. If not set,
    all phone numbers must include a country code prefix.

``SMS_WHITELIST_REGIONS`` (:py:class:`list`)
    A list of regions that SMS-es can be sent to. If ``None``, all regions are
    allowed. If empty list, no regions are allowed.

``SMS_WHITELIST_NUMBERS`` (:py:class:`list`)
    A list of phone numbers that SMS-es can be sent to (useful in testing). If
    ``None``, all numbers are allowed. If empty list, no numbers are allowed.

"""
from __future__ import absolute_import, unicode_literals

from warnings import warn
from . import dispatcher


class DefaultSmsDispatcher(dispatcher.MockSmsDispatcher):
    """ A mock SMS dispatcher that issues a warning when called. """

    def _send(self, number, message):
        warn(RuntimeWarning, "No sms dispatcher configured (SMS_DISPATCHER)")
        return super(DefaultSmsDispatcher, self)._send(number, message)


_dispatcher = DefaultSmsDispatcher()
""" The currently configured dispatcher.

This value is changed by calling `init_app`.
"""


def send_sms(number, message):
    """ Send SMS to 'number' with 'message'

    This will send an SMS message using whatever backend that is configured
    with the app settings.
    """
    return _dispatcher(number, message)


def get_sms_dispatcher(config):
    """ Fetch sms dispatcher from config.

    :param dict config:
        Any dict-like object with configuration.

    :rtype: pofh.sms.dispatcher.SmsDispatcher
    :return: An SMS dispatcher class.

    """
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
    """ Use app configuration to set up SMS backend.

    :param flask.Flask app: The flask application
    """
    global _dispatcher
    if app.config.get('SMS_DISPATCHER'):
        _dispatcher = get_sms_dispatcher(app.config)

    # Default region/country code
    _dispatcher.default_region = app.config.get('SMS_DEFAULT_REGION', None)

    # Configure region whitelist
    regions = app.config.get('SMS_WHITELIST_REGIONS', None)
    if regions is not None:
        _dispatcher.whitelist_regions = True
        if not isinstance(regions, list):
            regions = [regions, ]
        for r in regions:
            _dispatcher.add_region(r)

    # Configure phone number whitelist
    numbers = app.config.get('SMS_WHITELIST_NUMBERS', None)
    if numbers is not None:
        _dispatcher.whitelist_numbers = True
        if not isinstance(numbers, list):
            numbers = [numbers, ]
        for r in numbers:
            _dispatcher.add_number(r)
