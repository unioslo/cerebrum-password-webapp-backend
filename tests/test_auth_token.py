#!/usr/bin/env python
# encoding: utf-8
""" Unit tests for app.config """

import pytest
import datetime
import calendar
from pofh.auth import token as module


def test_new_empty():
    token = module.JWTAuthToken.new()
    assert token.namespace is None
    assert token.identity is None
    assert token.iss is None


def test_new_pos():
    token = module.JWTAuthToken.new('foo', 'bar', 'baz')
    assert token.namespace == 'foo'
    assert token.identity == 'bar'
    assert token.iss == 'baz'


def test_new_kw():
    token = module.JWTAuthToken.new(issuer='baz',
                                    identity='bar',
                                    namespace='foo')
    assert token.namespace == 'foo'
    assert token.identity == 'bar'
    assert token.iss == 'baz'


@pytest.fixture
def namespace():
    return 'test_namespace'


@pytest.fixture
def identity():
    return 'test_identity'


@pytest.fixture
def issuer():
    return 'some_issuer'


@pytest.fixture
def secret():
    return 'not so secret secret'


@pytest.fixture
def token(namespace, identity, issuer):
    return module.JWTAuthToken.new(namespace, identity, issuer)


def test_repr(token):
    r = repr(token)
    l = locals()
    from uuid import UUID
    l.update({'JWTAuthToken': module.JWTAuthToken,
              'UUID': UUID, })
    t = eval(r, globals(), l)
    assert isinstance(t, module.JWTAuthToken)
    assert t.get_payload() == token.get_payload()


def test_default_issued_at(token):
    assert isinstance(token.iat, datetime.datetime)
    diff = abs(datetime.datetime.utcnow() - token.iat)
    # should have been created in the last second
    assert diff < datetime.timedelta(seconds=1)


def test_sub(token, namespace, identity):
    assert token.sub == '{!s}:{!s}'.format(namespace, identity)


def test_set_sub(token):
    new_ns = 'new_ns'
    new_id = 'new_id'
    token.sub = '{!s}:{!s}'.format(new_ns, new_id)
    assert token.namespace == new_ns
    assert token.identity == new_id


def test_set_iat_datetime(token):
    new_iat = datetime.datetime.utcnow()
    token.iat = new_iat
    assert token.iat == new_iat


def test_set_iat_millitime(token):
    new_iat = datetime.datetime.utcnow()
    millitime = calendar.timegm(new_iat.utctimetuple())
    token.iat = millitime
    # We lose microsecond precision when using timestamps
    assert abs(new_iat - token.iat) < datetime.timedelta(seconds=1)


def test_set_exp_datetime(token):
    new_exp = datetime.datetime.utcnow()
    token.exp = new_exp
    assert token.exp == new_exp


def test_set_exp_millitime(token):
    new_exp = datetime.datetime.utcnow()
    millitime = calendar.timegm(new_exp.utctimetuple())
    token.exp = millitime
    # We lose microsecond precision when using timestamps
    assert abs(new_exp - token.exp) < datetime.timedelta(seconds=1)


def test_set_exp_delta(token):
    new_iat = datetime.datetime.utcnow()
    delta = datetime.timedelta(seconds=90)
    token.iat = new_iat
    token.exp = delta
    assert token.exp == new_iat + delta


def test_change_iat(token):
    first = datetime.datetime.utcnow()
    exp = datetime.timedelta(seconds=5)
    nbf = datetime.timedelta(seconds=10)
    token.iat = first
    token.exp = exp
    token.nbf = nbf
    assert token.exp == first + exp
    assert token.nbf == first + nbf
    new = datetime.datetime.utcnow()
    token.iat = new
    assert token.exp == new + exp
    assert token.nbf == new + nbf


def test_get_payload(token):
    payload = token.get_payload()
    for claim in ['iss', 'iat', 'nbf', 'exp', 'sub']:
        assert getattr(token, claim) == payload[claim]


def test_load_payload():
    payload = {
        'iss': 'foo',
        'iat': 77000,
        'nbf': 78000,
        'exp': 79000,
        'sub': 'foo:bar',
        'jti': 'f8bfcdd5-aaec-4055-a3dc-d8f3c0dc63b6',
    }
    token = module.JWTAuthToken.from_payload(payload)
    for claim in ['iat', 'nbf', 'exp']:
        dt = datetime.datetime.utcfromtimestamp(payload[claim])
        assert abs(getattr(token, claim) - dt) < datetime.timedelta(seconds=1)
    for claim in ['sub', 'iss']:
        assert getattr(token, claim) == payload[claim]


def test_encode_decode_cycle(token, secret):
    token_value = token.jwt_encode(secret)
    token_copy = token.jwt_decode(token_value, secret)

    for claim in ['iat', 'nbf', 'exp']:
        diff = abs(getattr(token, claim) - getattr(token_copy, claim))
        assert diff < datetime.timedelta(seconds=1)
    for claim in ['sub', 'iss', 'jti']:
        assert getattr(token, claim) == getattr(token_copy, claim)
