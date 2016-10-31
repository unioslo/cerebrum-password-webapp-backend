# encoding: utf-8
""" This sub-package includes functionality for logging stats to statsd.

Settings
--------
The following settings are used from the Flask configuration:

``STATSD_ENABLE`` (:py:class:`bool`)
    Set to True to enable statsd support.

``STATSD_HOST`` (:py:class:`str`)
    The statsd hostname.

``STATSD_HOST`` (:py:class:`int`)
    The statsd UDP port.

``STATSD_PREFIX`` (:py:class:`str`)
    A global prefix for metrics.

"""

from werkzeug.local import LocalProxy
from flask import current_app, Blueprint
from statsd import StatsClient
from statsd.client import Pipeline, StatsClientBase
from .extension import FlaskExtension


class DummyStatsdClient(StatsClientBase):
    """ Dummy statsd client.

    This client is used if ``STATSD_ENABLE`` is set to ``False``.

    NOTE: The default StatsdClient sends metrics using UDP, so there's no
    actual need for a mock client / dummy client.

    The client will simply not attempt to send any metrics. This allows us to
    set up logging of metrics without actually having UDP packets sent to a
    host that won't accept them.

    """

    def __init__(self, prefix=None):
        self._prefix = prefix

    def _send(self, data):
        """ Don't actually send anything. """
        pass

    def pipeline(self):
        return Pipeline(self)


class Statsd(FlaskExtension):
    """ Statsd proxy/factory for flask applications. """

    def __init__(self, app=None):
        self.statsd = None
        super(Statsd, self).__init__(app=app)

    def init_app(self, app):
        super(Statsd, self).init_app(app)
        self.set_config_default('enable', False)
        self.set_config_default('host', 'localhost')
        self.set_config_default('port', 8125)
        self.set_config_default('prefix', None)

    @property
    def enabled(self):
        return bool(self.get_config('enable'))

    @property
    def host(self):
        return str(self.get_config('host'))

    @property
    def port(self):
        return int(self.get_config('port'))

    @property
    def prefix(self):
        return self.get_config('prefix')

    def make_client(self):
        if not self.enabled:
            return DummyStatsdClient(
                prefix=self.prefix)
        else:
            return StatsClient(
                    host=self.host,
                    port=self.port,
                    prefix=self.prefix,
                    ipv6=False)

    @property
    def client(self):
        """ The statsd client (StatsClient). """
        if not hasattr(self, '_client'):
            setattr(self, '_client', self.make_client())
        return getattr(self, '_client')


extension = LocalProxy(lambda: Statsd.get(current_app))
""" Easy access to the Statsd wrapper. """

statsd = LocalProxy(lambda: extension.client)
""" The statsd client. """


TEST_API = Blueprint('statsd', __name__, url_prefix='/stats')
""" Test api, enabled when DEBUG mode is on. """


@TEST_API.route('/incr')
def incr():
    """ increases a count metric.

    The counter is stored in the ``<STATSD_PREFIX>.stats-test.value`` metric.
    """
    statsd.incr('stats-test.value')
    return ('', 204)


@TEST_API.route('/decr')
def decr():
    """ decreases a count metric.

    The counter is stored in the ``<STATSD_PREFIX>.stats-test.value`` metric.
    """
    statsd.decr('stats-test.value')
    return ('', 204)


@TEST_API.route('/gauge/<int:value>', methods=['PUT'])
def gauge(value):
    """ sets a gauge metric to ``value``.

    The gauge is stored in the ``<STATSD_PREFIX>.stats-test.gauge`` metric.
    """
    statsd.gauge('stats-test.gauge', value)
    return ('', 204)


@TEST_API.route('/time')
def timer():
    """ sorts a bunch of numbers and records the time.

    The time used is stored in the ``<STATSD_PREFIX>.stats-test.time`` timer
    metric.
    """
    from flask import jsonify
    import random
    with statsd.timer('stats-test.sort-random'):
        sort = sorted([random.random() for i in range(5000)])
        return jsonify({'sorted': list(sort)[:10]})


@TEST_API.before_request
def record_request_stats():
    from flask import g, request
    import re
    import time

    def sanitize(url):
        url = str(url).lstrip('/')
        for pattern, replace in [
                (r'[/]', '.'),
                (r'[ ]', '-'),
                (r'[^-_a-zA-Z0-9.]', ''), ]:
            url = re.sub(pattern, replace, url)
        return url
    g.stat_request_start = time.time()
    g.stat_request_method = str(request.method).lower()
    g.stat_request_rule = sanitize(request.url_rule)


@TEST_API.after_request
def record_response_stats(response):
    """ Stores a few count and timer metrics for each request to the test api.

    Metrics:

      - <STATSD_PREFIX>.stats-test.request.<method>.<rule> counter
      - <STATSD_PREFIX>.stats-test.all timer
      - <STATSD_PREFIX>.stats-test.request.<method>.<rule> timer
    """
    from flask import g
    import time
    request_time = int((time.time() - g.stat_request_start) * 1000)
    # Count requests per route
    statsd.incr(
        '.'.join(('stats-test', 'request',
                  g.stat_request_method,
                  g.stat_request_rule)))
    statsd.timing('stats-test.all', request_time)
    statsd.timing(
        '.'.join(('stats-test', 'request',
                  g.stat_request_method,
                  g.stat_request_rule)),
        request_time)
    return response


def init_app(app):
    """ Set up the stats extension. """
    extension = Statsd(app)

    if extension.enabled:
        # Get client at startup to catch any issues:
        extension.client

    if app.debug:
        app.register_blueprint(TEST_API)
