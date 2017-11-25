# -*- coding: utf-8 -*-

import importlib
import logging

import flask
import flask_bootstrap
from flask_admin import Admin
from pkg_resources import VersionConflict, iter_entry_points
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from bio2bel.constants import DEFAULT_CACHE_CONNECTION

log = logging.getLogger(__name__)

ui = flask.Blueprint('ui', __name__)

web_modules = {}
add_admins = {}

for entry_point in iter_entry_points(group='bio2bel', name=None):
    entry = entry_point.name

    try:
        bio2bel_module = entry_point.load()
    except VersionConflict:
        log.warning('Version conflict in %s', entry)
        continue

    try:
        web_modules[entry] = bio2bel_module.web
    except AttributeError:
        try:
            web_modules[entry] = importlib.import_module('bio2bel_{}.web'.format(entry))
        except ImportError:
            log.warning('no submodule bio2bel_%s.web', entry)
            continue

    try:
        add_admins[entry] = web_modules[entry].add_admin
    except AttributeError:
        log.warning('no function bio2bel_%s.web.add_admin', entry)
        continue


@ui.route('/')
def home():
    """no place like home"""
    return flask.render_template('index.html', entries=sorted(add_admins))


def create_application(connection=None):
    """

    :param Optional[str] connection:
    :rtype: flask.Flask
    """
    app = flask.Flask(__name__)

    flask_bootstrap.Bootstrap(app)
    Admin(app)

    connection = connection or DEFAULT_CACHE_CONNECTION
    engine = create_engine(connection)
    session_maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = scoped_session(session_maker)

    for name, add_admin in add_admins.items():
        url = '/{}'.format(name)
        try:
            add_admin(app, session, url=url, endpoint=name, name=name)
            log.warning('added %s - %s to %s', name, add_admin, url)
        except:
            log.exception('couldnt add %s', name)
    app.register_blueprint(ui)

    return app
