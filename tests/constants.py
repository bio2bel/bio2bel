# -*- coding: utf-8 -*-

import logging
from unittest import mock

from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

from bio2bel.abstractmanager import AbstractManager
from bio2bel.testing import TemporaryConnectionMixin

log = logging.getLogger(__name__)


class MockConnectionMixin(TemporaryConnectionMixin):
    @classmethod
    def setUpClass(cls):
        """Create temporary file"""
        super(MockConnectionMixin, cls).setUpClass()

        def mock_connection():
            return cls.connection

        cls.mock_global_connection = mock.patch('bio2bel.models.get_global_connection', mock_connection)
        cls.mock_module_connection = mock.patch('bio2bel.utils.get_connection', mock_connection)


TestBase = declarative_base()


class Model(TestBase):
    __tablename__ = 'test_model'
    id = Column(Integer, primary_key=True)
    model_id = Column(String(15), nullable=False, index=True, unique=True)


class Manager(AbstractManager):
    """Manager for running tests"""

    module_name = 'test'

    @property
    def base(self):
        return TestBase

    def get_model_by_model_id(self, model_id):
        return self.session.query(Model).filter(Model.model_id == model_id).one_or_none()

    def count_model(self):
        return self._count_model(Model)

    def populate(self):
        """Won't implement this, but at least override it"""
        models = [
            Model(model_id='MODEL{}'.format(model_id))
            for model_id in range(5)
        ]
        self.session.add_all(models)
        self.session.commit()
