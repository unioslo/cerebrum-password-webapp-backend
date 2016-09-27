# encoding: utf-8
""" Identity Management system client.

Configuration
-------------

IDM_CLIENT (str)
    Chooses the IdM backend.
    Currently supported:
     - mock
     - crb-rest

"""
from __future__ import absolute_import, unicode_literals

from flask import g, current_app
from warnings import warn
from . import client


class DefaultClient(client.MockClient):
    def __init__(self, *args, **kwargs):
        warn(RuntimeWarning("No IdM client configured (IDM_CLIENT)"))
        super(DefaultClient, self).__init__(*args, **kwargs)


def get_idm_client():
    try:
        return g.idm_client
    except AttributeError:
        g.idm_client = build_idm_client(current_app.config)
        return g.idm_client


def build_idm_client(config):
    """ Fetch sms dispatcher from config. """
    # default
    if not getattr(config, 'IDM_CLIENT', None):
        return DefaultClient()

    # mock sms dispatcher
    if config['IDM_CLIENT'] == 'mock':
        return client.MockClient()

    # uio_gateway sms dispatcher
    if config['IDM_CLIENT'] == 'cerebrum-api':
        from . import cerebrum_api_v1
        return cerebrum_api_v1.from_config(config)

    raise ValueError(
        "Invalid IDM_CLIENT '{!s}'".format(config['IDM_CLIENT']))


def init_app(app):
    """ Use app configuration to set up session backend. """
    # TODO: Validate config?
    pass
