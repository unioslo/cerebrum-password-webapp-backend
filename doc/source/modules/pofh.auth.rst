=========
pofh.auth
=========
The pofh auth module consists of three main components:

1. A `request listener`_ that looks for and validates tokens in the
   ``Authorization`` header.
2. A request handler `wrapper`_ that checks if a valid token has been detected.
3. The `token`_ class itself that simplifies access to the token values.


Request listener
================
When initialized, this module will insert a request listener that looks for
supported authorization headers and validates them if supplied.


Validated tokens are stored in the ``flask.g`` context as
``flask.g.current_token``.


For any request, there are four outcomes:

1. No authorization header is given.

   The ``flask.g.current_token`` value is not populated (``None``)

2. An unsupported authorization scheme is given.

   E.g.: ``Authorization: Foo Bar``.

   The ``flask.g.current_Token`` value is not populated (``None``).

2. An unsigned or invalid JWT token is given.

   E.g.: ``Authorization: JWT gooblyboob``.

   The application returns a 403 HTTP response.

3. A signed and valid JWT token is given.

   E.g.: ``Authorization: JWT eyJhbGciOiJ…``

   `Token`_ is stored in ``flask.g.current_token``.


init_app
--------
To set up this behaviour, ``init_app`` needs to be called on the Flask
application.

.. autofunction:: pofh.auth.init_app



Wrapper
=======
To protect a path, its request handler needs to be decorated with the
``require_jwt`` wrapper. This wrapper inspects the ``flask.g.current_token`` to
decide if the token is authorized to use that path. Calling a request handler
that has been wrapped with ``require_jwt`` has three outcomes:

1. No ``flask.g.current_token`` has been set up.

   The application returns a 401 HTTP response with a ``WWW-Authenticate``
   header (challenge).

2. The ``flask.g.current_token`` does not match the required namespace.

   The application returns a 403 HTTP response.

3. The ``flask.g.current_token`` matches the required namespace.

   The application runs the request handler.


require_jwt
-----------

.. autofunction:: pofh.auth.require_jwt


Token
=====
TODO: The class

.. autoclass:: pofh.auth.token.JWTAuthToken
   :members:


Example
=======
Create and initialize an application: ::

    app = Flask('foo')
    init_app(app)


Require a token for namespace ``foo`` or ``bar`` on the path ``/hello``:

::

    @app.route('/hello')
    @require_jwt(namespaces=['foo', 'bar'])
    def hello():
      return "Hello {!s}!".format(g.current_token.sub)

Issue a token for the ``foo`` namespace on the path ``/auth/foo/<somename>``:

::

    @app.route('/auth/foo/<str:identity>')
    def auth_foo(identity):
      token = JWTAuthToken.new(namespace='foo', identity=identity)
      return jsonify(
        {'token': token.jwt_encode(app.config['JWT_SECRET_KEY'])})


Configuration
=============

.. automodule:: pofh.auth
