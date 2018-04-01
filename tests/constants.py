# -*- coding: utf-8 -*-

import logging

from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

from bio2bel.abstractmanager import AbstractManager

log = logging.getLogger(__name__)

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
        """Gets a model if it exists by its identifier

        :param str model_id: A Model identifier
        :rtype: Optional[Model]
        """
        return self.session.query(Model).filter(Model.model_id == model_id).one_or_none()

    def count_model(self):
        """Counts the test model

        :rtype: int
        """
        return self._count_model(Model)

    def populate(self):
        """Adds five models to the store"""
        models = [
            Model(model_id='MODEL{}'.format(model_id))
            for model_id in range(5)
        ]
        self.session.add_all(models)
        self.session.commit()
