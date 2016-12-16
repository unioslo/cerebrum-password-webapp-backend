# encoding: utf-8

""" Test the Cerebrum client using request-mock. """
from __future__ import unicode_literals, absolute_import, print_function

import pytest
import json
import requests
import requests_mock
import datetime
import pofh.idm.cerebrum_api_v1 as cerebrum
from pofh.idm import IdmClientException


@pytest.fixture()
def client(app):
    with app.app_context():
        ret = cerebrum.from_config(dict(
            CEREBRUM_API_URL='mock://foo.bar',
            CEREBRUM_API_KEY='foobar',
            CEREBRUM_API_TIMEOUT=42,
            CEREBRUM_RESERVED_GROUPS=[],
            CEREBRUM_CONTACT_SETTINGS=[],
            CEREBRUM_FRESH_DAYS=10,
            CEREBRUM_AFF_GRACE_DAYS=7))
        yield ret


@pytest.fixture
def data(client):
    with requests_mock.mock() as m:
        yield m


def test_reserved_group(client):
    """ Test reserved group. """
    client.add_reserved_group('foobar')
    assert client.is_reserved_group('foobar') is True
    assert client.is_reserved_group('quux') is False


def test_contact_type(client):
    phone_no_delay = cerebrum.ContactType('test', 'phone')
    phone_with_delay = cerebrum.ContactType('test', 'phone', 7)
    phone_with_delay_from_config = cerebrum.ContactType.from_config({
        'system': 'test',
        'type': 'phone',
        'delay': 7})
    assert phone_no_delay != phone_with_delay
    assert phone_with_delay == phone_with_delay_from_config
    phone_from_cerebrum = {'source_system': 'test', 'type': 'phone'}
    assert phone_with_delay == phone_from_cerebrum


def test_is_valid_contact(client):
    """ Test contact validation. """
    # No delay
    client.add_contact_type(cerebrum.ContactType('test', 'phone'))
    assert client.is_valid_contact(
        {'source_system': 'test', 'type': 'phone'}) is True
    assert client.is_valid_contact(
        {'source_system': 'test', 'type': 'fax'}) is False
    # Delay
    client.add_contact_type(cerebrum.ContactType('test', 'mobile', delay=7))
    three_days_ago = datetime.datetime.now() - datetime.timedelta(days=3)
    twenty_days_ago = datetime.datetime.now() - datetime.timedelta(days=20)
    assert client.is_valid_contact(
        {'source_system': 'test',
         'type': 'mobile',
         'last_modified': twenty_days_ago.isoformat()}) is True
    assert client.is_valid_contact(
        {'source_system': 'test',
         'type': 'mobile',
         'last_modified': three_days_ago.isoformat()}) is False
    # Delay with fresh entity
    assert client.is_valid_contact(
        {'source_system': 'test',
         'type': 'mobile',
         'last_modified': three_days_ago.isoformat()},
        fresh_entity=True) is True


def test_get_person(client, data):
    """ Test get_person. """
    client.add_person_id_type('id')
    data.get(client._build_url(client._PERSON_LOOKUP),
             text=json.dumps({'external_ids': [{'person_id': 42}]}))
    assert client.get_person('id', 42) == 42
    assert client.get_person('invalidType', 42) == None
    data.get(client._build_url(client._PERSON_LOOKUP),
             text=json.dumps({'external_ids': []}))
    assert client.get_person('id', 123) == None


def test_account_is_quarantined(client, data):
    """ Test _account_is_quarantined. """
    client.add_accepted_quarantine('okay')
    data.get(
        client._build_url(client._ACCOUNT_QUARANTINES.format(username='foo')),
        text=json.dumps({'quarantines': [{'type': 'okay'}]}))
    data.get(
        client._build_url(client._ACCOUNT_QUARANTINES.format(username='bar')),
        text=json.dumps({'quarantines': [{'type': 'nope'}]}))
    assert client._account_is_quarantined('foo') is False
    assert client._account_is_quarantined('bar') is True


def test_can_authenticate(client, data):
    """ Test can_authenticate """
    for username in ('foo', 'bar'):
        data.get(
            client._build_url(client._ACCOUNT_INFO.format(username=username)),
            text=json.dumps({'active': True}))
    data.get(
        client._build_url(client._ACCOUNT_QUARANTINES.format(username='foo')),
        text=json.dumps({'locked': False, 'quarantines': []}))
    data.get(
        client._build_url(client._ACCOUNT_QUARANTINES.format(username='bar')),
        text=json.dumps({'locked': True, 'quarantines': []}))
    assert client.can_authenticate('foo') is True
    assert client.can_authenticate('bar') is False


