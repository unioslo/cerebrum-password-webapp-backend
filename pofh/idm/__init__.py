# encoding: utf-8
""" Identity Management system client.

Configuration
-------------

IDM_CLIENT (:py:class:`str`)
    Chooses the IdM backend. Currently supported:
     - mock
     - cerebrum-api

IDM_MOCK_DATA (:py:class:`str`)
    Path to a json or yaml file with mock data. If the path is not absolute, it
    is assumed to be relative to the application instance path.

    Only used with the mock client.

"""
from __future__ import absolute_import, unicode_literals

import os
from flask import g, current_app
from warnings import warn
from . import client


# TODO: Re-write the clients themselves to be thread safe, intead of
# re-initializing them each request?


class IdmClientException(Exception):
    pass


def get_idm_client():
    """ Fetch an IdM client from the current app config.

    Requires an app context.
    """
    try:
        return g.idm_client
    except AttributeError:
        g.idm_client = build_idm_client(current_app)
        return g.idm_client


def build_idm_client(app):
    """ Fetch idm client from config.  """

    # mock sms dispatcher
    if app.config.get('IDM_CLIENT', 'mock') == 'mock':
        data = None
        if app.config.get('IDM_MOCK_DATA'):
            filename = app.config['IDM_MOCK_DATA']
            if not os.path.isabs(filename):
                filename = os.path.join(app.instance_path, filename)
            ext = os.path.splitext(filename)[1]
            if os.path.isfile(filename) and ext == '.json':
                import json
                loader = json.load
            elif os.path.isfile(filename) and ext in ('.yml', '.yaml'):
                import yaml
                loader = yaml.load
            else:
                raise RuntimeError(
                    "Unable to load mock data from '{!s}'".format(filename))
            with open(filename, 'r') as f:
                data = loader(f)

        return client.MockClient(data)

    # uio_gateway sms dispatcher
    if app.config['IDM_CLIENT'] == 'cerebrum-api':
        from . import cerebrum_api_v1
        return cerebrum_api_v1.from_config(app.config)

    raise ValueError(
        "Invalid IDM_CLIENT '{!s}'".format(app.config['IDM_CLIENT']))


def init_app(app):
    """ Use app configuration to verify idm client config. """
    if not app.config.get('IDM_CLIENT', None):
        warn(RuntimeWarning("No IdM client configured (IDM_CLIENT)"))
    with app.app_context():
        get_idm_client()
        # TODO: Test client?
