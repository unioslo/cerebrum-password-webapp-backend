#!/usr/bin/env python
# encoding: utf-8
""" Unit tests for pofh.language """

import pytest
from pofh import language
from language_tags.Tag import Tag


@pytest.mark.parametrize(
    "item,result",
    [
        ('da', ('da', 1.0)),
        ('en-gb;q=0.8', ('en-gb', 0.8)),
        ('en;q=0.7', ('en', 0.7)),
        ('*;q=0.5', ('*', 0.5)),
    ]
)
def test_parse_lang_items(item, result):
    assert language.parse_language_item(item) == result


@pytest.mark.parametrize(
    "item",
    [
        'foo-bar-baz',
        'en;',
        ';q=1.0',
        'en;q=foo',
        'en;1.0',
        'en;q=',
    ]
)
def test_parse_lang_error_invalid_lang(item):
    with pytest.raises(ValueError):
        language.parse_language_item(item)


def test_parse_accept_lang():
    result = language.parse_header('da, en-gb;q=0.8, en;q=0.7, *;q=0.5')
    assert result == [
        ('da', 1.0), ('en-gb', 0.8), ('en', 0.7), ('*', 0.5)]


def test_parse_accept_lang_omit_errors():
    result = language.parse_header('da, ;q=0.8, en;q=1.7, *;q=0.5')
    assert result == [('da', 1.0), ('*', 0.5)]


def test_parse_language_tag():
    result = language.parse_language_tag('en')
    result = language.parse_language_tag('zh-hans')
    assert isinstance(result, Tag)
    assert str(result) == 'zh-Hans'
    assert str(result.language) == 'zh'


def test_parse_lang_invalid():
    with pytest.raises(ValueError):
        language.parse_language_tag('foo-bar')
    with pytest.raises(ValueError):
        language.parse_language_tag(7)


# TODO: build app and parse request