def test_can_use_sms_service(client, data):
    """ Test can_use_sms_service. """
    for x in ('foo', 'bar'):
        # No quarantines
        data.get(
            client._build_url(client._ACCOUNT_QUARANTINES.format(username=x)),
            text=json.dumps({'quarantines': []}))
        # No traits
        data.get(
            client._build_url(client._ACCOUNT_TRAITS.format(username=x)),
            text=json.dumps({'traits': []}))
        # Accounts are active
        data.get(
            client._build_url(client._ACCOUNT_INFO.format(username=x)),
            text=json.dumps({'active': True}))

    # Deleted or expired account
    with pytest.raises(IdmClientException) as exc:
        data.get(
            client._build_url(client._ACCOUNT_INFO.format(username='batman')),
            text=json.dumps({'active': False}))
        client.can_use_sms_service(1, 'batman')
    assert str(exc.value) == 'inactive-account'

    # Reserved via group
    client.add_reserved_group('foobar')
    with pytest.raises(IdmClientException) as exc:
        data.get(
            client._build_url(client._ACCOUNT_GROUPS.format(username='foo')),
            text=json.dumps({'groups': [{'name': 'foobar'}]}))
        client.can_use_sms_service(1, 'foo')
    assert str(exc.value) == 'reserved-by-group-membership'

    # No groups
    data.get(client._build_url(client._ACCOUNT_GROUPS.format(username='bar')),
             text=json.dumps({'groups': []}))

    assert client.can_use_sms_service(1, 'bar') is True

    # Self-reservation via trait
    with pytest.raises(IdmClientException) as exc:
        data.get(
            client._build_url(client._ACCOUNT_TRAITS.format(username='bar')),
            text=json.dumps({'traits': [{'trait': 'pasw_reserved',
                                         'number': 1}]}))
        del client._cache['traits-bar']
        client.can_use_sms_service(1, 'bar')
    assert str(exc.value) == 'reserved-by-self'

    # Reserved for being a sysadm account
    with pytest.raises(IdmClientException) as exc:
        data.get(
            client._build_url(client._ACCOUNT_TRAITS.format(username='bar')),
            text=json.dumps({'traits': [{'trait': 'sysadm_account'}]}))
        del client._cache['traits-bar']
        client.can_use_sms_service(1, 'bar')
    assert str(exc.value) == 'reserved-sysadm-account'

    # Unacceptable quarantine
    data.get(
        client._build_url(client._ACCOUNT_QUARANTINES.format(username='bar')),
        text=json.dumps({'quarantines': [{'type': 'bad-manners'}]}))
    with pytest.raises(IdmClientException) as exc:
        del client._cache['quarantine-status-bar']
        client.can_use_sms_service(1, 'bar')
    assert str(exc.value) == 'quarantined'


def test_can_show_usernames(client, data):
    data.get(client._build_url(client._PERSON_CONSENTS.format(pid=1)),
             text=json.dumps({'consents': []}))
    assert client.can_show_usernames(person_id=1) is True
    data.get(client._build_url(client._PERSON_CONSENTS.format(pid=2)),
             text=json.dumps({'consents': [{'name': 'publication'}]}))
    assert client.can_show_usernames(person_id=2) is False


def test_get_usernames(client, data):
    """ Test get_usernames. """
    data.get(client._build_url(client._PERSON_ACCOUNTS.format(pid=42)),
             text=json.dumps({'accounts': [{'id': 'foobar'}, {'id': 'quux'}]}))
    res = client.get_usernames(42)
    assert 'foobar' in res and 'quux' in res
    assert 'barfoo' not in res


