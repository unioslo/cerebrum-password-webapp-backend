# encoding: utf-8
""" Simple redis store.

Settings
--------
``REDIS_URL` (:py:class:`str`)
    The URL to the redis database.

    Examples:

     * mock://
     * redis://:password@localhost:6379/0
     * unix://:password@/path/to/socket.sock?db=0

"""
from __future__ import unicode_literals, absolute_import

from flask_redis import FlaskRedis
from werkzeug.local import LocalProxy


class RedisFactory(object):
    """ Simple FlaskRedis factory.

    This allows us to set up FlaskRedis as a localproxy, and replace the
    default FlaskRedis provider with a mock provider.
    """

    def __init__(self, provider):
        self._provider = provider
        self._obj = None

    def __call__(self):
        if self._obj is None:
            if issubclass(self._provider, FlaskRedis):
                self._obj = self._provider()
            else:
                self._obj = FlaskRedis.from_custom_provider(self._provider)
        return self._obj

    def set_provider(self, provider):
        self._provider = provider
        self._obj = None

factory = RedisFactory(FlaskRedis)


# Note: FlaskRedis doesn't need a LocalProxy, but this allows us to import
# the `store` name from this module before `init_app`, and use the modified
# object after `init_app` has been called.
store = LocalProxy(factory)
""" The redis store."""


def init_debug(app):
    """ Add routes for debugging and testing. """
    from flask import current_app, jsonify, Blueprint

    TEST_API = Blueprint('store', __name__, url_prefix='/store-test')
    TEST_KEY_PREFIX = 'store-debug:'

    @TEST_API.route('/<string:key>/<string:value>', methods=['PUT', ])
    def _debug_store_set(key, value):
        key = '{!s}{!s}'.format(TEST_KEY_PREFIX, key)
        current_app.logger.debug(
            "Store-debug: Setting '{!s}' to '{!s}'".format(key, value))
        store.set(key, value)
        return ('', 204)

    @TEST_API.route('/<string:key>', methods=['GET', ])
    def _debug_store_get(key):
        real_key = '{!s}{!s}'.format(TEST_KEY_PREFIX, key)
        current_app.logger.debug("Store-debug: Getting '{!s}'".format(real_key))
        return jsonify({key: store.get(real_key)})

    @TEST_API.route('/', methods=['GET', ])
    def _debug_store_list():
        current_app.logger.debug("Store-debug: Listing keys")
        data = dict()
        for key in store.scan_iter(match='{!s}*'.format(TEST_KEY_PREFIX)):
            data[key[len(TEST_KEY_PREFIX):]] = store.get(key)
        return jsonify(data)

    app.register_blueprint(TEST_API)


def init_app(app):
    """ Configure the redis provider and connection params. """
    global _factory

    app.config.setdefault('REDIS_URL', "redis://localhost:6379/0")

    if not app.config['REDIS_URL']:
        raise RuntimeError("No 'REDIS_URL' configured")

    if app.config['REDIS_URL'].startswith('mock://'):
        from mockredis import MockRedis as _MockRedis

        class MockRedis(_MockRedis):
            @classmethod
            def from_url(cls, *args, **kwargs):
                return cls()

        factory.set_provider(MockRedis)

    store.init_app(app)

    if app.debug:
        init_debug(app)
