# encoding: utf-8
""" Custom API Errors and error handler. """
import blinker
from six import with_metaclass
from flask import jsonify, current_app


class ApiErrorType(type):
    """ Automatically populates an `error_type` class attribute.

    The error_type is generated from the class name, if not explicitly given in
    the class.
    """

    def __init__(cls, name, bases, dct):
        cls.error_type = dct.pop('error_type', '')
        if not cls.error_type:
            for char in name:
                if char.isupper() and cls.error_type:
                    cls.error_type += '-'
                cls.error_type += char.lower()
        super(ApiErrorType, cls).__init__(name, bases, dct)


class ApiError(with_metaclass(ApiErrorType, Exception)):
    """ Abstract, generic API error.

    You'll typically want to create a subclass this for each specific error
    scenario.

    Example:

    >>> class InvalidCredentials(ApiError):
    ...     code = 401
    >>> InvalidCredentials.error_type
    'invalid-credentials'

    """

    code = 400
    header = 'X-Pofh-Api-Error'

    def __init__(self, details=None):
        super(ApiError, self).__init__(self.error_type)
        self.details = details or None

    def __str__(self):
        return '<ApiError [{:d}]: {!s}>'.format(self.code, self.error_type)

    def __repr__(self):
        return "{!s}(details={!r})".format(
            self.__class__.__name__,
            self.details)

    def get_response(self):
        """ Format a Flask JSON response object from this error. """
        response = jsonify(
            error=self.error_type,
            details=self.details or {},
        )
        response.status_code = self.code
        if self.header:
            response.headers[self.header] = self.error_type
        return response

    @classmethod
    def subtypes(cls):
        """ Recursively list all subtypes of this type. """
        for sub in cls.__subclasses__():
            for subsub in sub.list_subtypes():
                yield subsub
            yield sub


def list_error_types():
    """ Lists all ApiError error types.

    This is useful for documentation, or when developing clients. It allows us
    to list out all the possible non-standard errors from the API.

    Note: Error types that have not been constructed (e.g. lazy imports,
    conditional imports, conditional class construction) will not be included.
    """
    return list(sorted(ApiError.subtypes(), key=lambda e: e.error_type))


signal_api_error = blinker.signal('pofh.api-error')
""" ApiError signal.

This signal is sent from the default error handler.

The sender is the exception type (which allows receivers to connect only to
certain types). The exception itself is sent as a keyword argument,
``exception``.
"""


def _handle(error):
    current_app.logger.debug("API error: {!s}".format(error))
    signal_api_error.send(type(error), exception=error)
    return error.get_response()


def init_app(app):
    """ Sets up custom error handler for unhandled ApiError exceptions. """
    app.errorhandler(ApiError)(_handle)
