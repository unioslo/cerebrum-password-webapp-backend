# coding:utf-8
from datetime import datetime, timedelta
import pytz

from flask import current_app
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer,
                          BadSignature, SignatureExpired)
from marshmallow import fields, Schema
from passlib.apps import custom_app_context as pwd_context
from . import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password_hash = db.Column(db.String(128))
    password_updated_at = db.Column(db.DateTime)

    def __init__(self, **kwargs):
        self.username = kwargs.get('username', None)
        self.hash_password(kwargs.get('password', None))
        self.password_updated_at = datetime.utcnow()

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    def generate_auth_token(self, expiration=3600):
        s = Serializer(current_app.config.get('SECRET_KEY'), expires_in=expiration)
        expire_timestamp = datetime.now(
            tz=pytz.timezone(current_app.config['TIMEZONE'])
        ) + timedelta(seconds=expiration)
        return s.dumps({
            'id': self.id,
            'username': self.username,
            'expiry_timestamp': expire_timestamp.isoformat()}).decode('utf-8')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config.get('SECRET_KEY'))
        try:
            data = s.loads(token)
            return data
        except SignatureExpired:
            return None
        except BadSignature:
            return None

    def __str__(self):
        return self.username

    def __repr__(self):
        return '<User {0}>'.format(self.username)


class UserSchema(Schema):
    id = fields.Integer()
    username = fields.String()
    last_login = fields.DateTime()