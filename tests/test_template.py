#!/usr/bin/env python
# encoding: utf-8
""" Unit tests for pofh.template """

import pytest
from jinja2 import Template
from pofh import template as module


@pytest.fixture
def template():
    """ The template module. """
    # Reset module constants
    module.TEMPLATES = {}
    return module


def test_format_template_name(template):
    fmt = template.format_template_name
    assert fmt('foo', 'en') == 'foo.en'
    assert fmt('foo.txt', 'en') == 'foo.en.txt'
    assert fmt('foo.bar.txt', 'en') == 'foo.bar.en.txt'


def test_add_template_none(template):
    template.add_template('foo', None)
    assert 'foo' in template.TEMPLATES
    assert template.TEMPLATES['foo'] is None


def test_add_template_str(template):
    template.add_template('foo', 'bar')
    assert 'foo' in template.TEMPLATES
    assert isinstance(template.TEMPLATES['foo'], Template)
    assert template.TEMPLATES['foo'].render() == 'bar'


def test_add_template(template):
    template.add_template('foo', Template('bar'))
    assert 'foo' in template.TEMPLATES
    assert isinstance(template.TEMPLATES['foo'], Template)
    assert template.TEMPLATES['foo'].render() == 'bar'


def test_build_template_ctx(template):
    config = {'TEMPLATE_CONTEXT': {}}
    config['TEMPLATE_CONTEXT']['en'] = {'a': 'foo', 'b': 'bar', }
    config['TEMPLATE_CONTEXT']['no'] = {'a': 'baz', }

    ctx = template.build_localized_context(config, ['en'])
    assert len(ctx) == 2
    assert ctx['a'] == 'foo'
    assert ctx['b'] == 'bar'
    ctx = template.build_localized_context(config, ['no'])
    assert len(ctx) == 1
    assert ctx['a'] == 'baz'
    ctx = template.build_localized_context(config, ['no', 'en'])
    assert len(ctx) == 2
    assert ctx['a'] == 'baz'
    assert ctx['b'] == 'bar'
    ctx = template.build_localized_context(config, ['en', 'no'])
    assert len(ctx) == 2
    assert ctx['a'] == 'foo'
    assert ctx['b'] == 'bar'


# TODO: find_localized_template
# build template dir (fixture)
# build app with template dir
# write templates
