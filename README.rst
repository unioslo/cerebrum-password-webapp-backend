====
pofh
====
*pofh* is a password change application, for use with Cerebrum and similar
Identity Management systems.


The application stack should look something like:

::

    +--------------------------+
    |         Frontend         |
    | (HTML/CSS/JS static app) |
    +--------------------------+
                |
    +-----------v--------------+
    |        Rev-proxy         |
    +-----------+--------------+
                |
    +-----------v--------------+
    |        Gunicorn          |
    +-----------+--------------+
                |
    +-----------v--------------+
    |         Backend          |
    |        (This app)        |
    +-----------+--------------+
                |
    +-----------v--------------+
    |          IdM             |
    +--------------------------+


Setup
=====

Install
-------
To run the installer, you'll need a new version of setuptools::

    $ pip install -U setuptools

To install the module using the setup script, you'll need to run::

    $ pip install .
    $ # OR
    $ python setup.py install


Run
---
To run the application using `gunicorn`_: ::

    $ gunicorn pofh:wsgi

To run the application using the builtin flask server: ::

    $ pofhd
    $ # OR
    $ python -m pofh


Run tests
---------
To run the tests using `tox`_, you'll need the `virtualenv`_ module in the
environment you'll be running from::

    $ pip intsall virtualenv

To run the tests, run::

    $ python setup.py test

This will install test dependencies, and run tests with ``tox``.

Alternatively, you can run: ::

    $ tox

If you already have all the tests installed.

If you already have `py.test`_ installed and don't want to run tests across
multiple python versions, you can run::

    $ py.test tests/


Build documentation
-------------------
To build the documentation, run: ::

    $ python setup.py build_sphinx

This will install ``pofh`` and all its dependencies in a temporary environment,
and build the documentation in the ``build/sphinx/html`` folder.

Alternatively, you can run: ::

    $ sphinx-build -b html -E docs/source <build-folder>

in an environment where ``pofh``, ``sphinx`` and ``sphinxcontrib-httpdomain`` have already been installed.


Try it out with Docker
----------------------
TODO: Update the docker files and write documentation.


Full setup
==========
TODO

Frontend
--------

The default frontend application is available `here`__.

__ `frontend`_



.. Links:
.. _tox: https://tox.readthedocs.io/en/latest/
.. _virtualenv: https://virtualenv.pypa.io/en/stable/
.. _py.test: http://doc.pytest.org/en/latest/
.. _backend: https://bitbucket.usit.uio.no/projects/CRB/repos/cerebrum-password-webapp-backend/browse
.. _frontend: https://bitbucket.usit.uio.no/projects/CRB/repos/cerebrum-password-webapp-frontend/browse
.. _gunicorn: http://gunicorn.org/
