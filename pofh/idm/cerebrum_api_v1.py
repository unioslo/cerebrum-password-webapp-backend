# encoding: utf-8
""" REST client for the Cerebrum REST API.

Configuration
-------------

CEREBRUM_API_URL (:py:class:`str`)
    The base URL to the API (HTTP POST).

CEREBRUM_API_KEY (:py:class:`str`)
    API key for the Cerebrum API.

CEREBRUM_API_TIMEOUT (:py:class:`float`)
    Timeout, in seconds.

CEREBRUM_RESERVED_GROUPS (:py:class:`list`)
    A list of groups that disqualifies use of the SMS reset service. Any
    indirect member of any listed group will not be able to reset passwords
    using the SMS service.

CEREBRUM_CONTACT_SETTINGS (:py:class:`list`)
    A weighted list of contact types that can be used by the SMS reset service.
    Each item is a dict that contains the following values:

    ::

        {
            # Source system, e.g. 'SAP', 'FS'
            'system': :py:class:`str`,

            # Contact type, e.g. 'MOBILE', 'PRIVATEMOBILE'
            'type': :py:class:`str`,

            # Mininum days since changed, e.g. 7, 14
            'delay': :py:class:`int`,
        }

"""
from __future__ import absolute_import, unicode_literals

import requests
from . import client


class ContactType(object):

    def __init__(self, system, ctype, delay=None):
        self.system = system
        self.ctype = ctype
        self.delay = delay

    @classmethod
    def from_config(cls, item):
        return cls(
            str(item['system']),
            str(item['type']),
            delay=item.get('delay', None))

    def __eq__(self, other):
        if isinstance(other, ContactType):
            return (self.system == other.system and
                    self.ctype == other.ctype and
                    self.delay == other.delay)
        elif isinstance(other, dict):
            # TODO: Compare delay?
            return (self.system == other.get('source_system') and
                    self.ctype == other.get('type'))
        return False


def from_config(config):
    """ Initialize settings from a dict-like config. """
    client = CerebrumClient(
        config['CEREBRUM_API_URL'],
        config['CEREBRUM_API_KEY'],
        config['CEREBRUM_API_TIMEOUT']
    )
    # Reserved groups
    for group_name in config.get('CEREBRUM_RESERVED_GROUPS', []):
        client.add_reserved_group(group_name)
    # Contact types
    for contact_type in config.get('CEREBRUM_CONTACT_SETTINGS', []):
        client.add_contact_type(ContactType.from_config(contact_type))
    return client


class CerebrumClient(client.IdmClient):

    # TODO: Use hrefs from the API?
    _PERSON_LOOKUP = '/search/persons/external-ids'
    _PERSON_ACCOUNTS = '/persons/{pid:d}/accounts'
    _PERSON_CONTACT = '/persons/{pid:d}/contacts'
    _ACCOUNT_GROUPS = '/accounts/{username!s}/groups'
    _PASSW_VERIFY = '/accounts/{username!s}/password/verify'
    _PASSW_CHECK = '/accounts/{username!s}/password/check'
    _PASSW_SET = '/accounts/{username!s}/password'

    def __init__(self, baseurl, apikey, timeout):
        self._baseurl = baseurl
        self._apikey = apikey
        self._timeout = timeout
        self._reserved_groups = set()
        self._contact_types = list()

    def add_reserved_group(self, name):
        """ Add a reserved group. """
        self._reserved_groups.add(name)

    def is_reserved_group(self, name):
        """ Check if a group is a reserved group. """
        return name in self._reserved_groups

    def add_contact_type(self, contact_type):
        """ Add a contact type. """
        if not isinstance(contact_type, ContactType):
            raise ValueError(
                "Invalid contact type (was {!s}, "
                "must be {!r})".format(contact_type, ContactType))
        self._contact_types.append(contact_type)

    def is_valid_contact(self, item):
        """ Check if a contact result from Cerebrum is valid.

        :param dict item:
            A dictionary with keys ['source_system', 'type']
        :return bool:
            True if the contact type is configured for use with the SMS
            service.
        """
        return item in self._contact_types

    def _build_url(self, relurl):
        # TODO: Join better
        return self._baseurl + relurl

    def _build_headers(self, headers=None):
        h = {
            'X-API-Key': self._apikey,
        }
        if headers is not None:
            for header in headers:
                h[header] = headers[header]
        return h

    def _do_get(self, relurl, headers=None, q=None):
        """ Use a GET resource in the API.

        :param str relurl: A resource path relative to the baseurl.
        :param dict headers: A dict with extra headers.
        :param dict q: A dict with query parameters.

        :return requests.Response:
            A response from the API.

        :raise requests.exceptions.RequestException:
            If there was a problem completing the request.
        """
        response = requests.get(
            self._build_url(relurl),
            headers=self._build_headers(headers=headers),
            params=q or {},
            timeout=self._timeout
        )
        response.raise_for_status()
        # TODO: Handle error?
        return response

    def _do_post(self, relurl, headers=None, d=None):
        """ Use a POST resource in the API.

        :param str relurl: A resource path relative to the baseurl.
        :param dict headers: A dict with extra headers.
        :param dict d: A dict with parameters.

        :return requests.Response:
            A response from the API.

        :raise requests.exceptions.RequestException:
            If there was a problem completing the request.
        """

        response = requests.post(
            self._build_url(relurl),
            headers=self._build_headers(headers=headers),
            data=d or {},
            timeout=self._timeout
        )
        response.raise_for_status()
        # TODO: Handle error?
        return response

    def get_person(self, idtype, idvalue):
        """ Look up person id from a unique id. """
        data = self._do_get(
            self._PERSON_LOOKUP,
            q={
                'source_system': ['SAP', 'FS', ],
                'id_type': idtype,
                'external_id': idvalue,
            }
        )
        results = data.json.get("results", [])
        return results.pop(0)["person_id"]

    def can_use_sms_service(self, username):
        """ Check if a given user can use the sms password reset service. """
        groups = self._do_get(
            self._ACCOUNT_GROUPS.format(username=username),
            q={
                'indirect_memberships': True,
            }
        )
        memberships = [group['name'] for group in groups.json]
        return not any(self.is_reserved_group(name) for name in memberships)

    def get_usernames(self, person_id):
        """ Fetch a list of usernames for a given person_id. """
        data = self._do_get(
            self._PERSON_ACCOUNTS.format(pid=person_id)
        )
        accounts = data.json.get('accounts', [])
        # TODO: Use href?
        return [item['id'] for item in accounts]

    def get_mobile_numbers(self, person_id):
        """ List valid phone numbers for a given person. """
        data = self._do_get(
            self._PERSON_CONTACT.format(pid=person_id)
        )
        contacts = data.json.get('contacts', [])
        return [item["value"] for item in contacts
                if item in self._contact_types]

    def verify_current_password(self, username, password):
        result = self._do_post(
            self._PASSW_VERIFY.format(username=username),
            d={
                'password': password,
            }
        )
        return result.json.get('verified', False)

    def check_new_password(self, username, password):
        result = self._do_post(
            self._PASSW_VERIFY.format(username=username),
            d={
                'password': password,
            }
        )
        return result.json

    def set_new_password(self, username, password):
        raise NotImplementedError()
        result = self._do_post(
            self._PASSW_SET.format(username=username),
            d={
                'password': password,
            }
        )
        return result.json.get('verified', False)
