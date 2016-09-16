# coding:utf-8
from flask import Flask
from flask_cors import CORS
from models import user, db
from api import api
cors = CORS()


def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)
    db.init_app(app)
    cors.init_app(app)
    api.init_app(app)
    return app
