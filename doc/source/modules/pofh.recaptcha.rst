==============
pofh.recaptcha
==============
A simple Google reCAPTCHA validator for flask applications.

To set up and use reCAPTCHA, you'll need to:

1. Configure the recaptcha module for your app (with ``init_app``).
2. Decorate your request handlers with the `require_recaptcha`_ wrapper.

.. automodule:: pofh.recaptcha
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


ReCaptcha
=========
The reCAPTHCA validator is implemented as a simple class:

.. autoclass:: pofh.recaptcha.ReCaptcha
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
        validator = ReCaptcha()
        validator.verify("foo", "127.0.0.1")


Example
=======

::

    app = Flask('foo')
    app.config['RECAPTCHA_ENABLE'] = True
    app.config['RECAPTCHA_SITE_KEY'] = 'foo'
    app.config['RECAPTCHA_SECRET_KEY'] = 'bar'
    init_app(app)

    @app.route('/foo', methods=['POST', ]
    @require_recaptcha(field='g-recaptcha-response')
    def foo():
        return "Recaptcha OK!"

