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

            # Minimum days since changed, e.g. 7, 14
            'delay': :py:class:`int`,
        }

CEREBRUM_FRESH_DAYS (:py:class:`int`)
    Used when considering if an entity is fresh. Maximum number of days since:
        - person creation
        - the date set in the account traits "new_student" and "sms_welcome"

CEREBRUM_AFF_GRACE_DAYS (:py:class:`int`)
    The number of days to allow using contact information from a source system
    a person has recently lost its affiliation from. This is to let people
    that have just quit or have an erroneous registration to use the service
    for a short time.

CEREBRUM_SOURCE_SYSTEM_PRIORITIES (:py:class:`list`)
    A weighted list of source systems. Used when trying to find phone numbers
    that can be used for SMS authentication. If this list contains source
    systems X and Y in that order, a person with an affiliation from X will
    only be able to use contact information from X for authentication.

CEREBRUM_PERSON_ID_TYPES (:py:class:`list`)
    A list of identifier types that are allowed when looking up a person.

CEREBRUM_FRESH_DAYS (:py:class:`int`)
    Used when considering if an entity is fresh. Maximum number of days since:
        - person creation
        - the date set in the account traits "new_student" and "sms_welcome"

CEREBRUM_ACCEPTED_QUARANTINES (:py:class:`list`)
    A list of quarantines an account can have and still be eligible for
    authentication by SMS.

