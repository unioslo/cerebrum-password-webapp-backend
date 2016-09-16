# coding:utf-8
from functools import wraps

from flask import request, current_app
from flask_restplus import Resource, Namespace
from marshmallow import fields, Schema
from app.models.user import User

api = Namespace('auth', description="Auth related operations")


def auth_required():
    """
    Decorator to place on routes that need authentication.
    It will check if a request contained a valid JWT, and reject the
    request if not.
    :return: The function for the route that was decorated.
    """
    def wrapper(route):
        @wraps(route)
        def decorated_route(*args, **kwargs):
            auth = request.headers.get('Authorization')
            if auth is None:
                response = {'message': 'Unauthenticated request.'}
                return response, 403
            token_data = User.verify_auth_token(auth.split()[-1])
            if token_data is None:
                response = {'message': 'Invalid or expired token.'}
                return response, 403
            kwargs['token_data'] = token_data
            return route(*args, **kwargs)
        return decorated_route
    return wrapper


@api.route('/getToken')
class GetToken(Resource):
    """
    Route to get a JWT. Requires a valid username and password.
    """
    def post(self):
        schema = GetTokenSchema()
        validate = schema.load(request.json)
        if validate.errors:
            current_app.logger.warn(validate.errors)
            api.abort(400, validate.errors)
        current_app.logger.warn(request.json)
        current_app.logger.warn(request.json['username'])
        current_app.logger.warn(request.json['password'])
        if request.json.get('username') is None or request.json.get('password') is None:
            return {'message': 'username and password required'}, 400
        user = User.query.filter_by(username=request.json['username']).first()
        if user is None or not user.verify_password(request.json['password']):
            return {'message': 'Invalid username or password.'}, 401
        return {'token': user.generate_auth_token()}


@api.route('/refreshToken')
class RefreshToken(Resource):
    def get(self):
        """
        Route to refresh the client's JWT. Verifies that the current JWT is
        valid, and returns a JSON-response with a newly created JWT. If
        the current JWT is invalid (or not present), the request is rejected.
        :return:
        """
        auth = request.headers.get('Authorization')
        if auth is None:
            api.abort(400, 'Request did not have a token.')
        token_data = User.verify_auth_token(auth.split()[-1])
        if token_data is None:
            api.abort(401, 'Invalid or expired token.')
        user = User.query.get(token_data['id'])
        return {'token': user.generate_auth_token()}


class GetTokenSchema(Schema):
    username = fields.String(required=True, allow_none=False)
    password = fields.String(required=True, allow_none=False)
