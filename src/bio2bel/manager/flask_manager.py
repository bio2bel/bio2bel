# -*- coding: utf-8 -*-

"""Provides abstractions over the management of SQLAlchemy connections and sessions."""

import os

import click
from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from .cli_manager import CliMixin
from .connection_manager import ConnectionManager
from ..exc import Bio2BELMissingModelsError

__all__ = [
    'FlaskMixin',
]


class FlaskMixin(ConnectionManager, CliMixin):
    """Mixin for making the AbstractManager build a Flask application."""

    #: Represents a list of SQLAlchemy classes to make a Flask-Admin interface.
    flask_admin_models = ...

    def __init__(self, *args, **kwargs):  # noqa: D107
        if self.flask_admin_models is ...:
            raise Bio2BELMissingModelsError(
                'FlaskMixin necessitates definition of class variable "flask_admin_models".')

        super().__init__(*args, **kwargs)

    def _add_admin(self, app, **kwargs):
        """Add a Flask Admin interface to an application.

        :param flask.Flask app: A Flask application
        :param kwargs: Keyword arguments are passed through to :class:`flask_admin.Admin`
        :rtype: flask_admin.Admin
        """
        admin = Admin(app, **kwargs)

        for flask_admin_model in self.flask_admin_models:
            if isinstance(flask_admin_model, tuple):  # assume its a 2 tuple
                if len(flask_admin_model) != 2:
                    raise TypeError

                model, view = flask_admin_model
                admin.add_view(view(model, self.session))

            else:
                admin.add_view(ModelView(flask_admin_model, self.session))

        return admin

    def get_flask_admin_app(self, url=None, secret_key=None):
        """Create a Flask application.

        :param Optional[str] url: Optional mount point of the admin application. Defaults to ``'/'``.
        :rtype: flask.Flask
        """
        app = Flask(__name__)

        if secret_key:
            app.secret_key = secret_key

        self._add_admin(app, url=(url or '/'))
        return app

    @staticmethod
    def _cli_add_flask(main):
        """Add the web command.

        :type main: click.core.Group
        :rtype: click.core.Group
        """
        return add_cli_flask(main)

    @classmethod
    def get_cli(cls):
        """Add  a :mod:`click` main function to use as a command line interface.

        :rtype: click.core.Group
        """
        main = super().get_cli()

        cls._cli_add_flask(main)

        return main


def add_cli_flask(main):
    """Add a ``web`` comand main :mod:`click` function.

    :param click.core.Group main: A click-decorated main function
    :rtype: click.core.Group
    """
    @main.command()
    @click.option('-v', '--debug', is_flag=True)
    @click.option('-p', '--port')
    @click.option('-h', '--host')
    @click.option('-k', '--secret-key', default=os.urandom(8))
    @click.pass_obj
    def web(manager, debug, port, host, secret_key):
        """Run the web app."""
        app = manager.get_flask_admin_app(url='/', secret_key=secret_key)
        app.run(debug=debug, host=host, port=port)

    return main
