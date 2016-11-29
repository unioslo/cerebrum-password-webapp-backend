#!/usr/bin/env python
# encoding: utf-8
""" Simple command line client for the backend api.

This client is intended to be used for testing only, as it takes passwords as
regular command line arguments.

"""
from __future__ import print_function, unicode_literals
import requests
import contextlib
import httplib
import blinker

signal_request = blinker.Signal('request')
signal_response = blinker.Signal('response')


@contextlib.contextmanager
def patch_send():
    """ Patch HTTPConnection.send to issue signal. """
    def new_send(self, data):
        signal_request.send(self, request=data)
        return old_send(self, data)
    old_send = httplib.HTTPConnection.send
    httplib.HTTPConnection.send = new_send
    yield
    httplib.HTTPConnection.send = old_send


def block_format(strblock, prefix="", header="", indent=0):
    """ Indent and prefix lines of text. """
    def fmt_line(line):
        return '{!s} {!s} {!s}'.format(' ' * indent, prefix, line)
    def fmt_header(line):
        return "{!s}{!s}\n".format(' ' * indent, line) if line else ''
    return "{!s}{!s}\n".format(
        fmt_header(header),
        "\n".join(fmt_line(line) for line in strblock.split("\n")))


def response_str(response):
    """ Turn a requests.Response into raw response string. """
    return "{r.status_code:d} {r.reason!s}\n{headers!s}\n\n{r.content!s}".format(
        r=response,
        headers="\n".join(("{!s}: {!s}".format(h, v)
                          for h, v in response.headers.items())))


class PofhClient(object):
    """ Simple client for the backend. """

    BASEURL = 'http://localhost:5000'
    """ URL to the API. """

    ACCEPT_LANG = 'nb,nn;q=0.8,en;q=0.5'
    """ Accept-Language header value. """

    AUTH_SCHEME = 'JWT'
    """ Auth scheme for the Authorization header. """

    USE_JSON = True
    """ Use JSON in request body params. """

    RECAPTCHA_DUMMY_VALUE = 'foo'

    def __init__(self, use_json=USE_JSON, baseurl=BASEURL):
        self.session = requests.Session()
        self.baseurl = baseurl
        self.use_json = use_json

    def __call__(self, prepared):
        """ Send a prepared request. """
        with patch_send():
            response = self.session.send(prepared)
        signal_response.send(self, response=response_str(response))
        response.raise_for_status()
        return response

    def _build_request(self, method, relpath, data=None, token=None):
        """ Build generic request. """
        headers = {}
        params = {}
        if self.ACCEPT_LANG:
            headers['Accept-Language'] = self.ACCEPT_LANG
        if token is not None:
            headers['Authorization'] = '{!s} {!s}'.format(self.AUTH_SCHEME, token)
        for k, v in (data or {}).items():
            params[k] = v
        r = requests.Request(
            method=method,
            url='{}{}'.format(self.baseurl, relpath),
            headers=headers,
            params=params if method == 'GET' else None,
            data=params if method != 'GET' and not self.use_json else None,
            json=params if method != 'GET' and self.use_json else None
        )
        return r.prepare()

    def list_usernames(self, idtype, idvalue):
        """ /list-usernames -> list of usernames"""
        request = self._build_request(
            'POST',
            '/list-usernames',
            data={
                "g-recaptcha-response": self.RECAPTCHA_DUMMY_VALUE,
                "identifier_type": idtype,
                "identifier": idvalue,
            }
        )
        response = self(request).json()
        return response['usernames']

    def basic_auth(self, username, password):
        """ /authenticate -> tuple with href,token. """
        request = self._build_request(
            'POST',
            '/authenticate',
            data={
                "g-recaptcha-response": self.RECAPTCHA_DUMMY_VALUE,
                "username": username,
                "password": password
            }
        )
        response = self(request).json()
        return response['href'], response['token']

    def sms_person_auth(self, idtype, idvalue, username, mobile):
        """" /sms -> tuple with href,token. """
        request = self._build_request(
            'POST',
            '/sms',
            data={
                "g-recaptcha-response": self.RECAPTCHA_DUMMY_VALUE,
                'identifier_type': idtype,
                'identifier': idvalue,
                'username': username,
                'mobile': mobile,
            }
        )
        response = self(request).json()
        return response['href'], response['token']

    def sms_nonce_auth(self, token, nonce):
        """ /sms/verify -> href,token """
        request = self._build_request(
            'POST',
            '/sms/verify',
            data={
                'nonce': nonce,
            },
            token=token
        )
        response = self(request).json()
        return response['href'], response['token']

    def change_password(self, token, new_password):
        """ /password -> Null. """
        request = self._build_request(
            'POST',
            '/password',
            data={
                "password": new_password,
            },
            token=token
        )
        self(request)


def scenario_username(args):
    client = PofhClient(baseurl=args.base_url)

    print("List usernames")
    usernames = client.list_usernames(args.id_type, args.id_value)
    print("  Got usernames: {!s}".format(usernames))


def scenario_password(args):
    client = PofhClient(baseurl=args.base_url)

    print("Authenticate with username and password")
    href, token = client.basic_auth(args.username, args.oldpass)
    print("  Got token for {!s}{!s} ({!s})".format(client.baseurl, href, token))

    print("Change password")
    client.change_password(token, args.newpass)
    print("  Success!")


def scenario_sms(args):
    client = PofhClient(baseurl=args.base_url)

    print("Authenticate with person details")
    href, token = client.sms_person_auth(
        args.id_type, args.id_value,
        args.username, args.mobile
    )
    print("  Got token for {!s}{!s} ({!s})".format(client.baseurl, href, token))

    nonce = raw_input("Nonce: ")

    print("Verify nonce ({!s})".format(nonce))
    href2, token2 = client.sms_nonce_auth(token, nonce)
    print("  Got token for {!s}{!s} ({!s})".format(client.baseurl, href2, token2))

    print("Change password")
    client.change_password(token2, args.newpass)
    print("  Success!")


def main(args=None):
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        default=False,
                        help="Print requests and responses")
    parser.add_argument('-u', '--base-url',
                        default=PofhClient.BASEURL,
                        help='Base url to the api (%(default)s).')

    commands = parser.add_subparsers(help='Scenarios')

    # List usernames
    list_usernames = commands.add_parser('list')
    list_usernames.add_argument('-t', '--id-type',
                                default='fnr',
                                metavar='id-type')
    list_usernames.add_argument('id_value',
                                metavar='person-id')
    list_usernames.set_defaults(command=scenario_username)

    # Change password using usename and password
    basic_auth = commands.add_parser('password')
    basic_auth.add_argument('username')
    basic_auth.add_argument('oldpass')
    basic_auth.add_argument('newpass')
    basic_auth.set_defaults(command=scenario_password)

    # Change password using nonce
    sms_auth = commands.add_parser('sms')
    sms_auth.add_argument('-t', '--id-type',
                          default='fnr',
                          metavar='id-type')
    sms_auth.add_argument('id_value',
                          metavar='person-id')
    sms_auth.add_argument('username')
    sms_auth.add_argument('mobile')
    sms_auth.add_argument('newpass')
    sms_auth.set_defaults(command=scenario_sms)

    args = parser.parse_args(args)

    if args.verbose:
        @signal_request.connect
        def print_request(sender, request=''):
            print(block_format(request, prefix='>', header='Request', indent=4))

        @signal_response.connect
        def print_response(sender, response=''):
            print(block_format(response, prefix='<', header='Response', indent=4))

    args.command(args)


if __name__ == '__main__':
    raise SystemExit(main())
