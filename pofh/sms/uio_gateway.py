# encoding: utf-8
""" SMS dispatcher for the UiO gateway.

``SMS_GATEWAY_URL`` (:py:class:`str`)
    The URL to the SMS endpoint (HTTP POST).

``SMS_GATEWAY_SYSTEM`` (:py:class:`str`)
    The system identificator of this system.

``SMS_GATEWAY_USER`` (:py:class:`str`)
    The gateway username.

``SMS_GATEWAY_PASSWORD`` (:py:class:`str`)
    The gateway password.

``SMS_GATEWAY_TIMEOUT`` (:py:class:`float`)
    Timeout, in seconds.

"""
from __future__ import absolute_import, unicode_literals

import requests
import phonenumbers
from flask import current_app
from . import dispatcher


def from_config(config):
    """ Initialize settings from a dict-like config. """
    return UioGatewayDispatcher(
        config['SMS_GATEWAY_URL'],
        config['SMS_GATEWAY_SYSTEM'],
        config['SMS_GATEWAY_USER'],
        config['SMS_GATEWAY_PASSWORD'],
        config.get('SMS_GATEWAY_TIMEOUT', 10.0)
    )


def format_e164(number):
    """ Format phone number.

    :param phonenumbers.PhoneNumber number:

    :return str: ITU-T E.164 formatted phone number.
    """
    return phonenumbers.format_number(
        number,
        phonenumbers.PhoneNumberFormat.E164)


def validate_response(response):
    """ Check the response from the gateway.

    The SMS gateway we use should respond with a line formatted as:

      <msg_id>¤<status>¤<phone_to>¤<timestamp>¤¤¤<multi-line-message>

    An example:

      UT_19611¤SENDES¤87654321¤20120322-15:36:35¤¤¤Welcome to UiO.\\n...

    :param requests.Response response:
        The HTTP response.

    :raise dispatcher.SmsResponseError:
        If the response indicates that the SMS is not sent
    """
    # All the metadata are in the first line:
    metadata = response.text.split("\n")[0]
    try:
        # msg_id, status, to, timestamp, message
        msg_id, status, to, _, _ = metadata.split('¤', 4)
    except ValueError:
        raise dispatcher.SmsResponseError(
            "Bad response from server: {!s}".format(metadata))

    if status != 'SENDES':
        raise dispatcher.SmsResponseError(
            "Bad status from server: {!s} ({!s})".format(
                status, metadata))


class UioGatewayDispatcher(dispatcher.SmsDispatcher):
    """ For lack of a better name. """

    def __init__(self, url, system, user, password, timeout):
        super(UioGatewayDispatcher, self).__init__()
        self._url = url
        self._system = system
        self._user = user
        self._pass = password
        self._timeout = timeout

    def _send(self, number, message):
        """ Send an SMS message.

        :param phonenumbers.PhoneNumber number:
            The phone number to send to.
        :param str message:
            The message string.
        """
        postdata = {
            'b': self._user,
            'p': self._pass,
            's': self._system,
            't': format_e164(number),
            'm': message
        }

        response = requests.post(self._url,
                                 data=postdata,
                                 timeout=self._timeout)
        # Raise error if error status
        response.raise_for_status()
        validate_response(response)

    @dispatcher.SmsDispatcher.signal_sms_pre.connect
    def _print_sms_pre(sender, **args):
        current_app.logger.debug(
            "SMS: Sending message to '{raw_number!s}'".format(**args))

    @dispatcher.SmsDispatcher.signal_sms_filtered.connect
    def _print_sms_filtered(sender, **args):
        current_app.logger.info(
            "SMS: Invalid or non-whitelisted number '{raw_number!s}'".format(
                **args))

    @dispatcher.SmsDispatcher.signal_sms_sent.connect
    def _print_sms_error(sender, **args):
        current_app.logger.error(
            "SMS: Sending to '{raw_number!s}' failed: {error!s}".format(
                **args))

    @dispatcher.SmsDispatcher.signal_sms_sent.connect
    def _print_sms_sent(sender, **args):
        current_app.logger.debug(
            "SMS: Sent message to '{raw_number!s}'".format(**args))
