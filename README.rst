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


Api
===
TODO


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

To run the tests::

    $ python setup.py test
    $ # OR
    $ tox

If you already have `py.test`_ installed and don't want to run tests across
multiple python versions, you can run::

    $ py.test tests/


Try it out with Docker
----------------------
TODO



Full setup
==========
TODO

Frontend
--------

The default frontend application is available `here`__.


__ `frontend`_


IdM adapter
-----------
TODO

statsd
------
TODO

logging
-------
TODO

session db
----------
TODO

.. Links:
.. _tox: https://tox.readthedocs.io/en/latest/
.. _virtualenv: https://virtualenv.pypa.io/en/stable/
.. _py.test: http://doc.pytest.org/en/latest/
.. _frontend: https://bitbucket.usit.uio.no/projects/CRB/repos/cerebrum-password-webapp-frontend/browse
.. _gunicorn: http://gunicorn.org/
