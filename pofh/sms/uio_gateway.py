# encoding: utf-8
""" SMS dispatcher for the UiO gateway.

Configuration
-------------

SMS_GATEWAY_URL (str)
    The URL to the SMS endpoint (HTTP POST).

SMS_GATEWAY_SYSTEM (str)
    The system identificator of this system.

SMS_GATEWAY_USER (str)
    The gateway username.

SMS_GATEWAY_PASSWORD (str)
    The gateway password.

SMS_GATEWAY_TIMEOUT (float)
    Timeout, in seconds.

"""
from __future__ import absolute_import, unicode_literals

import requests
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


class UioGatewayDispatcher(dispatcher.SmsDispatcher):

    """ For lack of a better name. """

    def __init__(self, url, system, user, password, timeout):
        self._url = url
        self._system = system
        self._user = user
        self._pass = password
        self._timeout = timeout

    def _validate_response(self, response):
        """Check that the response from an SMS gateway says that the message
        was sent or not. The SMS gateway we use should respond with a line
        formatted as:

         <msg_id>¤<status>¤<phone_to>¤<timestamp>¤¤¤<message>

        An example:

         UT_19611¤SENDES¤87654321¤20120322-15:36:35¤¤¤Welcome to UiO. Your

        ...followed by the rest of the lines with the message that was sent.

        :param requests.Response response:
            The HTTP response.
        :raise dispatcher.SmsResponseError:
            If the response indicates that the SMS is not sent
        """
        # We're only interested in the first line:
        lines = response.split("\n")
        try:
            # msg_id, status, to, timestamp, message
            msg_id, status, to, _, _ = lines[0].split('\xa4', 4)
        except ValueError:
            raise dispatcher.SmsResponseError(
                "Bad response from server: {!s}".format(lines[0]))

        if status != 'SENDES':
            raise dispatcher.SmsResponseError(
                "Bad status from server: {!s} ({!s})".format(
                    status, lines[0]))

    def _send(self, number, message):
        """ Send an SMS message. """

        postdata = {
            'b': self._user,
            'p': self._pass,
            's': self._system,
            't': number,
            'm': message
        }

        response = requests.post(self._url,
                                 data=postdata,
                                 timeout=self._timeout)
        # Raise error if error status
        response.raise_for_status()
        self._check_response(response)
