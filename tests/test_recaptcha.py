#!/usr/bin/env python
# encoding: utf-8
""" Unit tests for pofh.recaptcha """
from __future__ import unicode_literals, absolute_import, print_function

import pytest
import requests_mock
from pofh.recaptcha import RecaptchaClient, Recaptcha, recaptcha
import json
from six.moves.urllib import parse


@pytest.fixture
def valid():
    """ valid g-recaptcha-response. """
    return "foo"


@pytest.fixture
def invalid():
    """ invalid g-recaptcha-response. """
    return "bar"


@pytest.fixture
def ip():
    """ ip address. """
    return '127.0.0.1'


@pytest.yield_fixture
def client(valid):
    """ a functional recaptcha module with mock backend. """
    def make_response(request, context):
        success = ('response', valid) in parse.parse_qsl(request.body)
        return json.dumps({"success": success})
    with requests_mock.Mocker() as mock:
        mock.register_uri('POST', '//example.org', text=make_response)
        yield RecaptchaClient("secret", "mock://example.org")


@pytest.yield_fixture
def client_error():
    """ an erroneous recaptcha module with mock backend. """
    with requests_mock.Mocker() as mock:
        mock.register_uri('POST', '//example.org',
                          status_code=400)
        yield RecaptchaClient("secret", "mock://example.org")


def test_recaptcha_success(client, valid, ip):
    assert client(valid, ip) is True


def test_recaptcha_fail(client, invalid, ip):
    assert client(invalid, ip) is False


def test_recaptcha_error(client_error, valid, ip):
    with pytest.raises(Exception):
        client_error(valid, ip)


def test_signal_start(client, catcher, valid, ip):
    start = catcher(client.signal_start)
    client(valid, ip)
    assert len(start.caught) == 1
    assert start.caught[0].sender == client
    assert start.caught[0].args['value'] == valid
    assert start.caught[0].args['remoteip'] == ip


def test_signal_done_ok(client, catcher, valid, ip):
    done = catcher(client.signal_done)
    client(valid, ip)
    assert len(done.caught) == 1
    assert done.caught[0].sender == client
    assert done.caught[0].args['value'] == valid
    assert done.caught[0].args['remoteip'] == ip
    assert done.caught[0].args['status'] is True


def test_signal_done_fail(client, catcher, invalid, ip):
    done = catcher(client.signal_done)
    client(invalid, ip)
    assert len(done.caught) == 1
    assert done.caught[0].sender == client
    assert done.caught[0].args['value'] == invalid
    assert done.caught[0].args['remoteip'] == ip
    assert done.caught[0].args['status'] is False


def test_signal_error(client_error, catcher):
    error = catcher(client_error.signal_error)
    exc = None
    try:
        client_error('foo', 'bar')
    except Exception as e:
        exc = e
    assert len(error.caught) == 1
    assert error.caught[0].sender == client_error
    assert error.caught[0].args['value'] == 'foo'
    assert error.caught[0].args['remoteip'] == 'bar'
    assert error.caught[0].args['error'] == exc


def test_middleware_init(app):
    Recaptcha(app)
    assert Recaptcha.extension_name in app.extensions


def test_middleware_disable(app):
    app.config['RECAPTCHA_ENABLE'] = False
    middleware = Recaptcha(app)
    assert middleware.enabled is False


def test_middleware_enable(app):
    app.config['RECAPTCHA_ENABLE'] = True
    middleware = Recaptcha(app)
    assert middleware.enabled is True


def test_middleware_proxy(app):
    app.config['RECAPTCHA_ENABLE'] = True
    Recaptcha(app)
    with app.app_context():
        assert recaptcha.enabled is True


def test_middleware_get_client_error(app):
    app.config['RECAPTCHA_ENABLE'] = True
    middleware = Recaptcha(app)
    # missing RECAPTCHA_SECRET_KEY
    with pytest.raises(AttributeError):
        middleware.client


def test_middleware_get_client(app):
    app.config['RECAPTCHA_ENABLE'] = True
    app.config['RECAPTCHA_SECRET_KEY'] = 'foo'
    middleware = Recaptcha(app)
    # missing RECAPTCHA_SECRET_KEY
    assert isinstance(middleware.client, RecaptchaClient)
    assert middleware.client.secret_key == app.config['RECAPTCHA_SECRET_KEY']
