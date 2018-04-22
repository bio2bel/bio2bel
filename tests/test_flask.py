# -*- coding: utf-8 -*-

"""Tests the Flask web application generation utilities."""

from flask_admin.contrib.sqla import ModelView

from bio2bel.abstractmanager import _FlaskMixin
from bio2bel.exc import Bio2BELMissingModelsError
from bio2bel.testing import TemporaryConnectionMethodMixin
from tests.constants import Manager, Model


class WrongFlaskTestManager(_FlaskMixin):
    """An implementation of an AbstractManager that is unable to produce a Flask app."""
    module_name = 'test'


class FlaskTestManager(Manager):
    """Extends the test Manager for generating a Flask application."""
    flask_admin_models = [Model]


class TruncatedModelView(ModelView):
    """A truncated Flask Admin view."""
    column_exclude_list = ['model_id']


class FlaskTestViewManager(Manager):
    """Extends the test Manager for generating a Flask application."""
    flask_admin_models = [(Model, TruncatedModelView)]


class FlaskFailureTestViewManager(Manager):
    """Extends the test Manager for generating a Flask application."""
    flask_admin_models = [(Model, TruncatedModelView, 'junk!')]


class TestFlask(TemporaryConnectionMethodMixin):
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

        self.assertFalse(manager.is_populated())
        manager.populate()
        self.assertTrue(manager.is_populated())

        app = manager.get_flask_admin_app()
        client = app.test_client()

        home_rv = client.get('/')
        self.assertIn(Model.__name__.encode('utf-8'), home_rv.data)

        rv = client.get('/{}'.format(Model.__name__.lower()), follow_redirects=True)
        self.assertIn(b'MODEL:1', rv.data)

    def test_app_truncated_view(self):
        """Test the ability to define tuple views."""
        manager = FlaskTestViewManager(connection=self.connection)

        self.assertFalse(manager.is_populated())
        manager.populate()
        self.assertTrue(manager.is_populated())

        app = manager.get_flask_admin_app()
        client = app.test_client()

        home_rv = client.get('/')
        self.assertIn(Model.__name__.encode('utf-8'), home_rv.data)

        rv = client.get('/{}'.format(Model.__name__.lower()), follow_redirects=True)
        self.assertNotIn(b'MODEL:1', rv.data)
        self.assertIn(b'1111', rv.data)

    def test_app_view_failure(self):
        """Test the ability to define tuple views."""
        manager = FlaskFailureTestViewManager(connection=self.connection)
        manager.populate()
        with self.assertRaises(TypeError):
            manager.get_flask_admin_app()
