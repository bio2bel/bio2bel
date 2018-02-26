# -*- coding: utf-8 -*-

"""Bio2BEL database model"""

import datetime
import logging

from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from bio2bel.constants import get_global_connection

log = logging.getLogger(__name__)

Base = declarative_base()

TABLE_PREFIX = 'bio2bel'
ACTION_TABLE_NAME = '{}_action'.format(TABLE_PREFIX)


class Action(Base):
    """Represents an update, dropping, population, etc. to the database"""
    __tablename__ = ACTION_TABLE_NAME

    id = Column(Integer, primary_key=True)

    resource = Column(String(32), nullable=False,
                      doc='The normalized name of the Bio2BEL package (e.g., hgnc, chebi, etc)')
    action = Column(String(32), nullable=False)
    created = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, doc='The date and time of upload')

    @classmethod
    def make_populate(cls, resource):
        """Make a ``populate`` instance of :class:`Action`"""
        return Action(resource=resource.lower(), action='populate')

    @classmethod
    def make_drop(cls, resource):
        """Make a ``drop`` instance of :class:`Action`"""
        return Action(resource=resource.lower(), action='drop')

    @classmethod
    def _store_helper(cls, make_method, resource):
        connection = get_global_connection()

        engine = create_engine(connection)
        Base.metadata.create_all(engine, checkfirst=True)

        Session = sessionmaker(bind=engine)
        session = Session()

        model = make_method(resource)
        session.add(model)
        session.commit()
        session.close()

    @classmethod
    def store_populate(cls, resource):
        """Stores a drop event

        :param str resource: The normalized name of the resource to store

        >>> from bio2bel.models import Action
        >>> Action.store_populate('hgnc')
        """
        cls._store_helper(cls.make_populate, resource)

    @classmethod
    def store_drop(cls, resource):
        """Stores a drop event

        :param str resource: The normalized name of the resource to store

        >>> from bio2bel.models import Action
        >>> Action.store_drop('hgnc')
        """
        cls._store_helper(cls.make_drop, resource)


def store_populate(resource):
    Action.store_populate(resource)

def store_drop(resource):
    Action.store_drop(resource)

if __name__ == '__main__':
    Action.store_populate('hgnc')
