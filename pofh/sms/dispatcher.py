# encoding: utf-8
""" Abstract SMS dispatcher implementations.  """
from __future__ import absolute_import, unicode_literals

import blinker
import phonenumbers


class SmsDispatcher(object):
    """ Abstract SMS Dispatcher. """

    signal_sms_pre = blinker.Signal('sms.pre')
    signal_sms_filtered = blinker.Signal('sms.filtered')
    signal_sms_error = blinker.Signal('sms.error')
    signal_sms_sent = blinker.Signal('sms.sent')

    def __init__(self):
        self._country_code_whitelist = list()
        self._number_whitelist = list()

    @property
    def default_region(self):
        """ default region for numbers without country code. """
        try:
            return self._default_region
        except AttributeError:
            return None

    @default_region.setter
    def default_region(self, region):
        if (region is not None and
                region not in phonenumbers.SUPPORTED_REGIONS):
            raise ValueError("Invalid region '{!s}'".format(region))
        self._default_region = region

    @property
    def whitelist_regions(self):
        """ True if region whitelist is in use. """
        return getattr(self, '_do_whitelist_regions', False)

    @whitelist_regions.setter
    def whitelist_regions(self, value):
        setattr(self, '_do_whitelist_regions', bool(value))

    def add_region(self, region):
        """ Add a region to the whitelist.

        :param str region: A region to add to the whitelist.
        """
        self._country_code_whitelist.append(
            phonenumbers.country_code_for_valid_region(region))

    def check_region(self, number):
        """ Check if region of a given number is valid. """
        return (not self.whitelist_regions or
                number.country_code in self._country_code_whitelist)

    @property
    def whitelist_numbers(self):
        """ True if numbers whitelist is in use. """
        return getattr(self, '_do_whitelist_numbers', False)

    @whitelist_numbers.setter
    def whitelist_numbers(self, value):
        setattr(self, '_do_whitelist_numbers', bool(value))

    def add_number(self, raw_number):
        """ Add a phone number to the whitelist.

        :param raw_number: A phone number to whitelist.
        """
        self._number_whitelist.append(self._transform(raw_number))

    def check_number(self, number):
        """ Check if a given number is valid. """
        return (not self.whitelist_numbers or
                number in self._number_whitelist)

    def _transform(self, raw_number):
        """ Parse and transform a raw phone number.

        :param raw_number: The phone number to transform.

        :return phonenumbers.PhoneNumber: The parsed phone number.
        """
        return phonenumbers.parse(raw_number, region=self.default_region)

    def _filter(self, number):
        """ Filter phone number.

        This function can be used to make sure only valid phone numbers are
        sent to the gateway.

        :param phonenumbers.PhoneNumber number:
            The phone number to filter.

        :return bool:
            Returns True if the number should be filtered.
        """
        if not phonenumbers.is_valid_number(number):
            # Invalid phone number
            return True
        if not self.check_region(number):
            # Non-whitelisted country code
            return True
        if not self.check_number(number):
            # Non-whitelisted number
            return True
        return False

    def __call__(self, raw_number, message, **kwargs):
        """ Send SMS message.

        This method trigges a series of events:

         - sms.pre: when this method is called
         - sms.filtered: if this method refuses to send sms to the given number
         - sms.error: if unable to send message
         - sms.sent: if the message is sent

        :param phonenumbers.PhoneNumber number: The phone number to send to.
        :param str message: The message to include.

        :return bool: True if the message was sent, False otherwise.
        """
        self.signal_sms_pre.send(self, raw_number=raw_number, message=message)

        # Transform and filter
        number = self._transform(raw_number)
        if self._filter(number):
            self.signal_sms_filtered.send(self,
                                          raw_number=raw_number,
                                          number=number,
                                          message=message)
            return False

        # Try to send
        try:
            self._send(number, message, **kwargs)
        except Exception as e:
            # TODO: Stop catching all?
            # TODO: Or, log the error?
            self.signal_sms_error.send(self,
                                       raw_number=raw_number,
                                       number=number,
                                       message=message,
                                       error=e)
            return False
        self.signal_sms_sent.send(self,
                                  raw_number=raw_number,
                                  number=number,
                                  message=message)
        return True

    def _send(self, number, message):
        raise NotImplementedError("Abstract method")


class MockSmsDispatcher(SmsDispatcher):
    """ A mock SMS dispatcher that doesn't send SMS. """

    def _send(self, number, message):
        return
