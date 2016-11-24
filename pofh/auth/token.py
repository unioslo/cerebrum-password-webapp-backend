# encoding: utf-8
""" JWT Auth token. """
from __future__ import unicode_literals, absolute_import

from datetime import timedelta
from datetime import datetime
import uuid
import jwt


class JWTAuthToken(object):
    """ Auth token for this application.

    Each token consists of a namespace (which identifies allowed actions) and
    an identity (which identifies some entity that the token is authorized to
    act upon). These values are serialized in the sub (subject) claim, as
    <<ns>:<id>>

    Any claim (sub, iss, jti, iat, exp, nbf) can be set using keyword
    arguments when creating a new token.

    """

    DEFAULT_EXP = timedelta(seconds=3)
    """ Default expire time, relative to ``iat``. """

    DEFAULT_NBF = timedelta(seconds=0)
    """ Default 'not before' time, relative to ``iat``. """

    JWT_ALGORITHM = 'HS512'
    """ Algorithm for signing and verifying tokens. """

    JWT_OPTIONS = {
        'require_iat': True,
        'require_nbf': True,
        'require_exp': True,
        'require_sub': True,
        'require_jti': True,
        'verify_iat': True,
        'verify_nbf': True,
        'verify_exp': True,
        'verify_aud': False,
        'verify_signature': True,
    }

    def __init__(self, **kwargs):
        self.namespace = None
        self.identity = None
        self.sub = kwargs.get('sub', ':')
        self.iss = kwargs.get('iss', None)
        self.jti = kwargs.get('jti', uuid.uuid4())
        self.iat = kwargs.get('iat', datetime.utcnow())
        self.exp = kwargs.get('exp', self.DEFAULT_EXP)
        self.nbf = kwargs.get('nbf', self.DEFAULT_NBF)

    def __repr__(self):
        return '{!s}({!s})'.format(
            self.__class__.__name__,
            ', '.join(('{!s}={!r}'.format(k, v)
                       for k, v in self.get_payload().items())))

    @classmethod
    def new(cls, namespace=None, identity=None, issuer=None):
        """ Create a new token, with a given namespace and identity.  """
        token = cls(iss=issuer)
        token.namespace = namespace
        token.identity = identity
        return token

    def renew(self):
        """ Update token with new 'nbf' and 'exp' claims.

        The new values are :py:func:`datetime.datetime.utcnow` + ``DEFAULT_*``.
        """
        self.nbf = datetime.utcnow() + self.DEFAULT_NBF
        self.exp = datetime.utcnow() + self.DEFAULT_EXP

    def get_payload(self):
        """ Build a payload for this token.

        :rtype: dict
        :return: A dict representation of token data.
        """
        # TBD: Should we have datetimes or timestamps in the payload?
        payload = {
            'jti': str(self.jti),
            'iat': self.iat,
            'nbf': self.nbf,
            'exp': self.exp,
            'sub': self.sub,
        }

        if self.iss:
            payload['iss'] = self.iss
        return payload

    @classmethod
    def from_payload(cls, payload):
        """ Create a new token from a JWT payload.

        :param dict payload: A dict representation of token data.

        :rtype: JWTAuthToken
        :return: A token initialized with values from the payload.
        """
        token = cls(iss=payload.get('iss'))
        for claim in ('iat', 'nbf', 'exp', 'sub', 'jti'):
            setattr(token, claim, payload[claim])
        return token

    def jwt_encode(self, secret):
        """ Encode payload as JWT.

        :param str secret: The secret to use for signing.

        :rtype: str
        :return: A JSON Web Token string.
        """
        return jwt.encode(self.get_payload(),
                          secret,
                          algorithm=self.JWT_ALGORITHM)

    @classmethod
    def jwt_decode(cls, token_value, secret, leeway=0):
        """ Decode and verify token.

        :param str token_value: The JSON Web Token value.
        :param str secret: The secret used to sign the token.
        :param int leeway: Delta (in seconds) to accept in nbf/exp values.

        :rtype: JWTAuthToken
        :return: A token initialized with values from the decoded payload.
        """
        payload = jwt.decode(
            token_value, secret,
            options=cls.JWT_OPTIONS,
            algorithms=[cls.JWT_ALGORITHM, ],
            leeway=leeway)
        return cls.from_payload(payload)

    @classmethod
    def jwt_debug(cls, token_value):
        """ Decode, but not verify token.

        :param str token_value: The JSON Web Token value.
        :param str secret: The secret used to sign the token.
        :param int leeway: Delta (in seconds) to accept in nbf/exp values.

        :rtype: dict
        :return: Payload from the decoded token.
        """
        return jwt.decode(token_value, verify=False)

    # PROPERTIES:

    @property
    def jti(self):
        """ Unique ID for this token. """
        try:
            return self.__jti
        except AttributeError:
            self.__jti = uuid.uuid4()
            return self.__jti

    @jti.setter
    def jti(self, value):
        if isinstance(value, uuid.UUID):
            self.__jti = value
        else:
            self.__jti = uuid.UUID(value)

    @jti.deleter
    def jti(self):
        del self.__jti

    @property
    def sub(self):
        """ The authorized subject. """
        return '{!s}:{!s}'.format(self.namespace or '', self.identity or '')

    @sub.setter
    def sub(self, value):
        def _pop(l):
            try:
                return l.pop(0) or None
            except IndexError:
                return None
        parts = value.split(':', 1)
        self.namespace = _pop(parts)
        self.identity = _pop(parts)

    @property
    def iat(self):
        """ when token was issued (:py:class:`datetime.datetime`).

        Can be set to either a datetime or a timestamp. Is set to `utcnow` if
        deleted.
        """
        return self.__issued_at

    @iat.setter
    def iat(self, when):
        if isinstance(when, (int, float)):
            self.__issued_at = datetime.utcfromtimestamp(int(when))
        elif isinstance(when, datetime):
            self.__issued_at = when
        else:
            raise ValueError("Invalid time for 'iat' ({!r})".format(when))

    @iat.deleter
    def iat(self):
        self.__issued_at = datetime.utcnow()

    @property
    def nbf(self):
        """ not before time (:py:class:`datetime.datetime`).

        Can be set to either a datetime, a timestamp, or a `timedelta` relative
        to `iat`. Is set to `DEFAULT_NBF` if deleted.
        """
        if isinstance(self.__nbf, timedelta):
            return self.iat + self.__nbf
        else:
            # assume timestamp
            return self.__nbf

    @nbf.setter
    def nbf(self, when):
        if isinstance(when, (datetime, timedelta)):
            self.__nbf = when
        elif isinstance(when, (int, float)):
            self.__nbf = datetime.utcfromtimestamp(int(when))
        else:
            raise ValueError("Invalid time for 'nbf' ({!r})".format(when))

    @nbf.deleter
    def nbf(self):
        self.nbf = self.DEFAULT_NBF

    @property
    def exp(self):
        """ expire time (:py:class:`datetime.datetime`).

        Can be set to either a datetime, a timestamp, or a `timedelta` relative
        to `iat`. Is set to `DEFAULT_EXP` if deleted.
        """
        if isinstance(self.__exp, timedelta):
            return self.iat + self.__exp
        else:
            return self.__exp

    @exp.setter
    def exp(self, when):
        if isinstance(when, (datetime, timedelta)):
            self.__exp = when
        elif isinstance(when, (int, float)):
            self.__exp = datetime.utcfromtimestamp(int(when))
        else:
            raise ValueError("Invalid time for 'exp' ({!r})".format(when))

    @exp.deleter
    def exp(self):
        self.exp = timedelta(seconds=self.DEFAULT_EXP)
