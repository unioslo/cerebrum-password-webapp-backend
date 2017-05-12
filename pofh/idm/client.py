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

    def can_show_usernames(self, person_id):
        """ Check if the usernames for a person can be shown.

        :param str person_id:
            The person to look up.
        :return bool:
            Show usernames?
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
    """ An IdM mock client implementation.

    Set ``data`` to a :py:class:`dict` to use custom mock data:

    ::

        {
            "persons": {
                "<id>": {
                    "users": ["<username>", ...],
                    "mobile": ["<number>", ...],
                },
                ...
            },
            "users": {
                "<username>": {
                    "password": "<password>",
                    "can_use_sms": (True | False),
                },
                ...
            }
        }

    """

    # dummy data map
    _default_db = {
        "persons": {
            "1": {
                "studentNumber": "111111",
                "users": ["foo", "bar"],
                "mobile": ["+4720000000", "+4720000001", "+4791000000"],
            },
            "2": {
                "studentNumber": "222222",
                "users": ["baz"],
                "mobile": ["+4720000002"],
                "can_show_usernames": False,
            }
        },
        "users": {
            "foo": {
                "password": "hunter2",
                "can_use_sms": True,
            },
            "bar": {
                "password": "hunter2",
                "can_use_sms": False,
            },
            "baz": {
                "password": "hunter2",
            }
        }
    }

    def __init__(self, data=None):
        self._db = {}
        if data is None:
            self.load_data(self._default_db)
        else:
            self.load_data(data)

    _valid_passwords = ["hunter2", "password1", "fido5", "secret",
                        "testtesttesttesttest"]

    def load_data(self, data):
        for name, info in data.get("users", {}).items():
            self._db.setdefault("users", {})[name] = dict()
            self._db["users"][name]["password"] = info.get("password", "")
            self._db["users"][name]["can_use_sms"] = info.get("can_use_sms",
                                                              False)
        for pid, info in data.get("persons", {}).items():
            self._db.setdefault("persons", {})[pid] = dict()
            for name in info.get("users", []):
                if name in self._db["users"]:
                    self._db["persons"][pid].setdefault("users",
                                                        []).append(name)
            for number in info.get("mobile", []):
                self._db["persons"][pid].setdefault("mobile",
                                                    []).append(number)
            self._db["persons"][pid]["can_show_usernames"] = info.get(
                "can_show_usernames", True)

    def get_person(self, idtype, idvalue):
        if idvalue in self._db["persons"]:
            return idvalue
        for pid, data in self._db["persons"].items():
            if data.get("studentNumber") == idvalue:
                return pid
        return None

    def get_usernames(self, person_id):
        try:
            return self._db["persons"][person_id]["users"]
        except KeyError:
            return []

    def get_mobile_numbers(self, person_id, username):
        try:
            return self._db["persons"][person_id]["mobile"]
        except KeyError:
            return []

    def get_preferred_mobile_number(self, person_id):
        try:
            return self._db["persons"][person_id]["mobile"][0]
        except KeyError:
            return None

    def can_show_usernames(self, person_id):
        try:
            return self._db["persons"][person_id]["can_show_usernames"]
        except KeyError:
            return True

    def can_use_sms_service(self, person_id, username):
        try:
            return self._db["users"][username]["can_use_sms"]
        except KeyError:
            return False

    def can_authenticate(self, username):
        try:
            return self._db["users"][username]["can_authenticate"]
        except KeyError:
            return True

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
