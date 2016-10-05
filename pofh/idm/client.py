# encoding: utf-8
""" Abstract IdM clients. """
from __future__ import absolute_import, unicode_literals


class IdmClient(object):
    """ Idm Client specification

    This class specifies the neccessary functionality that is required from an
    IdM client.

    All clients should inherit from this class.
    """

    def get_person(self, idtype, idvalue):
        """ Look up person from a unique id.

        :param str idtype:
            Which identifier type to use for person lookup.
        :param str idvalue:
            Which identifier to use for person lookup.
        :return str:
            A unique person id, or `None` if no person is found.
        """
        raise NotImplementedError()

    def get_usernames(self, person_id):
        """ Fetch a list of usernames for a given person.

        :param str person_id:
            The person to look up users for.
        :return list:
            A list of username strings.
        """
        raise NotImplementedError()

    def get_mobile_numbers(self, person_id):
        """ Get valid phone numbers for a given person.

        :param str person_id: The person to look up users for.
        :return list: A list of phone number strings.
        """
        raise NotImplementedError()

    def can_use_sms_service(self, username):
        """ Check if a given user can use the sms password reset service.

        :param str username:
            Username of the user to check.
        :return bool:
            True if the user can use the sms service, False otherwise.
        """

        """ Check if service can be used by 'username'. """
        raise NotImplementedError()

    def verify_current_password(self, username, password):
        """ Check a current username and password (log in).

        :param str username: username
        :param str password: password
        :return bool:
            True if the username/password combination is valid, otherwise
            False.
        """
        raise NotImplementedError()

    def check_new_password(self, username, password):
        """ Check if a password is good enough for a given user.

        :param str username: Username for the new password.
        :param str password: The new password candidate to check.
        :return bool:
            True if the password is good enough for the user.
            TODO: Or structured data on error?
        """
        raise NotImplementedError()

    def set_new_password(self, username, password):
        """ Change the password for a given user.

        :param str username: The user to change password for.
        :param str password: The new password to set.
        :return bool: True if the password was changed.
        """
        raise NotImplementedError()


class MockClient(IdmClient):
    """ An IdM mock client implementation. """

    # dummy data map
    _default_db = {
        "persons": {
            "1": {
                "users": ["foo", "bar"],
                "mobile": ["12345678", "87654321", ],
            },
            "2": {
                "users": ["baz", "bat"],
                "mobile": ["12345678", "87654321", ],
            }
        },
        "users": {
            "foo": {
                "password": "hunter2",
                "can_use_sms": True,
            },
            "bar": {
                "password": "password1",
                "can_use_sms": False,
            },
            "baz": {
                "password": "fido5",
                "can_use_sms": True,
            },
            "bat": {
                "password": "secret",
                "can_use_sms": False,
            },
        }
    }

    def __init__(self, db=None):
        self._db = db or self._default_db

    _valid_passwords = ["hunter2", "password1", "fido5", "secret"]

    def get_person(self, idtype, idvalue):
        if idvalue in self._db["persons"]:
            return idvalue
        return None

    def get_usernames(self, person_id):
        try:
            return self._db["persons"][person_id]["users"]
        except KeyError:
            return []

    def get_mobile_numbers(self, person_id):
        try:
            return self._db["persons"][person_id]["mobile"]
        except KeyError:
            return []

    def can_use_sms_service(self, username):
        try:
            return self._db["users"][username]["can_use_sms"]
        except KeyError:
            return False

    def verify_current_password(self, username, password):
        try:
            return self._db["users"][username]["password"] == password
        except KeyError:
            return False

    def check_new_password(self, username, password):
        # TODO: Structured errors?
        return password in self._valid_passwords

    def set_new_password(self, username, password):
        if username in self._db["users"]:
            return True
        return False
