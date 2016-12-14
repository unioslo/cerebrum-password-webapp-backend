# -*- coding: utf-8 -*-

"""
Testing the web API.
"""
from __future__ import unicode_literals, absolute_import, print_function

import pytest
import pofh
import json


class DefaultConfig(pofh.DefaultConfig):
    """ New default config """
    JWT_SECRET_KEY = 'very secret key'
    JWT_LEEWAY = 5
    SMS_DISPATCHER = 'mock'
    REDIS_URL = 'mock://example.com'


@pytest.fixture
def app():

    oldconf = pofh.DefaultConfig
    pofh.DefaultConfig = DefaultConfig

    app = pofh.wsgi.create()
    app.testing = True,
    # TBD: Specify Cerebrum mock DB?
    yield app
    pofh.DefaultConfig = oldconf


@pytest.fixture
def client(app):
    return app.test_client()


def test_authenticate(client):
    """ Test the /authenticate end point. """

    # TODO: Test recaptcha?

    # Bad payload
    res = client.post("/authenticate",
                      data={'very': 'wrong'})
    assert res.status_code == 400
    res = json.loads(res.data)
    assert res['error'] == 'schema-error'
    # Invalid credentials
    res = client.post("/authenticate",
                      data={'username': 'foo', 'password': 'bad'})
    assert res.status_code == 401
    res = json.loads(res.data)
    assert res['error'] == 'invalid-creds'
    # Valid credentials
    res = client.post("/authenticate",
                      data={'username': 'foo', 'password': 'hunter2'})
    assert res.status_code == 200
    res = json.loads(res.data)
    assert res['token']


@pytest.fixture
def token(client):
    res = client.post("/authenticate",
                      data={'username': 'foo', 'password': 'hunter2'})
    res = json.loads(res.data)
    return 'JWT ' + res['token']


def test_password(client, token):
    """ Test the /password end point. """

    res = client.post('/password', headers={'Authorization': token},
                      data={'password': 'hunter3'})
    dta = json.loads(res.data)
    assert res.status_code == 400
    assert dta['error'] == 'invalid-new-password'

    res = client.post('/password', headers={'Authorization': token},
                      data={'passord': 'hunter3'})
    dta = json.loads(res.data)
    assert res.status_code == 400
    assert dta['error'] == 'schema-error'

    res = client.post('/password', headers={'Authorization': 'JWT missing'},
                      data={'passord': 'hunter3'})
    dta = json.loads(res.data)
    assert res.status_code == 403
    assert dta['error'] == 'forbidden'

    res = client.post('/password', headers={'Authorization': token},
                      data={'password': 'fido5'})
    assert res.status_code == 204


def test_smsidentify(client):
    """ Test the '/sms' route. """

    tests = [
        # identifier 42 does not exist
        (400, 'not-found-error', None,
         {'identifier_type': 'id',
          'identifier': '42',
          'username': 'foo',
          'mobile': '+4720000000'}),
        # username foobar does not exist
        (400, 'not-found-error', None,
         {'identifier_type': 'id',
          'identifier': '1',
          'username': 'foobar',
          'mobile': '+4720000000'}),
        # user bar is reserved
        (403, 'service-unavailable', None,
         {'identifier_type': 'id',
          'identifier': '1',
          'username': 'bar',
          'mobile': '+4720000000'}),
        # number and person mismatch
        (400, 'not-found-error', None,
         {'identifier_type': 'id',
          'identifier': '1',
          'username': 'foo',
          'mobile': '+4720000042'}),
        # invalid mobile number
        (400, 'invalid-mobile-number', 'unparseable-phone-number',
         {'identifier_type': 'id',
          'identifier': '1',
          'username': 'foo',
          'mobile': 'AAAAaaaaaaaaaaaaa'}),
        # all ok (no real SMS sent)
        (200, None, None,
         {'identifier_type': 'id',
          'identifier': '1',
          'username': 'foo',
          'mobile': '+4791000000'}),
    ]
    for status, error, reason, data in tests:
        res = client.post('/sms', data=data)
        assert res.status_code == status
        assert json.loads(res.data).get('error') == error
        assert json.loads(res.data).get('details', {}).get('reason') == reason


def test_smsverify(client):
    """ Test the '/sms/verify' endpoint. """

    res = client.post('/sms', data={'identifier_type': 'id',
                                    'identifier': '1',
                                    'username': 'foo',
                                    'mobile': '+4791000000'})
    token = 'JWT ' + json.loads(res.data)['token']
    res = client.post('/sms/verify', headers={'Authorization': token},
                      data={'nonce': 'test'})
    assert res.status_code == 401
    assert json.loads(res.data).get('error') == 'invalid-nonce'

    # TODO: override pofh.api.sms.check_nonce() to return True, and get pw token


def test_listusers(client):
    """ Test the '/list-usernames' endpint. """

    # Can list
    res = client.post('/list-usernames', data={'identifier_type': 'id',
                                               'identifier': '1'})
    assert res.status_code == 200
    users = set(json.loads(res.data).get('usernames', []))
    assert set(['foo', 'bar']) == users

    # Cannot list
    res = client.post('/list-usernames', data={'identifier_type': 'id',
                                               'identifier': '2'})
    assert res.status_code == 400
