# -*- coding: utf-8 -*-

"""
Testing the web API.
"""
from __future__ import unicode_literals, absolute_import, print_function

import pytest
import pofh
import json

from pofh.api.authenticate import BasicAuthError


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
    with pytest.raises(BasicAuthError):
        client.post("/authenticate",
                    data={'username': 'foo', 'password': 'bad'})
    res = client.post("/authenticate",
                      data={'username': 'foo', 'passord': 'bad'})
    assert res.status_code == 400
    res = json.loads(res.data)
    assert res['error'] == 'schema-error'
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
    assert dta['error'] == 'weak-password'

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
        (400, 'not-found-error', {'identifier_type': 'id',
                                  'identifier': '42',
                                  'username': 'foo',
                                  'mobile': '+4720000000'}),
        # username foobar does not exist
        (400, 'not-found-error', {'identifier_type': 'id',
                                  'identifier': '1',
                                  'username': 'foobar',
                                  'mobile': '+4720000000'}),
        # user bar is reserved
        (403, 'reserved', {'identifier_type': 'id',
                           'identifier': '1',
                           'username': 'bar',
                           'mobile': '+4720000000'}),
        # number and person mismatch
        (400, 'invalid-mobile-number', {'identifier_type': 'id',
                                        'identifier': '1',
                                        'username': 'foo',
                                        'mobile': '+4720000042'}),
        # phonenumber lib does not accept number as valid
        (500, 'Unable to send SMS', {'identifier_type': 'id',
                                     'identifier': '1',
                                     'username': 'foo',
                                     'mobile': '+4720000000'}),
        # all ok (no real SMS sent)
        (200, None, {'identifier_type': 'id',
                     'identifier': '1',
                     'username': 'foo',
                     'mobile': '+4791000000'}),
    ]
    for status, error, data in tests:
        res = client.post('/sms', data=data)
        assert res.status_code == status
        # TODO: Fix identify() to return json?
        if status != 500:
            assert json.loads(res.data).get('error') == error
        else:
            assert res.data == error


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

    res = client.post('/list-usernames', data={'identifier_type': 'id',
                                               'identifier': '1'})
    assert res.status_code == 200
    users = set(json.loads(res.data).get('usernames', []))
    assert set(['foo', 'bar']) == users
