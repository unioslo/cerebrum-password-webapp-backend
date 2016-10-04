========
pofh.sms
========

init_app
========
To set up a default app dispatcher, ``init_app`` needs to be called on the Flask
application. This will set up the dispatcher with configuration from the app
(see `configuration`_).

.. autofunction:: pofh.sms.init_app

send_sms
========
To send sms using the configured dispatcher, use ``send_sms``.

.. autofunction:: pofh.sms.send_sms


The dispatcher
==============
The dispatcher is an abstract implementation of communication with an SMS
service.


Whitelist
---------
The dispatcher supports whitelisting numbers or regions.

Enable region whitelist, with Norway and Sweden whitelisted:

    ::

        dispatcher = SmsDispatcher()
        dispatcher.whitelist_regions = True
        dispatcher.add_region('NO')
        dispatcher.add_region('SE')

Enable number whitelist, with one whitelisted number:

    ::

        dispatcher = SmsDispatcher()
        dispatcher.whitelist_numbers = True
        dispatcher.add_number("+47 228 55 050")


Signals
-------
The dispatcher can issue four separate :py:class:`blinker.Signal` signals when
trying to send an SMS. Each registered handler will receive the sender class and
a series of keyword arguments.

``sms.pre``
    Always issued when attempting to send an SMS.
    Includes keyword arguments:

    ``raw_number`` (:py:class:`str`)
        The phone number value.
    ``message`` (:py:class:`str`)
        The SMS message value.

``sms.filtered``
    Issued if the SMS is not sent because the number was not valid or
    not whitelisted.
    Includes keyword arguments:

    ``raw_number`` (:py:class:`str`)
        The phone number value.
    ``message`` (:py:class:`str`)
        The SMS message value.
    ``number`` (:py:class:`phonenumbers.PhoneNumber`)
        The parsed phone number.

``sms.error``
    Issued if the SMS is not sent because some error occured.
    Includes keyword arguments:

    ``raw_number`` (:py:class:`str`)
        The phone number value.
    ``message`` (:py:class:`str`)
        The SMS message value.
    ``number`` (:py:class:`phonenumbers.PhoneNumber`)
        The parsed phone number.
    ``error`` (:py:class:`Exception`)
        The error that happened.

``sms.sent``
    Issued if the SMS is sent.
    Includes keyword arguments:

    ``raw_number`` (:py:class:`str`)
        The phone number value.
    ``message`` (:py:class:`str`)
        The SMS message value.
    ``number`` (:py:class:`phonenumbers.PhoneNumber`)
        The parsed phone number.


Example

    ::

        signal = blinker.signal('sms.pre')
        @signal.connect()
        def listener(sender, **kw):
            print("Trying to send {!r} to {!s}".format(kw['message'], kw['raw_number']))
        MockSmsDispatcher()(123, 'hello')


Dispatchers
-----------

.. autoclass:: pofh.sms.dispatcher.SmsDispatcher
   :members:

.. autoclass:: pofh.sms.dispatcher.MockSmsDispatcher
   :members:

.. autoclass:: pofh.sms.uio_gateway.UioGatewayDispatcher
   :members:


Configuration
=============
.. automodule:: pofh.sms

UiO gateway configuration
-------------------------
.. automodule:: pofh.sms.uio_gateway
