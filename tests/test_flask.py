# -*- coding: utf-8 -*-

"""Tests the Flask web application generation utilities."""

from bio2bel.abstractmanager import AbstractManagerFlaskMixin
from bio2bel.exc import Bio2BELMissingModelsError
from bio2bel.testing import MockConnectionMixin
from tests.constants import Manager, Model


class WrongFlaskTestManager(AbstractManagerFlaskMixin):
    """An implementation of an AbstractManager that is unable to produce a Flask app."""
    module_name = 'test'


class FlaskTestManager(Manager):
    """Extends the test Manager for generating a Flask application"""
    flask_admin_models = [Model]


class TestFlask(MockConnectionMixin):
    """Tests Flask application generation."""

    def test_missing_models(self):
        """Test exceptions are thrown properly for an improperly implemented AbstractManager."""
        self.assertIs(WrongFlaskTestManager.flask_admin_models, ...)

        manager = WrongFlaskTestManager(connection=self.connection)
        self.assertIs(manager.flask_admin_models, ...)

        with self.assertRaises(Bio2BELMissingModelsError):
            manager.get_flask_admin_app()

    def test_app(self):
        """Test the successful generation of a flask application."""
        manager = FlaskTestManager(connection=self.connection)
        manager.populate()

        app = manager.get_flask_admin_app()
        client = app.test_client()

        home_rv = client.get('/')
        self.assertIn(Model.__name__.encode('utf-8'), home_rv.data)

        rv = client.get('/{}'.format(Model.__name__.lower()), follow_redirects=True)
        self.assertIn(b'MODEL:1', rv.data)
