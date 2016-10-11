# encoding: utf-8
""" Basic templates.

Settings
--------
TEMPLATE_DIR (:py:class:`str`)
    Path to a directory with templates. Defaults to ``<flask instance
    path>/templates``.

TEMPLATE_CONTEXT (:py:class:`dict`)
    A dictinary of dictionaries. This defines a series of data available in the
    flask template context, per language.

    If you've set the default language to ``"en"``, and want the names
    ``{{from}}`` and ``{{limit}}`` available in the flask template environment,
    you would set this setting to: ::

        {
            'en': {'from': 'Foo University College', 'limit': 10},
            'nb': {'from': 'Høgskolen Foo', }
            'nn': {'from': 'Høgskulen Foo', }
        }


"""
from __future__ import print_function, unicode_literals

import os
from jinja2 import Template
from jinja2.exceptions import TemplateNotFound
from flask import current_app

from . import language


TEMPLATES = {}


def add_template(name, template):
    """ Adds a template to the localized template list. """
    if template and not isinstance(template, Template):
        template = Template(template)
    TEMPLATES[name] = template


def format_template_name(name, lang):
    """ Format localized template name

    >>> format_template_name('foo', 'en')
    foo.en
    >>> format_template_name('foo.txt', 'en')
    foo.en.txt
    >>> format_template_name('foo.bar.txt', 'en')
    foo.bar.en.txt

    :param str name: A template name
    :param language_tags.Subtag.Subtag lang: A language subtag

    :return str: A localized template name
    """
    base, ext = os.path.splitext(name)
    return "{base!s}.{lang!s}{ext!s}".format(
        base=base, lang=lang, ext=ext)


def find_localized_template(name, languages, env=None):
    """ Get localized template from common name.

    :param str name:
        The template name
    :param list languages:
        Accepted language strings.
    :param flask.templating.Environment env:
        Look up templates using this environment.

    :raise TemplateNotFound:
    :return Template:
    """
    # build template preference list
    candidates = []
    for lang in languages:
        candidates.append(format_template_name(name, lang))
    # default template
    candidates.append(name)

    # find template
    for name in candidates:
        # in inventory
        if isinstance(TEMPLATES.get(name), Template):
            return TEMPLATES[name]
        # in template env
        if env is not None:
            try:
                return env.get_template(name)
            except TemplateNotFound:
                continue

    raise TemplateNotFound(
        name,
        message="Cound not find template {!s} (names={!r})".format(
            name, candidates))


def get_localized_template(name):
    """ Get localized template from common name.

    :param str name: The template name

    Note: The template name should be indexed by calling ``add_template``.
    Note: This function depends on the request context.
    """
    return find_localized_template(name,
                                   language.get_languages(),
                                   env=current_app.jinja_env)


def _get_app_contexts(config):
    contexts = {}
    for lang, ctx in config['TEMPLATE_CONTEXT'].items():
        if lang and ctx:
            if not isinstance(ctx, dict):
                raise ValueError('Invalid TEMPLATE_CONTEXT[{!r}]'.format(lang))
            lang = language.parse_language_tag(lang)
            contexts[str(lang)] = ctx
    return contexts


def build_localized_context(config, languages):
    """ Assemble a context from one or more languages.

    :param list languages: A list of language strings, by priority.

    :return dict: The context
    """
    all_ctx = _get_app_contexts(config)
    context = {}
    for lang in reversed(languages):
        for key, value in all_ctx.get(lang, {}).items():
            context[key] = value
    return context


def get_localized_context():
    """ Get localized template context.

    Note: This function depends on the request context.
    """
    return build_localized_context(current_app.config,
                                   language.get_languages())


def init_app(app):
    """ Set up template settings. """
    # TODO: This depends on language.init_app, how can we make sure that it has
    # been set up?

    app.config.setdefault('TEMPLATE_DIR', os.path.join(app.instance_path,
                                                       'templates'))
    app.config.setdefault('TEMPLATE_CONTEXT', {})

    app.template_folder = app.config['TEMPLATE_DIR']
    # Make sure the TEMPLATE_CONTEXT setting is sane:
    _get_app_contexts(app.config)
    app.context_processor(get_localized_context)

    #   from flask import request, jsonify, render_template
    #   from .api.utils import get_request_data
    #
    #   @app.route('/template/<string:name>', methods=['POST', ])
    #   def render(name):
    #       tpl = get_localized_template(name)
    #       data = get_request_data(request)
    #       return jsonify({'document': render_template(tpl, **data)})
