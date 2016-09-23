# encoding: utf-8
""" Abstract SMS dispatchers. """
from __future__ import absolute_import, unicode_literals

import re
import blinker

# TODO: Use libphonenumbers to filter and transform numbers
# import phonenumbers


class SmsError(RuntimeError):
    pass


class SmsResponseError(SmsError):
    pass


class SmsDispatcher(object):
    """ Abstract SMS Dispatcher. """

    signal_sms_pre = blinker.Signal('sms.pre')
    signal_sms_filtered = blinker.Signal('sms.filtered')
    signal_sms_error = blinker.Signal('sms.error')
    signal_sms_sent = blinker.Signal('sms.sent')

    def __init__(self):
        self.whitelist = list()

    def add_whitelist(self, regex):
        """ Add a number to the whitelist.

        :param str regex: A regex that whitelists phone numbers.
        """
        compiled = re.compile(regex)
        self.whitelist.append(compiled)

    def check_whitelist(self, number):
        """ Check if the mobile number, `number`, is whitelisted.

        :param str number: The mobile number to filter.
        :raise ValueError: If the number is un-sms-worthy.
        :return bool: True if the number is whitelisted.
        """
        for compiled_regex in self.whitelist:
            if compiled_regex.match(number):
                return True
        return False

    def _transform(self, number):
        """ Transform/wash phone number.

        This function can be used to format phone numbers for the SMS gateway.
        """
        return number.strip()

    def _filter(self, number):
        """ Filter phone number.

        This function can be used to make sure only valid phone numbers are
        sent to the gateway.

        :return bool: Returns True if the number should be filtered.
        """
        if not self.check_whitelist(number):
            return True
        # Filter others?
        return False

    def __call__(self, number, message, **kwargs):
        """ send SMS message.

        This method trigges a series of events:

         - sms.pre: when this method is called
         - sms.filtered: if this method refuses to send sms to the given number
         - sms.error: if unable to send message
         - sms.sent: if the message is sent

        :param str number: The phone number to send to.
        :param str message: The message to include.

        :return bool: True if the message was sent, False otherwise.
        """
        self.signal_sms_pre.send(
            self, number=number, message=message)

        number = self._transform(number)
        if self._filter(number):
            self.signal_sms_filtered.send(
                self, number=number, message=message)
            return False

        try:
            self._send(number, message, **kwargs)
        except Exception as e:
            # TODO: Stop catching all?
            # TODO: Or, log the error?
            self.signal_sms_error.send(
                self, number=number, message=message, error=e)
            return False
        self.signal_sms_sent.send(
            self, number=number, message=message)
        return True

    def _send(self, number, message):
        raise NotImplementedError("Abstract method")


class MockSmsDispatcher(SmsDispatcher):
    """ A mock SMS dispatcher that doesn't send SMS. """

    def _send(self, number, message):
        return
