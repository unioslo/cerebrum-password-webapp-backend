#!/usr/bin/env python
# encoding: utf-8
""" Unit tests for app.config """

import pytest
from pofh.sms import dispatcher

from collections import namedtuple


@pytest.fixture
def abstract():
    return dispatcher.SmsDispatcher()


def test_add_whitelist(abstract):
    assert len(abstract.whitelist) == 0
    abstract.add_whitelist('^foo$')
    assert len(abstract.whitelist) == 1
    assert abstract.whitelist[0].pattern == '^foo$'


def test_empty_whitelist(abstract):
    assert abstract.check_whitelist('') is False
    assert abstract.check_whitelist('12345678') is False


def test_whitelist_item(abstract):
    abstract.add_whitelist('^foo$')
    assert abstract.check_whitelist('foo') is True
    assert abstract.check_whitelist('bar') is False


def test_whitelist(abstract):
    abstract.add_whitelist('^fo.*$')
    abstract.add_whitelist('^ba.*$')
    assert abstract.check_whitelist('foo') is True
    assert abstract.check_whitelist('bar') is True
    assert abstract.check_whitelist('baz') is True
    assert abstract.check_whitelist('fail') is False


@pytest.fixture
def mock():
    d = dispatcher.MockSmsDispatcher()
    d.add_whitelist(r'^\d+$')
    return d


@pytest.fixture
def smserror():
    class _err(dispatcher.SmsDispatcher):
        def send(self, number, message):
            raise RuntimeError("err")
    return _err()


@pytest.fixture
def catcher():
    Recv = namedtuple('Recv', ('sender', 'args'))

    class _catcher(object):
        def __init__(self, signal):
            signal.connect(self)
            self.caught = []

        def __call__(self, sender, **kwargs):
            self.caught.append(Recv(sender, kwargs))
    return _catcher


def test_signal_pre(mock, catcher):
    pre = catcher(mock.signal_sms_pre)
    # All sms dispatcher calls should cause a signal_sms_pre
    mock('123', 'foo')
    assert len(pre.caught) == 1
    assert pre.caught[0].sender == mock
    assert pre.caught[0].args['number'] == '123'
    assert pre.caught[0].args['message'] == 'foo'


def test_signal_filter(mock, catcher):
    filtered = catcher(mock.signal_sms_filtered)
    # Mock only contains a /^\d+$/ whitelist, should be filtered
    mock('foo', 'foo')
    assert len(filtered.caught) == 1
    assert filtered.caught[0].sender == mock
    assert filtered.caught[0].args['number'] == 'foo'
    assert filtered.caught[0].args['message'] == 'foo'


def test_signal_sent(mock, catcher):
    sent = catcher(mock.signal_sms_sent)
    # Should be sent
    mock('123', 'foo')
    assert len(sent.caught) == 1
    assert sent.caught[0].sender == mock
    assert sent.caught[0].args['number'] == '123'
    assert sent.caught[0].args['message'] == 'foo'


def test_signal_error(smserror, catcher):
    errors = catcher(smserror.signal_sms_error)
    smserror.add_whitelist(r'^\d+$')
    smserror('123', 'foo')
    assert len(errors.caught) == 1
    assert errors.caught[0].sender == smserror
    assert errors.caught[0].args['number'] == '123'
    assert errors.caught[0].args['message'] == 'foo'
    assert isinstance(errors.caught[0].args['error'], RuntimeError)
