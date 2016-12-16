# encoding: utf-8
""" Flask SMS dispatcher.

Common settings
---------------
When ``init_app`` is called on an application, the following config values are
read from the application config dict:

``SMS_DISPATCHER`` (:py:class:`str`)
    Chooses the SMS backend.
    Currently supported:

     - mock
     - debug
     - uio-gateway

    Note that each module accepts additional configuration options.

``SMS_DEFAULT_REGION`` (:py:class:`str`)
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


def parse_number(number):
    """ This will parse a phone number using the currently configured
    dispatcher. """
    return _dispatcher.parse(number)


def filter_number(number):
    """ This will send a phone number through the filter using the currently
    configured dispatcher. """
    _dispatcher.filter(number)


def get_sms_dispatcher(app):
    """ Fetch sms dispatcher from config.

    :param dict config:
        Any dict-like object with configuration.

    :rtype: pofh.sms.dispatcher.SmsDispatcher
    :return: An SMS dispatcher class.

    """
    # mock sms dispatcher
    if app.config['SMS_DISPATCHER'] == 'mock':
        return dispatcher.MockSmsDispatcher()

    if app.config['SMS_DISPATCHER'] == 'debug':
        if not app.debug:
            raise RuntimeError("Cannot use the 'debug' dispatcher "
                               "without the DEBUG setting enabled")
        return dispatcher.DebugSmsDispatcher()

    # uio_gateway sms dispatcher
    if app.config['SMS_DISPATCHER'] == 'uio-gateway':
        from . import uio_gateway
        return uio_gateway.from_config(app.config)

    raise ValueError(
        "Invalid SMS_DISPATCHER '{!s}'".format(app.config['SMS_DISPATCHER']))


def init_app(app):
    """ Use app configuration to set up SMS backend.

    :param flask.Flask app: The flask application
    """
    app.config.setdefault('SMS_DEFAULT_REGION', None)
    app.config.setdefault('SMS_WHITELIST_REGIONS', None)
    app.config.setdefault('SMS_WHITELIST_NUMBERS', None)

    global _dispatcher
    if app.config.get('SMS_DISPATCHER'):
        _dispatcher = get_sms_dispatcher(app)

    # Default region/country code
    _dispatcher.default_region = app.config['SMS_DEFAULT_REGION']

    # Configure region whitelist
    regions = app.config['SMS_WHITELIST_REGIONS']
    if regions is not None:
        _dispatcher.whitelist_regions = True
        if not isinstance(regions, list):
            regions = [regions, ]
        for r in regions:
            _dispatcher.add_region(r)

    # Configure phone number whitelist
    numbers = app.config['SMS_WHITELIST_NUMBERS']
    if numbers is not None:
        _dispatcher.whitelist_numbers = True
        if not isinstance(numbers, list):
            numbers = [numbers, ]
        for r in numbers:
            _dispatcher.add_number(r)
