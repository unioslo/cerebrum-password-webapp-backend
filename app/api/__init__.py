# coding:utf-8
from flask_restplus import Api
from .passwords import api as users_api
from .auth import api as auth_api

api = Api(
    title='Password app!',
    version='1.0',
    description='Password app API',
    doc=False
)

api.add_namespace(users_api)
api.add_namespace(auth_api)
