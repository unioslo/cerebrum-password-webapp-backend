#!/usr/bin/env python
# encoding: utf-8
""" Unit tests for pofh.recaptcha """

import pytest
import requests_mock
from pofh.recaptcha import ReCaptcha
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
def mock(valid):
    """ a functional recaptcha module with mock backend. """
    def make_response(request, context):
        success = ('response', valid) in parse.parse_qsl(request.body)
        return json.dumps({"success": success})
    with requests_mock.Mocker() as mock:
        mock.register_uri('POST', '//example.org', text=make_response)
        yield ReCaptcha("site", "secret", "mock://example.org")


@pytest.yield_fixture
def mock_error():
    """ an erroneous recaptcha module with mock backend. """
    with requests_mock.Mocker() as mock:
        mock.register_uri('POST', '//example.org',
                          status_code=400)
        yield ReCaptcha("site", "secret", "mock://example.org")


def test_recaptcha_default_disabled(mock):
    assert mock.enabled is False


def test_recaptcha_enable(mock):
    mock.enabled = True
    assert mock.enabled is True


def test_recaptcha_success(mock, valid, ip):
    assert mock.verify(valid, ip) == True


def test_recaptcha_fail(mock, invalid, ip):
    assert mock.verify(invalid, ip) == False


def test_recaptcha_error(mock_error, valid, ip):
    with pytest.raises(Exception):
        mock.verify(valid, ip)


def test_signal_start(mock, catcher, valid, ip):
    start = catcher(mock.signal_start)
    mock.verify(valid, ip)
    assert len(start.caught) == 1
    assert start.caught[0].sender == mock
    assert start.caught[0].args['value'] == valid
    assert start.caught[0].args['remoteip'] == ip


def test_signal_done_ok(mock, catcher, valid, ip):
    done = catcher(mock.signal_done)
    mock.verify(valid, ip)
    assert len(done.caught) == 1
    assert done.caught[0].sender == mock
    assert done.caught[0].args['value'] == valid
    assert done.caught[0].args['remoteip'] == ip
    assert done.caught[0].args['status'] == True


def test_signal_done_fail(mock, catcher, invalid, ip):
    done = catcher(mock.signal_done)
    mock.verify(invalid, ip)
    assert len(done.caught) == 1
    assert done.caught[0].sender == mock
    assert done.caught[0].args['value'] == invalid
    assert done.caught[0].args['remoteip'] == ip
    assert done.caught[0].args['status'] == False


def test_signal_error(mock_error, catcher):
    error = catcher(mock_error.signal_error)
    exc = None
    try:
        mock_error.verify('foo', 'bar')
    except Exception as e:
        exc = e
    assert len(error.caught) == 1
    assert error.caught[0].sender == mock_error
    assert error.caught[0].args['value'] == 'foo'
    assert error.caught[0].args['remoteip'] == 'bar'
    assert error.caught[0].args['error'] == exc
