# -*- coding: utf-8 -*-

"""Testing constants and utilities for Bio2BEL."""

import logging

from bio2bel.manager.abstract_manager import AbstractManager
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

log = logging.getLogger(__name__)

TestBase = declarative_base()

NUMBER_TEST_MODELS = 5
TEST_MODEL_ID_FORMAT = 'MODEL:{}'
TEST_MODEL_NAME_FORMAT = '{0}{0}{0}{0}{0}'


class Model(TestBase):
    """A test model."""

    __tablename__ = 'test_model'

    id = Column(Integer, primary_key=True)

    model_id = Column(String(15), nullable=False, index=True, unique=True)
    name = Column(String(255), nullable=False, index=True)

    @staticmethod
    def from_id(model_id):
        """Create a test Model from a given integer identifier.

        :param int model_id:
        :rtype: Model
        """
        return Model(
            model_id=TEST_MODEL_ID_FORMAT.format(model_id),
            name=TEST_MODEL_NAME_FORMAT.format(model_id),
        )


class Manager(AbstractManager):
    """Manager for running tests."""

    module_name = 'test'

    def __init__(self, *args, **kwargs):
        """Instantiate the manager."""
        super().__init__(*args, **kwargs)

        self.last_populate_args = []
        self.last_populate_kwargs = {}

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

    def populate(self, *args, **kwargs):
        """Add five models to the store."""
        models = [
            Model.from_id(model_id)
            for model_id in range(NUMBER_TEST_MODELS)
        ]
        self.session.add_all(models)
        self.session.commit()

        if args:
            self.last_populate_args = args
            log.critical('args: %s', args)

        if kwargs:
            self.last_populate_kwargs = kwargs
            log.critical('kwargs: %s', kwargs)

    def summarize(self):
        """Summarize the database.

        :rtype: dict[str,int]
        """
        return dict(
            models=self.count_model(),
        )
