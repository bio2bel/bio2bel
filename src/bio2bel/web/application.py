# -*- coding: utf-8 -*-

"""The Bio2BEL web application."""

import importlib
import logging
from typing import Optional

import flask_bootstrap
from flask import Blueprint, Flask, render_template
from flask_admin import Admin
from pkg_resources import VersionConflict, iter_entry_points

from bio2bel.constants import DEFAULT_CACHE_CONNECTION
from bio2bel.manager.connection_manager import build_engine_session

log = logging.getLogger(__name__)

ui = Blueprint('ui', __name__)

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
            web_modules[entry] = importlib.import_module(f'bio2bel_{entry}.web')
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
    """Show the home page."""
    return render_template('index.html', entries=sorted(add_admins))


def create_application(connection: Optional[str] = None) -> Flask:
    """Create a Flask application."""
    app = Flask(__name__)

    flask_bootstrap.Bootstrap(app)
    Admin(app)

    connection = connection or DEFAULT_CACHE_CONNECTION
    engine, session = build_engine_session(connection)

    for name, add_admin in add_admins.items():
        url = f'/{name}'
        add_admin(app, session, url=url, endpoint=name, name=name)
        log.debug('added %s - %s to %s', name, add_admin, url)

    app.register_blueprint(ui)

    return app
