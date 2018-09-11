# -*- coding: utf-8 -*-

"""Bio2BEL database models.

Bio2BEL adds hooks to the populate and drop_all methods in the :py:class:`bio2bel.AbstractManager` class to track when they
are run and therefore create provenance information for a given analysis.

The most recent population action from a given module can be retrieved with the following code:

.. code-block:: python

    from bio2bel.models import Action, _make_session
    from sqlalchemy import desc

    session = _make_session()
    action = session.query(Action).filter(Action.resource == 'kegg').order_by(Action.created.desc()).first()

"""

import datetime
import logging
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from bio2bel.constants import get_global_connection

log = logging.getLogger(__name__)

Base = declarative_base()

TABLE_PREFIX = 'bio2bel'
ACTION_TABLE_NAME = '{}_action'.format(TABLE_PREFIX)


def create_all(engine, checkfirst=True):
    """Create the tables for Bio2BEL."""
    Base.metadata.create_all(bind=engine, checkfirst=checkfirst)


def _make_session(connection: Optional[str] = None):
    """Make a session.

    :type connection: Optional[str]
    :rtype: sqlalchemy.orm.Session
    """
    if connection is None:
        connection = get_global_connection()

    engine = create_engine(connection)

    create_all(engine)

    session_cls = sessionmaker(bind=engine)
    session = session_cls()

    return session


def _store_helper(model, session=None):
    """Help store an action.

    :param Action model:
    :param Optional[sqlalchemy.orm.Session] session: A pre-built session
    :rtype: Action
    """
    if session is None:
        session = _make_session()

    session.add(model)
    session.commit()
    session.close()

    return model


class Action(Base):
    """Represents an update, dropping, population, etc. to the database."""

    __tablename__ = ACTION_TABLE_NAME

    id = Column(Integer, primary_key=True)

    resource = Column(String(32), nullable=False,
                      doc='The normalized name of the Bio2BEL package (e.g., hgnc, chebi, etc)')
    action = Column(String(32), nullable=False)
    created = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, doc='The date and time of upload')

    def __repr__(self):  # noqa: D105
        return '{} {} at {}'.format(self.resource, self.action, self.created)

    @staticmethod
    def make_populate(resource) -> 'Action':
        """Make a ``populate`` instance of :class:`Action`."""
        return Action(resource=resource.lower(), action='populate')

    @staticmethod
    def make_populate_failed(resource) -> 'Action':
        """Make a ``populate_failed`` instance of :class:`Action`."""
        return Action(resource=resource.lower(), action='populate_failed')

    @staticmethod
    def make_drop(resource) -> 'Action':
        """Make a ``drop`` instance of :class:`Action`."""
        return Action(resource=resource.lower(), action='drop')

    @classmethod
    def store_populate(cls, resource: str, session=None) -> 'Action':
        """Store a "populate" event.

        :param resource: The normalized name of the resource to store
        :param Optional[sqlalchemy.orm.Session] session: A pre-built session

        Example:

        >>> from bio2bel.models import Action
        >>> Action.store_populate('hgnc')
        """
        return _store_helper(cls.make_populate(resource), session=session)

    @classmethod
    def store_populate_failed(cls, resource: str, session=None) -> 'Action':
        """Store a "populate failed" event.

        :param resource: The normalized name of the resource to store
        :param Optional[sqlalchemy.orm.Session] session: A pre-built session

        Example:

        >>> from bio2bel.models import Action
        >>> Action.store_populate_failed('hgnc')
        """
        return _store_helper(cls.make_populate_failed(resource), session=session)

    @classmethod
    def store_drop(cls, resource: str, session=None) -> 'Action':
        """Store a "drop" event.

        :param resource: The normalized name of the resource to store
        :param Optional[sqlalchemy.orm.Session] session: A pre-built session

        Example:

        >>> from bio2bel.models import Action
        >>> Action.store_drop('hgnc')
        """
        return _store_helper(cls.make_drop(resource), session=session)

    @classmethod
    def ls(cls, session=None):
        """Get all actions.

        :param Optional[sqlalchemy.orm.Session] session: A pre-built session
        :rtype: list[Action]
        """
        if session is None:
            session = _make_session()

        actions = session.query(cls).order_by(cls.created.desc()).all()
        session.close()
        return actions

    @classmethod
    def count(cls, session=None) -> int:
        """Count all actions.

        :param Optional[sqlalchemy.orm.Session] session: A pre-built session
        """
        if session is None:
            session = _make_session()

        count = session.query(cls).count()
        session.close()
        return count
