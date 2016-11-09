# encoding: utf-8

""" Test the Cerebrum client using request-mock. """
from __future__ import unicode_literals, absolute_import, print_function

import pytest
import json
import requests
import requests_mock
import pofh.idm.cerebrum_api_v1 as cerebrum


@pytest.fixture
def client():
    ret = cerebrum.from_config(dict(
        CEREBRUM_API_URL='mock://foo.bar',
        CEREBRUM_API_KEY='foobar',
        CEREBRUM_API_TIMEOUT=42,
        CEREBRUM_RESERVED_GROUPS=[],
        CEREBRUM_CONTACT_SETTINGS=[]))
    return ret


@pytest.fixture
def data(client):
    with requests_mock.mock() as m:
        yield m


def test_reserved_group(client):
    """ Test reserved group. """
    client.add_reserved_group('foobar')
    assert client.is_reserved_group('foobar') is True
    assert client.is_reserved_group('quux') is False


def test_valid_contacts(client):
    """ Test valid contacts. """
    client.add_contact_type(cerebrum.ContactType('test', 'phone'))
    assert client.is_valid_contact(
        {'source_system': 'test', 'type': 'phone'}) is True
    assert client.is_valid_contact(
        {'source_system': 'test', 'type': 'fax'}) is False


def test_get_person(client, data):
    """ Test get_person. """
    data.get(client._build_url(client._PERSON_LOOKUP),
             text=json.dumps({'results': [{'person_id': 42}]}))
    res = client.get_person('id', 42)
    assert res == 42


def test_can_use_sms_service(client, data):
    """ Test can_use_sms_service. """
    client.add_reserved_group('foobar')
    data.get(client._build_url(client._ACCOUNT_GROUPS.format(username='foo')),
             text=json.dumps({'groups': [{'name': 'foobar'}]}))
    assert client.can_use_sms_service('foo') is False
    data.get(client._build_url(client._ACCOUNT_GROUPS.format(username='bar')),
             text=json.dumps({'groups': []}))
    assert client.can_use_sms_service('bar') is True


def test_get_usernames(client, data):
    """ Test get_usernames. """

    data.get(client._build_url(client._PERSON_ACCOUNTS.format(pid=42)),
             text=json.dumps({'accounts': [{'id': 'foobar'}, {'id': 'quux'}]}))
    res = client.get_usernames(42)
    assert 'foobar' in res and 'quux' in res
    assert 'barfoo' not in res


def test_get_mobile_numbers(client, data):
    """ Test get_mobile_numebers. """

    data.get(client._build_url(client._PERSON_CONTACT.format(pid=42)),
             text=json.dumps({'contacts': [{'source_system': 'test', 'type':
                                            'cell', 'value': '+4720000000'},
                                           {'source_system': 'test', 'type':
                                            'fax', 'value': '+4721000000'}]}))
    client.add_contact_type(cerebrum.ContactType('test', 'cell'))
    res = client.get_mobile_numbers(42)
    assert res == ['+4720000000']


def test_verify_password(client, data):
    """ Test verify_current_password. """

    data.post(client._build_url(client._PASSW_VERIFY.format(username='foobar')),
              text=json.dumps({'verified': True}))
    data.post(client._build_url(client._PASSW_VERIFY.format(username='quux')),
              text=json.dumps({'verified': False}))
    assert client.verify_current_password('foobar', 'secret') is True
    assert client.verify_current_password('quux', 'secret') is False


def test_check_new_password(client, data):
    """ Check new password against Cerebrum tests. """
    data.post(client._build_url(client._PASSW_CHECK.format(username='foobar')),
              text=json.dumps({'passed': True}))
    data.post(client._build_url(client._PASSW_CHECK.format(username='quux')),
              text=json.dumps({'passed': False}))
    assert client.check_new_password('foobar', 'secret') is True
    assert client.check_new_password('quux', 'secret') is False


def test_set_new_password(client, data):
    """ Test setting new pw. """
    data.post(client._build_url(client._PASSW_SET.format(username='foobar')),
              text=json.dumps({'password': 'secret'}))
    data.post(client._build_url(client._PASSW_SET.format(username='quux')),
              status_code=400, reason='Bad password: not good enough')
    assert client.set_new_password('foobar', 'secret') is True
    with pytest.raises(requests.HTTPError):
        client.set_new_password('quux', 'secret')
