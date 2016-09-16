#!/usr/bin/env python3
# coding:utf-8

from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Shell
from app import create_app, db
from app.models.user import User
import config

app = create_app(config)
migrate = Migrate(app, db)
manager = Manager(app)


def save(entity):
    db.session.add(entity)
    db.session.commit()


def make_shell_context():
    return dict(app=app, db=db, User=User, save=save)

manager.add_command('db', MigrateCommand)
manager.add_command('shell', Shell(make_context=make_shell_context))

if __name__ == '__main__':
    manager.run()

