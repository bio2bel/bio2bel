# -*- coding: utf-8 -*-

"""Testing constants and utilities for Bio2BEL."""

import logging
from typing import List, Mapping, Optional

from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

from bio2bel.manager.abstract_manager import AbstractManager

log = logging.getLogger(__name__)

TestBase = declarative_base()

NUMBER_TEST_MODELS = 5
TEST_MODEL_ID_FORMAT = 'MODEL:{}'  # noqa:FS003
TEST_MODEL_NAME_FORMAT = '{0}{0}{0}{0}{0}'  # noqa:FS003


class Model(TestBase):
    """A test model."""

    __tablename__ = 'test_model'

    id = Column(Integer, primary_key=True)  # noqa:A003

    test_id = Column(String(15), nullable=False, index=True, unique=True)
    name = Column(String(255), nullable=False, index=True)

    @staticmethod
    def from_id(test_id: int):
        """Create a test Model from a given integer identifier.

        :rtype: Model
        """
        return Model(
            test_id=TEST_MODEL_ID_FORMAT.format(test_id),
            name=TEST_MODEL_NAME_FORMAT.format(test_id),
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

    def get_model_by_model_id(self, test_id: str) -> Optional[Model]:
        """Get a model if it exists by its identifier."""
        return self.session.query(Model).filter(Model.test_id == test_id).one_or_none()

    def count_model(self) -> int:
        """Count the test model."""
        return self._count_model(Model)

    def list_model(self) -> List[Model]:
        """Get all models."""
        return self._list_model(Model)

    def is_populated(self) -> bool:
        """Check if the database is already populated."""
        return 0 < self.count_model()

    def populate(self, *args, **kwargs) -> None:
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

    def summarize(self) -> Mapping[str, int]:
        """Summarize the database."""
        return {
            'models': self.count_model(),
        }
