""" Unit tests for pofh.middleware """

import pytest

from pofh import extension


def test_metaclass_implicit_name():
    class _Test(extension.FlaskExtension):
        pass

    assert _Test.extension_name == '_test'


def test_metaclass_explicit_name():
    class _Test(extension.FlaskExtension):
        extension_name = 'MyExtension'

    assert _Test.extension_name == 'myextension'


def test_class_expicit_name():
    class _Test(extension.FlaskExtension):
        def __init__(self):
            self.extension_name = 'asdf'

    test = _Test()
    assert test.extension_name == 'asdf'


NAME = 'TEST_EXTENSION'


@pytest.fixture
def Extension():
    class _TestExtension(extension.FlaskExtension):
        extension_name = NAME
    return _TestExtension


def test_register_extension(app):
    x = object()
    extension.register_extension(app, x, NAME)
    registered = getattr(app, extension.APP_EXTENSIONS_ATTRIBUTE)
    assert len(registered) == 1
    assert NAME.lower() in registered
    assert registered[NAME.lower()] is x


def test_has_extension(app):
    x = object()
    extension.register_extension(app, x, NAME)
    assert extension.has_extension(app, NAME)


def test_get_extension(app):
    x = object()
    extension.register_extension(app, x, NAME)
    assert extension.get_extension(app, NAME) is x


def test_init(app, Extension):
    Extension(app)
    assert extension.has_extension(app, NAME)


def test_set_default(app, Extension):
    foo_name = '{!s}_FOO'.format(Extension.extension_name.upper())
    bar_name = '{!s}_BAR'.format(Extension.extension_name.upper())
    app.config[foo_name] = 2

    ext = Extension(app)
    ext.set_config_default('foo', 1)
    ext.set_config_default('bar', 'test')

    assert app.config[foo_name] == 2
    assert app.config[bar_name] == 'test'


def test_get_config(app, Extension):
    ext = Extension(app)
    ext.set_config_default('foo', 1)
    ext.set_config_default('bar', 'test')

    assert ext.get_config('foo') == 1
    assert ext.get_config('bar') == 'test'
    assert ext.get_config('baz', 'default') == 'default'
    assert ext.get_config('bat') is None


def test_get_init(app, Extension):
    ext = Extension(app)
    assert Extension.get(app) is ext
