# -*- coding: utf-8 -*-

from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

from bio2bel import AbstractManager
from bio2bel.exc import Bio2BELMissingModelsError
from bio2bel.abstractmanager import AbstractManagerFlaskMixin
from bio2bel.testing import MockConnectionMixin


class TestFailure(MockConnectionMixin):

    def test_missing_models(self):
        class ExampleFlaskTestManager(AbstractManagerFlaskMixin):
            module_name = 'test'

        self.assertIs(ExampleFlaskTestManager.flask_admin_models, ...)

        manager = ExampleFlaskTestManager(connection=self.connection)
        self.assertIs(manager.flask_admin_models, ...)

        with self.assertRaises(Bio2BELMissingModelsError):
            manager.get_flask_admin_app()

    def test_app(self):
        TestBase = declarative_base()

        class Model(TestBase):
            __tablename__ = 'test_model'
            id = Column(Integer, primary_key=True)
            model_id = Column(String(15), nullable=False, index=True, unique=True)

        class FlaskTestManager(AbstractManager):
            module_name = 'test'
            flask_admin_models = [Model]

            @property
            def base(self):
                return TestBase

            def populate(self):
                self.session.add_all([
                    Model(model_id='model:{}'.format(model_id))
                    for model_id in range(4)
                ])
                self.session.commit()

        manager = FlaskTestManager(connection=self.connection)
        manager.populate()

        app = manager.get_flask_admin_app()
        client = app.test_client()

        home_rv = client.get('/')
        self.assertIn(Model.__name__.encode('utf-8'), home_rv.data)

        rv = client.get('/{}'.format(Model.__name__.lower()), follow_redirects=True)
        self.assertIn(b'model:1', rv.data)
