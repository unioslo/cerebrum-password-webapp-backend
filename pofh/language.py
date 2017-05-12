# encoding: utf-8
""" Language detection module.

This module contains a language listener that looks for language selectors in
requests, and stores the selected languages in the request context.

1. To set up the language listener, run ``init_app`` on the application.
2. To fetch the selected languages, call ``get_language`` or ``get_languages``.

Settings
--------
``DEFAULT_LANGUAGE`` (:py:class:`str`)
    Default language for the application.

"""
from __future__ import unicode_literals
import re
from language_tags import tags
from flask import request, g, current_app
from collections import OrderedDict


DEFAULT_LANGUAGE = 'en'
""" Default language (if not set in config). """


def parse_language_tag(tag_str):
    """ Parse and validate a language tag.

    :param str tag_str: A language tag to parse
    :raise ValueError: If the language tag is invalid.

    :rtype: language_tags.Tag.Tag
    :return: A language subtag object
    """
    tag_obj = tags.tag(tag_str)
    if tag_obj.valid:
        return tag_obj
    raise ValueError("Invalid language tag '{!s}'".format(tag_str))


# rfc2616, 'en-us;q=1.0', '*;q=0.5', 'en'...
_accept_language_item_re = re.compile(
    r"^(?P<l>(?:[A-Za-z]+(?:-[A-Za-z]+)?|\*))(?:;q=(?P<q>[01]?\.?[0-9]+))?$")


def parse_language_item(lang_item):
    """ Parse and validate a single Accept-Language-like value.

    >>> parse_language_item('en')
    ('en', 1.0)
    >>> parse_language_item('en-GB;q=0.8')
    ('en-GB', 0.8)

    :param str lang_item: The language value.

    :raise ValueError: If the item is invalid.
    :return tuple: A tuple with locale and 'quality factor'
    """
    match = _accept_language_item_re.match(lang_item.strip())
    if not match:
        raise ValueError("Invalid language value '{!s}'".format(lang_item))

    locale = match.group('l')
    q = float(match.group('q') or 1.0)
    if q > 1.0:
        raise ValueError("Invalid language value '{!s}'".format(lang_item))
    return (locale, q)


def parse_header(header_value):
    """ Parse the Accept-Language header value.

    >>> parse_header('da, en-gb;q=0.8, en;q=0.7')
    [('da', 1.0), ('en-gb', 0.8), ('en', 0.7)]

    :param str header_value: Value from the ``Accept-Language`` header

    :return list:
        Returns a list of ``(l, q)`` pairs, where ``l`` is a language tag
        string, and ``q`` is the float number 'quality factor' for that tag.
    """
    pairs = []
    for item in header_value.split(","):
        try:
            pairs.append(parse_language_item(item))
        except ValueError:
            continue
    return pairs


def get_query_lang(request, param='lang'):
    """ Get languages from a request query parameter.

    :param flask.Request request: A request to fetch language settings from.
    :param str param: The query parameter to fetch language settings from.

    :rtype: list
    :return:
        A list of language tags (:py:class:`language_tags.Tag.Tag`) given as
        query parameters.
    """
    languages = []
    if param in request.args:
        for lang in request.args.getlist(param):
            try:
                languages.append(parse_language_tag(lang))
            except ValueError:
                # invalid language
                continue
    return languages


def get_header_lang(request):
    """ Get languages from request headers.

    :param flask.Request request: A request to fetch language settings from.

    :rtype: list
    :return:
        A list of language tags (:py:class:`language_tags.Tag.Tag`) from the
        request headers, ordered by its ``q``-value, descending.
    """
    header_name = 'Accept-Language'
    languages = []

    if header_name in request.headers:
        for lang, q in sorted(
                parse_header(request.headers[header_name]),
                key=lambda t: t[1],
                reverse=True):
            try:
                languages.append(parse_language_tag(lang))
            except ValueError:
                # invalid language
                continue
    return languages


def get_default_language(app):
    """ Get default language from app config.

    :param flask.Flask app: Flask application
    :rtype: language_tags.Tag.Tag
    :return: A language subtag object
    """
    return parse_language_tag(app.config['DEFAULT_LANGUAGE'])


def autoset_context_language():
    """ Set the request context language from current request.

    Languages will be weighted by:

    1. language tags in query parameter 'lang'
    2. language tags in Accept-Language header
    3. language tag in DEFAULT_LANGUAGE

    """
    g._pofh_language = OrderedDict()

    def add_lang(tag):
        if str(tag) not in g._pofh_language:
            g._pofh_language[str(tag)] = tag

    for tag in get_query_lang(request):
        add_lang(tag)
        add_lang(tag.language)

    for tag in get_header_lang(request):
        add_lang(tag)
        add_lang(tag.language)

    default = get_default_language(current_app)
    add_lang(default)
    add_lang(default.language)

    g.log.debug("language-set", languages=(g._pofh_language.keys()))


def get_language():
    """ Fetches the preferred language from the request context.

    :rtype: str
    :return: The preferred language tag string.
    """
    return list(g._pofh_language.keys())[0]


def get_language_object():
    """ Fetches the preferred language from the request context.

    :rtype: language_tags.Tag.Tag
    :return: The preferred language tag.
    """
    return list(g._pofh_language.values())[0]


def get_languages():
    """ Fetches the preferred language list from the request context.

    :rtype: list
    :return: A list of language strings, ordered by preference
    """
    return list(g._pofh_language.keys())


def get_language_objects():
    """ Fetches the preferred language list from the request context.

    :rtype: list
    :return:
        A list of language objects (:py:class:`language_tags.Tag.Tag` or
        :py:class:`language_tags.Subtag.Subtag`), ordered by preference.
    """
    return list(g._pofh_language.values())


def init_app(app):
    """ Set up lanugage listener and default language. """
    app.config.setdefault('DEFAULT_LANGUAGE', DEFAULT_LANGUAGE)

    # make sure that the default language is a valid language tag
    parse_language_tag(app.config['DEFAULT_LANGUAGE'])
    app.before_request(autoset_context_language)
