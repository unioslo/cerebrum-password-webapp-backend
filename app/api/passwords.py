# coding:utf-8
from flask import request, current_app
from flask_restplus import Resource, Namespace
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from marshmallow import fields, Schema
from app.models.user import User
from app.models import db

from .auth import auth_required
api = Namespace('password', description="Password related operations")


@api.route('/')
class PasswordUpdater(Resource):
    @auth_required()
    def put(self, **kwargs):
        schema = UpdateSchema()
        validate = schema.load(request.json)
        if validate.errors:
            current_app.logger.warn(validate.errors)
            api.abort(400, 'Invalid request')
        if not request.json['id'] == kwargs['token_data']['id']:
            api.abort(403, 'Accounts can only validate their own password')
        user = User.query.get(request.json['id'])
        if user is None:
            api.abort(404, "User {} not found".format(request.json['id']))
        if user.verify_password(request.json['password']):
            api.abort(401, 'Password not accepted.')
        user.hash_password(request.json['password'])
        user.password_updated_at = datetime.utcnow()
        db.session.add(user)
        db.session.commit()
        return 200, {'message': 'Password updated'}


class UpdateSchema(Schema):
    password = fields.String(required=True, allow_none=False)
    id = fields.Integer(required=True, allow_none=False)