def test_get_mobile_numbers(client, data):
    """ Test getting mobile numbers while considering account and person
    freshness, affilation grace period and source system priorities. """
    # No traits
    data.get(client._build_url(client._ACCOUNT_TRAITS.format(username='foo')),
             text=json.dumps({'traits': []}))
    # Active account
    data.get(
        client._build_url(client._ACCOUNT_INFO.format(username='foo')),
        text=json.dumps({'active': True}))

    # Fresh person
    data.get(
        client._build_url(client._PERSON_INFO.format(pid=1)),
        text=json.dumps({'created_at': datetime.datetime.now().isoformat()}))

    # Valid affilition from source system 'test'
    # Recently deleted affilition from source system 'foobar'
    # Long since deleted affilition from source system 'nope'
    three_days_ago = datetime.datetime.now() - datetime.timedelta(days=3)
    one_year_ago = datetime.datetime.now() - datetime.timedelta(days=365)
    data.get(
        client._build_url(client._PERSON_AFFILIATIONS.format(pid=1)),
        text=json.dumps({'affiliations': [
            {'source_system': 'test', 'deleted_date': None},
            {'source_system': 'foobar',
             'deleted_date': three_days_ago.isoformat()},
            {'source_system': 'nope',
             'deleted_date': one_year_ago.isoformat()},
            ]}))

    data.get(client._build_url(client._PERSON_CONTACTS.format(pid=1)),
             text=json.dumps({'contacts': [
                {'source_system': 'test',
                 'type': 'cell',
                 'value': '+4720000000'},
                {'source_system': 'test',
                 'type': 'fax',
                 'value': '+4721000000'},
                {'source_system': 'foobar',
                 'type': 'cell',
                 'value': '+4721000111'},
                {'source_system': 'nope',
                 'type': 'cell',
                 'value': '+4721000222'}]}))
    client.add_contact_type(cerebrum.ContactType('test', 'cell'))
    client.add_contact_type(cerebrum.ContactType('foobar', 'cell'))
    client.add_contact_type(cerebrum.ContactType('nope', 'cell'))
    res = client.get_mobile_numbers(person_id=1, username='foo')
    assert res == ['+4720000000', '+4721000111']

    # Source system priorities
    client.set_source_system_priorities(['test', 'foobar'])
    res = client.get_mobile_numbers(person_id=1, username='foo')
    assert res == ['+4720000000']
    client.set_source_system_priorities(['foobar', 'test'])
    res = client.get_mobile_numbers(person_id=1, username='foo')
    assert res == ['+4721000111']
    client.set_source_system_priorities([])

    # Fresh account
    del client._cache['traits-foo']
    data.get(client._build_url(client._ACCOUNT_TRAITS.format(username='foo')),
             text=json.dumps({'traits': [
                {'trait': 'new_student',
                 'date': three_days_ago.isoformat()}]}))
    res = client.get_mobile_numbers(person_id=1, username='foo')
    assert res == ['+4720000000', '+4721000111']


def test_get_preferred_mobile_number(client, data):
    client.add_contact_type(cerebrum.ContactType('test', 'superior-phone'))
    client.add_contact_type(cerebrum.ContactType('test', 'lesser-phone'))
    data.get(client._build_url(client._PERSON_CONTACTS.format(pid=1)),
             text=json.dumps({'contacts': [
                {'source_system': 'test',
                 'type': 'lesser-phone',
                 'value': '+4720000000'},
                {'source_system': 'test',
                 'type': 'superior-phone',
                 'value': '+4721000000'}]}))
    data.get(client._build_url(client._PERSON_CONTACTS.format(pid=3)),
             text=json.dumps({'contacts': []}))
    assert client.get_preferred_mobile_number(1) == '+4721000000'
    assert client.get_preferred_mobile_number(3) == None


def test_verify_password(client, data):
    """ Test verify_current_password. """
    data.post(
        client._build_url(client._PASSWORD_VERIFY.format(username='one')),
        text=json.dumps({'verified': True}))
    data.post(
        client._build_url(client._PASSWORD_VERIFY.format(username='two')),
        text=json.dumps({'verified': False}))
    assert client.verify_current_password('one', 'secret') is True
    assert client.verify_current_password('two', 'secret') is False


def test_check_new_password(client, data):
    """ Check new password against Cerebrum tests. """
    data.post(
        client._build_url(client._PASSWORD_CHECK.format(username='foobar')),
        text=json.dumps({'passed': True}))
    data.post(
        client._build_url(client._PASSWORD_CHECK.format(username='quux')),
        text=json.dumps({'passed': False}))
    assert client.check_new_password('foobar', 'secret') is True
    assert client.check_new_password('quux', 'secret') is False


def test_set_new_password(client, data):
    """ Test setting new pw. """
    data.post(
        client._build_url(client._PASSWORD_SET.format(username='foobar')),
        text=json.dumps({'password': 'secret'}))
    data.post(
        client._build_url(client._PASSWORD_SET.format(username='quux')),
        status_code=400, reason='Bad password: not good enough')
    assert client.set_new_password('foobar', 'secret') is True
    with pytest.raises(requests.HTTPError):
        client.set_new_password('quux', 'secret')
