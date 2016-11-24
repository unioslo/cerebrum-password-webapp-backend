# -*- coding: utf-8 -*-

"""
Testing the Cerebrum mock client
"""
from __future__ import unicode_literals, absolute_import, print_function

import pytest
import pofh.idm as idm
import pofh.idm.client as client


# TODO: test get_idm_client() (needs app context)


@pytest.fixture
def mock():
    class App(object):
        pass
    app = App()
    app.config = {
        'IDM_CLIENT': 'mock',
    }
    return idm.build_idm_client(app)


def test_build_client(mock):
    assert isinstance(mock, client.MockClient)


def test_mock(mock):
    assert mock.get_person('id', '1') == '1'
    for uname in ('foo', 'bar'):
        assert uname in mock.get_usernames('1')
    assert '+4720000000' in mock.get_mobile_numbers('1', 'foo')
    assert mock.can_use_sms_service('1', 'foo') is True
    assert mock.can_use_sms_service('1', 'bar') is False
    assert mock.can_show_usernames('1') is True
    assert mock.can_show_usernames('2') is False
    assert mock.get_preferred_mobile_number('1') == '+4720000000'
    assert mock.get_preferred_mobile_number('3') == None
    assert mock.verify_current_password('foo', 'hunter2') is True
    assert mock.verify_current_password('bar', 'fido5') is False
    assert mock.check_new_password('foo', 'fido5') is True
    assert mock.check_new_password('foo', 'hunter3') is False
    assert mock.set_new_password('foo', 'fido5') is True
    assert mock.set_new_password('foobar', 'fido5') is False