"""
from __future__ import absolute_import, unicode_literals

import requests
import datetime
import dateutil.parser
from flask import g
from . import client, IdmClientException


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
    # Entity freshness
    client.set_fresh_days(config.get('CEREBRUM_FRESH_DAYS', 10))
    # Affiliation grace period
    client.set_affiliation_grace_days(
        config.get('CEREBRUM_AFF_GRACE_DAYS', 0))
    # Source system priorities
    client.set_source_system_priorities(
        config.get('CEREBRUM_SOURCE_SYSTEM_PRIORITIES', []))
    # Accepted quarantines
    for quarantine in config.get('CEREBRUM_ACCEPTED_QUARANTINES', []):
        client.add_accepted_quarantine(quarantine)
    # Person lookup ID types
    for id_type in config.get('CEREBRUM_PERSON_ID_TYPES', []):
        client.add_person_id_type(id_type)
    return client


class CerebrumClient(client.IdmClient):
    """ Client for communication with the Cerebrum REST API. """

    _PERSON_LOOKUP = '/search/persons/external-ids'
    _PERSON_INFO = '/persons/{pid:d}'
    _PERSON_AFFILIATIONS = '/persons/{pid:d}/affiliations'
    _PERSON_ACCOUNTS = '/persons/{pid:d}/accounts'
    _PERSON_CONTACTS = '/persons/{pid:d}/contacts'
    _PERSON_CONSENTS = '/persons/{pid:d}/consents'
    _ACCOUNT_INFO = '/accounts/{username!s}'
    _ACCOUNT_GROUPS = '/accounts/{username!s}/groups'
    _ACCOUNT_TRAITS = '/accounts/{username!s}/traits'
    _ACCOUNT_QUARANTINES = '/accounts/{username!s}/quarantines'
    _PASSWORD_VERIFY = '/accounts/{username!s}/password/verify'
    _PASSWORD_CHECK = '/accounts/{username!s}/password/check'
    _PASSWORD_SET = '/accounts/{username!s}/password'

    def __init__(self, baseurl, apikey, timeout):
        self._baseurl = baseurl
        self._apikey = apikey
        self._timeout = timeout
        self._reserved_groups = set()
        self._contact_types = list()
        self._cache = g.cerebrum_client = dict()
        self._fresh_days = 10
        self._aff_grace_days = 0
        self._source_system_priorities = list()
        self._accepted_quarantines = list()
        self._person_id_types = list()

    def set_fresh_days(self, days):
        """ Set the number of days an account or person
        is considered fresh. """
        self._fresh_days = days

    def set_affiliation_grace_days(self, days):
        """ Set the number of days a person affiliation is considered still
        valid after deletion. """
        self._aff_grace_days = days

    def set_source_system_priorities(self, priorities):
        """ Set the source system priorities. """
        self._source_system_priorities = priorities

    def add_accepted_quarantine(self, name):
        """ Add a quarantine that is acceptable when authenticating or using
        the SMS service. """
        self._accepted_quarantines.append(name)

    def add_person_id_type(self, name):
        """ Add a person ID lookup type. """
        self._person_id_types.append(name)

    def is_valid_person_id_type(self, name):
        """ Check if a person ID lookup type is supported. """
        return name in self._person_id_types

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

    def is_valid_contact(self, item, fresh_entity=False):
        """ Check if a contact result from Cerebrum is valid.

        :param dict item:
            A dictionary with keys ['source_system', 'type', 'last_modified']
        :return bool:
            True if the contact type is configured for use with the SMS
            service.
        """
        valid_type = [x for x in self._contact_types if item == x]
        if not valid_type:
            return False
        delay = valid_type.pop().delay
        if not delay or fresh_entity:
            return True
        last_modified = item.get('last_modified')
        if last_modified is None:
            return True
        last_modified = dateutil.parser.parse(last_modified)
        cutoff = datetime.datetime.now() - datetime.timedelta(days=delay)
        return last_modified < cutoff

    def _make_key(self, *args):
        return '-'.join(map(str, args))

    def _build_url(self, relurl):
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
            json=d or {},
            timeout=self._timeout
        )
        response.raise_for_status()
        # TODO: Handle error?
        return response

    def get_person(self, id_type, identifier):
        """ Look up person id from a unique id. """
        if not self.is_valid_person_id_type(id_type):
            return None
        data = self._do_get(
            self._PERSON_LOOKUP,
            q={
                'source_system': ['SAP', 'FS', ],
                'id_type': id_type,
                'external_id': identifier,
            }
        )
        results = data.json().get("results", [])
        if not results:
            return None
        return results.pop(0)["person_id"]

    def _get_person_info(self, person_id):
        """ Look up person information by person ID. """
        key = self._make_key('person', person_id)
        if key not in self._cache:
            data = self._do_get(
                self._PERSON_INFO.format(pid=person_id)
            )
            self._cache[key] = data.json()
        return self._cache[key]

    def _get_person_affiliations(self, person_id):
        """ Look up person affiliations by person ID. """
        key = self._make_key('person-affiliations', person_id)
        if key not in self._cache:
            data = self._do_get(
                self._PERSON_AFFILIATIONS.format(pid=person_id),
                q={'include_deleted': 'true'}
            )
            self._cache[key] = data.json().get('affiliations', [])
        return self._cache[key]

    def _get_account_info(self, username):
        """ Look up account information by username. """
        key = self._make_key('account', username)
        if key not in self._cache:
            data = self._do_get(
                self._ACCOUNT_INFO.format(username=username)
            )
            self._cache[key] = data.json()
        return self._cache[key]

    def _person_is_fresh(self, person_id):
        """ Check if a person has been created recently. """
        created_at_str = self._get_person_info(person_id).get('created_at')
        if not created_at_str:
            return False
        created_at = dateutil.parser.parse(created_at_str)
        cutoff = datetime.datetime.now() - datetime.timedelta(
            days=self._fresh_days)
        return created_at > cutoff

    def _account_is_active(self, username):
        """ Check if an account is considered active. """
        return self._get_account_info(username).get('active', False)

    def _account_is_fresh(self, username):
        """ Check if an account is considered fresh. """
        traits = [x for x in self._get_traits(username)
                  if x.get('trait') in ('new_student', 'sms_welcome') and
                  x.get('date')]
        for trait in traits:
            date = dateutil.parser.parse(trait.get('date'))
            cutoff = datetime.datetime.now() - datetime.timedelta(
                days=self._fresh_days)
            return date > cutoff
        return False

    def can_use_sms_service(self, person_id, username):
        """ Check if a given user can use the sms password reset service. """
        if not self._account_is_active(username):
            raise IdmClientException('inactive-account')
        if self._account_is_quarantined(username):
            raise IdmClientException('quarantined')
        if any(self.is_reserved_group(name) for name
               in self._get_group_memberships(username)):
            raise IdmClientException('reserved-by-group-membership')
        if self._account_is_self_reserved(username):
            raise IdmClientException('reserved-by-self')
        return True

    def can_authenticate(self, username):
        """ Check if a given user can authenticate with a password. """
        return (self._account_is_active(username) and
                not self._account_is_locked(username))

    def _get_traits(self, username):
        """ Fetch traits for a user. """
        key = self._make_key('traits', username)
        if key not in self._cache:
            data = self._do_get(
                self._ACCOUNT_TRAITS.format(username=username)
            )
            self._cache[key] = data.json().get('traits', [])
        return self._cache[key]

    def _get_consents(self, person_id):
        """ Fetch consents for a user. """
        key = self._make_key('consents', person_id)
        if key not in self._cache:
            data = self._do_get(
                self._PERSON_CONSENTS.format(pid=person_id)
            )
            self._cache[key] = data.json().get('consents', [])
        return self._cache[key]

    def _get_quarantine_status(self, username):
        """ Fetch quarantines for a user. """
        key = self._make_key('quarantine-status', username)
        if key not in self._cache:
            data = self._do_get(
                self._ACCOUNT_QUARANTINES.format(username=username)
            )
            self._cache[key] = data.json()
        return self._cache[key]

    def _get_person_contacts(self, person_id):
        """ Fetch contact information for a person. """
        key = self._make_key('person-contacts', person_id)
        if key not in self._cache:
            data = self._do_get(
                self._PERSON_CONTACTS.format(pid=person_id)
            )
            self._cache[key] = data.json().get('contacts', [])
        return self._cache[key]

    def _account_is_quarantined(self, username):
        """ Check if a user has any unacceptable quarantines. """
        quarantines = self._get_quarantine_status(username).get(
            'quarantines', [])
        return any(x.get('type') for x in quarantines
                   if x.get('type') not in self._accepted_quarantines)

    def _account_is_locked(self, username):
        """ Check if an account is considered locked. """
        return self._get_quarantine_status(username).get('locked')

    def _account_is_self_reserved(self, username):
        """ Check if a user has reserved itself from using the SMS based
        password recovery. """
        traits = self._get_traits(username=username)
        if any(trait.get('trait') == 'pasw_reserved' and
               trait.get('number', 0) == 1
               for trait in traits):
                return True
        return False

    def _get_group_memberships(self, username):
        """ Fetch a list of groups a given user is member of. """
        key = self._make_key('groups', username)
        if key not in self._cache:
            groups = self._do_get(
                self._ACCOUNT_GROUPS.format(username=username),
                q={
                    'indirect_memberships': True,
                }
            )
            memberships = [group['name'] for group in
                           groups.json().get('groups', [])]
            self._cache[key] = memberships
        return self._cache[key]

    def _has_publication_reservation(self, person_id):
        """ Check if a given person has opted out for publication. """
        return any(consent.get('name') == 'publication'
                   for consent in self._get_consents(person_id))

    def _affiliation_is_valid(self, aff):
        """ Check if an affiliation is considered valid, even if deleted. """
        deleted_date = aff.get('deleted_date')
        if deleted_date is None:
            return True
        deleted_date = dateutil.parser.parse(deleted_date)
        cutoff = datetime.datetime.now() - datetime.timedelta(
            days=self._aff_grace_days)
        return deleted_date > cutoff

    def _person_has_affiliation_from(self, person_id, source_system):
        """ Check if a person has a valid affiliation from a source system. """
        affiliations = self._get_person_affiliations(person_id)
        return any(source_system == x['source_system'] and
                   self._affiliation_is_valid(x)
                   for x in affiliations)

    def can_show_usernames(self, person_id):
        """ Can we show the usernames of this person? """
        return not self._has_publication_reservation(person_id=person_id)

    def get_usernames(self, person_id):
        """ Fetch a list of usernames for a given person_id. """
        key = self._make_key('usernames', person_id)
        if key not in self._cache:
            data = self._do_get(
                self._PERSON_ACCOUNTS.format(pid=person_id)
            )
            accounts = data.json().get('accounts', [])
            self._cache[key] = [item['id'] for item in accounts]
        return self._cache[key]

    def get_mobile_numbers(self, person_id, username=None):
        """ List valid phone numbers for a given person and username. """
        contacts = self._get_person_contacts(person_id)
        fresh = (self._account_is_fresh(username) or
                 self._person_is_fresh(person_id))
        if not self._source_system_priorities:
            return [item["value"] for item in contacts
                    if self.is_valid_contact(item, fresh_entity=fresh) and
                    self._person_has_affiliation_from(
                        person_id, item['source_system'])]
        for source_system in self._source_system_priorities:
            if not self._person_has_affiliation_from(person_id, source_system):
                continue
            return [item["value"] for item in contacts
                    if item['source_system'] == source_system and
                    self.is_valid_contact(item, fresh_entity=fresh)]

    def get_preferred_mobile_number(self, person_id):
        """ Fetch the phone number to use when sending usernames by SMS.
        The ordering of valid contact types affects the result, and freshness
        is ignored since this won't be used for authentication. """
        candidates = []
        for contact_type in self._contact_types:
            for item in self._get_person_contacts(person_id):
                if item == contact_type:
                    candidates.append(item["value"])
        return candidates.pop(0) if candidates else None

    def verify_current_password(self, username, password):
        """ Check if a set of credentials are valid for authentication. """
        result = self._do_post(
            self._PASSWORD_VERIFY.format(username=username),
            d={
                'password': password,
            }
        )
        return result.json().get('verified', False)

    def check_new_password(self, username, password):
        """ Check if a set of credentials validates against the password
        rules. """
        result = self._do_post(
            self._PASSWORD_CHECK.format(username=username),
            d={
                'password': password,
            }
        )
        return result.json().get('passed', False)

    def set_new_password(self, username, password):
        """ Change the password for a user. """
        result = self._do_post(
            self._PASSWORD_SET.format(username=username),
            d={
                'password': password,
            }
        )
        return bool(result.json().get('password', False))
