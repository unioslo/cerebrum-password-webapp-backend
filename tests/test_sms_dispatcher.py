#!/usr/bin/env python
# encoding: utf-8
""" Unit tests for pofh.sms """
from __future__ import unicode_literals, absolute_import, print_function

import pytest
import phonenumbers
from pofh.sms import dispatcher


@pytest.fixture
def valid_number():
    # +4722855050 belongs to the University of Oslo
    return phonenumbers.PhoneNumber(country_code=47, national_number=22855050)


@pytest.fixture
def invalid_number():
    # 7 digit number, which is not allowed by NKOM
    return phonenumbers.PhoneNumber(country_code=47, national_number=2285505)


def fmt(number):
    """ Normalize a phone number object. """
    return phonenumbers.format_number(
        number,
        phonenumbers.PhoneNumberFormat.E164)


@pytest.fixture
def abstract():
    return dispatcher.SmsDispatcher()


def test_filter_valid_number(abstract, valid_number):
    assert abstract.filter(valid_number) is None


def test_filter_invalid_number(abstract, invalid_number):
    with pytest.raises(dispatcher.FilterException) as exc:
        abstract.filter(invalid_number)
    assert str(exc.value) == 'invalid-phone-number'


def test_whitelist_region(abstract, valid_number):
    abstract.whitelist_regions = True
    with pytest.raises(dispatcher.FilterException) as exc:
        abstract.filter(valid_number)
    assert str(exc.value) == 'invalid-region'
    abstract.add_region("SE")
    with pytest.raises(dispatcher.FilterException) as exc:
        abstract.filter(valid_number)
    assert str(exc.value) == 'invalid-region'
    abstract.add_region("NO")
    assert abstract.filter(valid_number) is None


def test_whitelist_number(abstract, valid_number):
    abstract.whitelist_numbers = True
    with pytest.raises(dispatcher.FilterException) as exc:
        abstract.filter(valid_number)
    assert str(exc.value) == 'not-whitelisted'
    abstract.add_number(fmt(valid_number))
    assert abstract.filter(valid_number) is None


@pytest.fixture
def mock():
    d = dispatcher.MockSmsDispatcher()
    return d


@pytest.fixture
def smserror():
    class _err(dispatcher.SmsDispatcher):
        def send(self, number, message):
            raise RuntimeError("err")
    return _err()


def test_signal_pre(mock, catcher, valid_number):
    pre = catcher(mock.signal_sms_pre)
    # All sms dispatcher calls should cause a signal_sms_pre
    mock(fmt(valid_number), 'foo')
    assert len(pre.caught) == 1
    assert pre.caught[0].sender == mock
    assert pre.caught[0].args['raw_number'] == fmt(valid_number)
    assert pre.caught[0].args['message'] == 'foo'


def test_signal_filter(mock, catcher, invalid_number):
    filtered = catcher(mock.signal_sms_filtered)
    mock(fmt(invalid_number), 'foo')
    assert len(filtered.caught) == 1
    assert filtered.caught[0].sender == mock
    assert filtered.caught[0].args['raw_number'] == fmt(invalid_number)
    assert filtered.caught[0].args['number'] == invalid_number
    assert filtered.caught[0].args['message'] == 'foo'
    assert filtered.caught[0].args['reason'] == 'invalid-phone-number'


def test_signal_sent(mock, catcher, valid_number):
    sent = catcher(mock.signal_sms_sent)
    # Should be sent
    mock(fmt(valid_number), 'foo')
    assert len(sent.caught) == 1
    assert sent.caught[0].sender == mock
    assert sent.caught[0].args['raw_number'] == fmt(valid_number)
    assert sent.caught[0].args['number'] == valid_number
    assert sent.caught[0].args['message'] == 'foo'


def test_signal_error(smserror, catcher, valid_number):
    errors = catcher(smserror.signal_sms_error)
    smserror(fmt(valid_number), 'foo')
    assert len(errors.caught) == 1
    assert errors.caught[0].sender == smserror
    assert errors.caught[0].args['raw_number'] == fmt(valid_number)
    assert errors.caught[0].args['number'] == valid_number
    assert errors.caught[0].args['message'] == 'foo'
    assert isinstance(errors.caught[0].args['error'], RuntimeError)
