==============
pofh.extension
==============
The flask extension is an abstract class that can be used as a factory or
wrapper for other components.

A typical scenario where the extension is useful, is when we need a client or
some other object to be instantiated once per request, or once per worker. The
extension/wrapper is instantiated once per worker, and can work as a wrapper for
the actual object that is needed.

Example
=======

The following example shows an extension, ``Foo``, that creates a
``FooClient`` object.

The name ``foo`` in this example would be importable, and would create a
new ``FooClient`` each time an object attribute is accessed.

::

    class FooClient(object):
        """ some imaginary client class. """
        def __init__(self, timeout=None):
            self.timeout = timeout

    class Foo(FlaskExtension):
        """ extension wrapper. """
        def init_app(self, app):
            """ sets up default config. """
            super(Foo, self).init_app(app)
            self.set_config_default('timeout', 1.0)

        @property
        def timeout(self):
            """ timeout value from config. """
            return float(self.get_config('timeout'))

        def get_client(self):
            """ client factory. """
            return FooClient(timeout=self.timeout)

    foo = LocalProxy(lambda: Foo.get(current_app).get_client())
    """ importable name. """

    def init_app(app):
        Foo(app)


Settings
--------
The extension will be named from the class name, or the `extension_name`
class attribute, if set.

The ``timeout`` setting in the example above will be read from the Flask app
config as ``FOO_TIMEOUT``.

Per request factory
-------------------
To make a per-request factory, you can cache the client in get_client in
`flask.g`:

::

    def get_client(self):
        if not hasattr(g, '_foo_client'):
            setattr(g, '_foo_client', FooClient(timeout=self.timeout))
        return getattr(g, '_foo_client')

Per worker factory
------------------
To make a per-worker factory, you can cache the client in `get_client` in
the extension itself:

::

    def get_client(self):
        if not hasattr(self, '_client'):
            setattr(self, '_client', FooClient(timeout=self.timeout))
        return getattr(self, '_client')

Multiple extensions per worker
------------------------------
If you need multiple extensions from the same class in one
application/worker, this can be achieved by setting a custom
`extension_name` in ``__init__``.

::

    class Bar(Foo):

        def __init__(self, app=None, name='bar'):
            super(Bar, self).__init__(app=app)
            self.extension_name = name

        @classmethod
        def get(cls, name):
            return get_extension(app, name)

    bar1 = LocalProxy(lambda: Bar.get(current_app, 'bar_1').get_client())
    bar2 = LocalProxy(lambda: Bar.get(current_app, 'bar_2').get_client())

    def init_app(app):
        Bar(app, 'bar_1')
        Bar(app, 'bar_2')

Any settings would now be read from the configuration as ``BAR_1_<setting>`` and
``BAR_2_<setting>``.


Module documentation
====================

.. automodule:: pofh.extension
   :members:
