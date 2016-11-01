==========
pofh.stats
==========

Module
======
.. automodule:: pofh.stats

Use
===
The ``pofh.stats`` module contains a flask wrapper that configures and sets up
a global application statsd client.

To set up and use this module to record metrics to ``statsd``, you'll need to:

1. Initialize the `Statsd extension`_
2. Record metrics using the ``statsd`` proxy object.


Statsd extension
================
.. autoclass:: pofh.stats.Statsd
    :members:

init_app
--------
If initialized with :py:func:`pofh.stats.init_app`, the application setup will
fail with an exception if anything is missing from the configuration.

If Flask debug mode is set, some addiotional routes will be set up in the
application that demoes the statsd functionality.

Example
-------
Basic statsd metrics can be enabled in an app by initializing the stats module
and configuring it:

::

    app = Flask('example')
    pofh.stats.init_app(app)
    app.config['STATSD_ENABLE'] = True
    app.config['STATSD_PREFIX'] = 'example'

    # Increment 'example.foo'
    pofh.stats.statsd.incr('foo')
