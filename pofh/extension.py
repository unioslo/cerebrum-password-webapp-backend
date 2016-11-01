# encoding: utf-8
""" Abstract flask extension.  """
from six import with_metaclass


APP_EXTENSIONS_ATTRIBUTE = 'extensions'
""" Attribute name to use when storing extenstions. """


def register_extension(app, extension, name):
    """ Stores an object as a named extension in app object.

    :param flask.Flask app: The application to register the extension in.
    :param object extension: The extension to register.
    :param str name: The name of this extension.

    After calling this method, the `extension` object will be available in
    ``getattr(app, APP_EXTENSIONS_ATTRIBUTE)[name.lower()]``.

    """
    if app is None:
        raise RuntimeError("No application.")
    name = name.lower()
    extensions = getattr(app, APP_EXTENSIONS_ATTRIBUTE, {})
    extensions[name] = extension
    setattr(app, APP_EXTENSIONS_ATTRIBUTE, extensions)


def has_extension(app, name):
    """ Checks if a named extension exists in the application.

    :param flask.Flask app: The application to register the extension in.
    :param str name: The name of this extension.

    :return bool: True if the extension name is available.
    """
    name = name.lower()
    return name in getattr(app, APP_EXTENSIONS_ATTRIBUTE, {})


def get_extension(app, name):
    """ Gets a named extension from an application.

    :param flask.Flask app: The application to register the extension in.
    :param str name: The name of this extension.

    :return object: The registered extension object
    """
    name = name.lower()
    if not has_extension(app, name):
        return RuntimeError(
            "Extension '{!s}' not initialized".format(name))
    return getattr(app, APP_EXTENSIONS_ATTRIBUTE, {})[name]


class ExtensionType(type):
    """ A metaclass that populates an ``extension_name`` class attribute.

    The ``extension_name`` is generated from the class name, if not explicitly
    given in the class.
    """

    def __init__(cls, name, bases, dct):
        cls.extension_name = dct.pop('extension_name', '').lower()
        if not cls.extension_name:
            cls.extension_name = name.lower()
        super(ExtensionType, cls).__init__(name, bases, dct)


class FlaskExtension(with_metaclass(ExtensionType, object)):
    """ Simple wrapper object that stores itself in an application. """

    def __init__(self, app=None):
        self._app = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """ Initialize extension.

        :param flask.Flask app: The application to register the extension in.
        """
        self._app = app
        register_extension(app, self, self.extension_name)

    def set_config_default(self, name, default=None):
        """ Set a default value in the application config.

        The actual setting will be in upper case, and prefixed with the
        `extension_name` (e.g. ``Foo().set_config_default('bar')`` will set
        FOO_BAR to ``None``).

        :param str name: The setting base name, without any prefix.
        :param default: The default value of this setting.
        """
        name = '{!s}_{!s}'.format(self.extension_name, name).upper()
        self._app.config.setdefault(name, default)

    def get_config(self, name, default=None):
        """ Gets a setting value from the application config.

        The actual setting will be in upper case, and prefixed with the
        `extension_name` (e.g. ``Foo().get_config('bar')`` will get FOO_BAR or
        ``None``).

        :param str name: The setting base name, without any prefix.
        :param default: The default value if the setting is not set.
        """
        name = '{!s}_{!s}'.format(self.extension_name, name).upper()
        value = default
        if self._app is not None:
            value = self._app.config.get(name, default)
        return value

    @classmethod
    def get(cls, app):
        """ Get the current extension of this type from an app object.

        :param flask.Flask app:
            The application object to fetch the extension from.

        :return:
            Returns the extension, if it is initialized with this app object.
        """
        return get_extension(app, cls.extension_name)
