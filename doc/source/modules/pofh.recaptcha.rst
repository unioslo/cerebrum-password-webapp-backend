==============
pofh.recaptcha
==============
.. automodule:: pofh.recaptcha

Use
---
To set up and use recaptcha, you'll need to:

1. Configure the recaptcha module for your app (with the `Recaptcha app`_).
2. Decorate your request handlers with the `require_recaptcha`_ wrapper.


Recaptcha app
=============
.. autoclass:: pofh.recaptcha.Recaptcha
   :members:

init_app
--------
If initialized with :py:func:`pofh.recaptcha.init_app`, the application setup
will fail with a :py:class:`RuntimeError` if the module is configured
incorrectly.

If Flask debug mode is set, two additional routes will be set up in the
application that allows you to test the Recaptcha integration.

.. autofunction:: pofh.recaptcha.init_app


require_recaptcha
=================
To protect a request handler with recaptcha, it needs to be decorated with the
`require_recaptcha`_ wrapper.

This wrapper inspects the current request body (assuming it to be either
``application/JSON`` or ``application/x-www-form-urlencoded``) for the
configured value (``g-recaptcha-response``), and validates it.

If the value is missing or does not pass validation, a HTTP 400 response is
returned from the request handler.

.. autofunction:: pofh.recaptcha.require_recaptcha


RecaptchaClient
===============
The recaptcha validator is implemented as a separate class:

.. autoclass:: pofh.recaptcha.RecaptchaClient
   :members:

Signals
-------
The validator can issue three separate :py:class:`blinker.Signal` signals when
validating recaptcha responses.

``recaptcha.start``
    Always issued when attempting to validate a recaptcha response.
    Includes keyword arguments:

    ``value`` (:py:class:`str`)
        The recaptcha response that is being validated.
    ``remoteip`` (:py:class:`str`)
        The remoteip that is sent to the validation service.

``recaptcha.done``
    Issued when validation completes.
    Includes keyword arguments:

    ``value`` (:py:class:`str`)
        The recaptcha response that is being validated.
    ``remoteip`` (:py:class:`str`)
        The remoteip that is sent to the validation service.
    ``status`` (:py:class:`bool`)
        Result from the validation service

``recaptcha.error``
    Issued if validation fails for some reason.
    Includes keyword arguments:

    ``value`` (:py:class:`str`)
        The recaptcha response that is being validated.
    ``remoteip`` (:py:class:`str`)
        The remoteip that is sent to the validation service.
    ``error`` (:py:class:`Exception`)
        The error that happened.

Example

    ::

        signal = blinker.signal('recaptcha.error')
        @signal.connect()
        def logger(sender, **kw):
            print("Recaptcha failed: {!r}".format(kw))
        validator = RecaptchaClient()
        validator("foo", "127.0.0.1")


Example
=======

::

    app = Flask('foo')
    app.config['RECAPTCHA_ENABLE'] = True
    app.config['RECAPTCHA_SECRET_KEY'] = 'bar'
    Recaptcha(app)

    @app.route('/foo', methods=['POST', ]
    @require_recaptcha(field='g-recaptcha-response')
    def foo():
        return "Recaptcha OK!"
