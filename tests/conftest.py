#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" py.test test configuration and common fixtures. """
from __future__ import unicode_literals, absolute_import, print_function

import pytest
from collections import namedtuple


@pytest.fixture
def dummy_fixture():
    """ example fixture. """
    return "example"


@pytest.fixture
def config():
    """ Application config. """
    config_ = object()
    return config_


@pytest.fixture
def app(config):
    """ Flask application. """
    from flask import Flask
    app_ = Flask('unit-tests')
    app_.config.from_object(config)
    return app_


@pytest.fixture
def catcher():
    Recv = namedtuple('Recv', ('sender', 'args'))

    class _catcher(object):
        def __init__(self, signal):
            signal.connect(self)
            self.caught = []

        def __call__(self, sender, **kwargs):
            self.caught.append(Recv(sender, kwargs))
    return _catcher
