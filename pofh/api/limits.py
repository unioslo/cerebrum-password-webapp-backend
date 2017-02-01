# encoding: utf-8
""" Accessory functions for rate limiting. """
from __future__ import unicode_literals, absolute_import

from functools import wraps

from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .. import apierror


def get_limiter(app):
    if ('REDIS_URL' in app.config and
            any(map(lambda x: app.config['REDIS_URL'].startswith(x),
                    ['redis://', 'redis+sentinel://', 'redis+cluster://']))):
        redis_url = app.config['REDIS_URL']
    else:
        redis_url = None

    limiter = Limiter(
        app,
        key_func=get_remote_address,
        storage_uri=redis_url)
    for handler in app.logger.handlers:
        limiter.logger.addHandler(handler)
    return limiter


RATE_LIMIT_PREFIX = 'rate-limit:'


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
        @wraps(func)
        def wrapper(*args, **kwargs):
            from ..redisclient import store
            scope = "{}{}".format(RATE_LIMIT_PREFIX, request.remote_addr)
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
