# -*- coding: utf-8 -*-

"""Testing constants and utilities for Bio2BEL."""

import logging

from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

from bio2bel.abstractmanager import AbstractManager

log = logging.getLogger(__name__)

TestBase = declarative_base()


class Model(TestBase):
    """A test model"""
    __tablename__ = 'test_model'

    id = Column(Integer, primary_key=True)

    model_id = Column(String(15), nullable=False, index=True, unique=True)
    name = Column(String(255), nullable=False, index=True)


class Manager(AbstractManager):
    """Manager for running tests."""

    module_name = 'test'

    @property
    def _base(self):
        return TestBase

    def get_model_by_model_id(self, model_id):
        """Get a model if it exists by its identifier.

        :param str model_id: A Model identifier
        :rtype: Optional[Model]
        """
        return self.session.query(Model).filter(Model.model_id == model_id).one_or_none()

    def count_model(self):
        """Count the test model.

        :rtype: int
        """
        return self._count_model(Model)

    def list_model(self):
        """Get all models.

        :rtype: list[Model]
        """
        return self._list_model(Model)

    def is_populated(self):
        """Check if the database is already populated.

        :rtype: bool
        """
        return 0 < self.count_model()

    def populate(self):
        """Add five models to the store."""
        models = [
            Model(
                model_id='MODEL:{}'.format(model_id),
                name='{model_id}{model_id}{model_id}{model_id}{model_id}'.format(model_id=model_id),
            )
            for model_id in range(5)
        ]
        self.session.add_all(models)
        self.session.commit()
