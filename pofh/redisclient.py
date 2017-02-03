# encoding: utf-8
""" Simple redis store.

Settings
--------
``REDIS_URL` (:py:class:`str`)
    The URL to the redis database.

    Examples:

     * mock://
     * redis://:password@localhost:6379/0
     * redis+sentinel://:password@localhost:26379/mymaster/0
     * unix://:password@/path/to/socket.sock?db=0

"""
from __future__ import unicode_literals, absolute_import

from flask_redis_sentinel import SentinelExtension


class RedisProvider(object):
    def __init__(self, app=None, client_class=None, **kwargs):
        self._client_class = client_class
        self._client = None
        self._sentinel = None

        if app is not None:
            self.init_app(app)

    def init_app(self, app, **kwargs):
        self._sentinel = SentinelExtension(app,
                                           client_class=self._client_class)
        self._client = self._sentinel.default_connection

    def __getattr__(self, name):
        return getattr(self._client, name)

    def __getitem__(self, name):
        return self._client[name]

    def __setitem__(self, name, value):
        self._client[name] = value

    def __delitem__(self, name):
        del self._client[name]

store = RedisProvider()
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
        current_app.logger.debug(
            "Store-debug: Getting '{!s}'".format(real_key))
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
    app.config.setdefault('REDIS_URL', "redis://localhost:6379/0")

    if not app.config['REDIS_URL']:
        raise RuntimeError("No 'REDIS_URL' configured")

    if app.config['REDIS_URL'].startswith('mock://'):
        from mockredis import MockRedis as _MockRedis

        class MockRedis(_MockRedis):
            @classmethod
            def from_url(cls, *args, **kwargs):
                return cls(strict=True)
        # Trick the URL parser
        app.config['REDIS_URL'] = app.config['REDIS_URL'].replace('mock://',
                                                                  'redis://')
        app.config['REDIS_CLASS'] = MockRedis
        app.logger.debug('Using a mock Redis client')

    store.init_app(app)

    if app.debug:
        init_debug(app)
