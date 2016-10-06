=============
pofh.template
=============

.. automodule:: pofh.template


Localized templates
-------------------
Use :py:func:`pofh.template.find_localized_template` to get a template for a given language:

::

    add_template('foo.en.txt', 'Hello, {{ name }}!')
    add_template('foo.no.txt', 'Hallo, {{ name }}!')
    tpl = find_localized_template('foo.txt', 'en')
    tpl.render(name='World')

.. autofunction:: pofh.template.find_localized_template


If :py:mod:`pofh.language` is initialized, use
:py:func:`get_localized_template` to get a localized template with the current
language settings:

::

    tpl = get_localized_template('foo.txt')
    tpl.render(name='World!')

.. autofunction:: pofh.template.get_localized_template


Use the context to insert localized values
------------------------------------------
The template context can be used to insert localized values. E.g.:

::

    add_template('foo.en.txt', 'Hello, {{ name }}!')
    add_template('foo.no.txt', 'Hallo, {{ name }}!')
    CONTEXT['en'] = {'name': 'World'}
    CONTEXT['no'] = {'name': 'Verden'}

    tpl = find_localized_template('foo.txt', 'no')
    ctx = build_template_context('no')
    tpl.render(**ctx)


If this module and the py:mod:`pofh.language` module is initialized, the
context is loaded from config (``TEMPLATE_CONTEXT``) and inserted into the flask
template environment:

::

    add_template('foo.en.txt', 'Hello, {{ name }}!')
    add_template('foo.no.txt', 'Hallo, {{ name }}!')
    tpl = get_localized_template('foo.txt')
    render_template(tpl)


