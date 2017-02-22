# encoding: utf-8
""" Accessory functions for rate limiting. """
from __future__ import unicode_literals, absolute_import

import functools

from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .. import apierror


def get_limiter(app):
    from limits.storage import RedisInteractor, Storage

    class redisclient_storage(RedisInteractor, Storage):
        """ Storage backend for flask-limiters backend (limiter).

        This is essentially a copy of limiter.storage.RedisStorage, if we
        disregard the usage of ..redisclient and the merging of
        initialize_storage and __init__.

        However, this is not a verbatim copy, as we'd rarther refer to
        RedisInteractor instead of self/RedisClient.
        """
        STORAGE_SCHEME = "rcs"

        def __init__(self, *args, **kwargs):
            self.storage = None

        def _maybee_do_init(f):
            @functools.wraps(f)
            def wrapper(self, *args, **kwargs):
                if self.storage is None:
                    from ..redisclient import store
                    self.storage = store
                    self.lua_moving_window = self.storage.register_script(
                        RedisInteractor.SCRIPT_MOVING_WINDOW
                    )
                    self.lua_acquire_window = self.storage.register_script(
                        RedisInteractor.SCRIPT_ACQUIRE_MOVING_WINDOW
                    )
                    self.lua_clear_keys = self.storage.register_script(
                        RedisInteractor.SCRIPT_CLEAR_KEYS
                    )
                    self.lua_incr_expire = self.storage.register_script(
                        RedisInteractor.SCRIPT_INCR_EXPIRE
                    )
                return f(self, *args, **kwargs)
            return wrapper

        @_maybee_do_init
        def incr(self, key, expiry, elastic_expiry=False):
            if elastic_expiry:
                return super(redisclient_storage, self).incr(
                    key, expiry, self.storage, elastic_expiry
                )
            else:
                return self.lua_incr_expire([key], [expiry])

        @_maybee_do_init
        def get(self, key):
            return super(redisclient_storage, self).get(key, self.storage)

        @_maybee_do_init
        def acquire_entry(self, key, limit, expiry, no_add=False):
            return super(redisclient_storage, self).acquire_entry(
                key, limit, expiry, self.storage, no_add=no_add
            )

        @_maybee_do_init
        def get_expiry(self, key):
            return super(redisclient_storage, self).get_expiry(key,
                                                               self.storage)

        @_maybee_do_init
        def check(self):
            return super(redisclient_storage, self).check(self.storage)

        @_maybee_do_init
        def reset(self):
            cleared = self.lua_clear_keys(['LIMITER*'])
            return cleared

    redis_url = "rcs://"
    limiter = Limiter(
        app,
        key_func=get_remote_address,
        storage_uri=redis_url,
        strategy='moving-window')
    for handler in app.logger.handlers:
        limiter.logger.addHandler(handler)

    def e():
        raise RateLimitError

    limiter.limit = functools.partial(limiter.limit, error_message=e)

    return limiter


RATE_LIMIT_PREFIX = 'rate-limit'


class RateLimitError(apierror.ApiError):
    """Too Many Requests"""
    code = 429
    details = "Try again soon."


def exponential_ratelimit():
    """Limit to at most 60 requests per second, with exponentially increasing
    time penalty.

    Returns the wrapped function, or raises RateLimitError.
    """
    def w(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from ..redisclient import store
            scope = "{}:{}:{}".format(RATE_LIMIT_PREFIX,
                                      func.__name__,
                                      request.remote_addr)
            state = store.get(scope)
            ok = False
            if not state:
                state = 1
                ok = True
            store.incr(scope)
            store.expire(scope, int(state)**2)
            if ok:
                return func(*args, **kwargs)
            else:
                raise RateLimitError()
        return wrapper
    return w
