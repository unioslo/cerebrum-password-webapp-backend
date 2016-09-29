# encoding: utf-8
""" Identity Management system client.

Configuration
-------------

IDM_CLIENT (str)
    Chooses the IdM backend. Currently supported:
     - mock
     - cerebrum-api

"""
from __future__ import absolute_import, unicode_literals

from flask import g, current_app
from warnings import warn
from . import client


def get_idm_client():
    try:
        return g.idm_client
    except AttributeError:
        g.idm_client = build_idm_client(current_app.config)
        return g.idm_client


def build_idm_client(config):
    """ Fetch sms dispatcher from config. """

    # mock sms dispatcher
    if config.get('IDM_CLIENT', 'mock') == 'mock':
        return client.MockClient()

    # uio_gateway sms dispatcher
    if config['IDM_CLIENT'] == 'cerebrum-api':
        from . import cerebrum_api_v1
        return cerebrum_api_v1.from_config(config)

    raise ValueError(
        "Invalid IDM_CLIENT '{!s}'".format(config['IDM_CLIENT']))


def init_app(app):
    """ Use app configuration to set up session backend. """
    if not app.config.get('IDM_CLIENT', None):
        warn(RuntimeWarning("No IdM client configured (IDM_CLIENT)"))
    # TODO: Make sure we can get a client from current config?
