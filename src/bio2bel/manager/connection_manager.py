# -*- coding: utf-8 -*-

"""Provides abstractions over the management of SQLAlchemy connections and sessions."""

import logging
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from ..exc import Bio2BELMissingNameError, Bio2BELModuleCaseError
from ..models import Action, create_all
from ..utils import get_connection

__all__ = [
    'ConnectionManager',
]

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Represents the connection-building aspect of the abstract manager.

    Minimally requires the definition of the class-level variable, ``module_name``.

    Example for InterPro:

    >>> from bio2bel.manager import ConnectionManager
    >>> class Manager(ConnectionManager):
    >>>     module_name = 'interpro'

    In general, this class won't be used directly except in the situation where the connection should be loaded
    in a different way and it can be used as a mixin.
    """

    #: This represents the module name. Needs to be lower case
    module_name: str

    def __init__(self, connection: Optional[str] = None, engine=None, session=None, **kwargs):
        """Build an abstract manager from either a connection or an engine/session.

        The remaining keyword arguments are passed to :func:`build_engine_session`.

        :param connection:
        :param engine:
        :param session:
        """
        self._assert_module_name()

        if connection and (engine or session):
            raise ValueError('can not specify connection with engine/session')

        if engine is None and session is None:
            if connection is None:
                connection = self._get_connection()

            engine, session = build_engine_session(connection=connection, **kwargs)

        self.engine = engine
        self.session = session

        create_all(self.engine)

    @property
    def connection(self) -> str:
        """Return this manager's connection string."""
        return str(self.engine.url)

    @classmethod
    def _assert_module_name(cls):
        if not hasattr(cls, 'module_name'):
            raise Bio2BELMissingNameError(f'module_name class variable not set on {cls.__name__}')
        elif not isinstance(cls.module_name, str):
            raise TypeError(f'module_name class variable not set as str: {cls.__name__}')
        elif cls.module_name != cls.module_name.lower():
            raise Bio2BELModuleCaseError('module_name class variable should be lowercase')

    @classmethod
    def _get_connection(cls, connection: Optional[str] = None) -> str:
        """Get a default connection string.

        Wraps :func:`bio2bel.utils.get_connection` and passing this class's :data:`module_name` to it.
        """
        return get_connection(connection=connection)

    def _store_populate(self):
        Action.store_populate(self.module_name, session=self.session)

    def _store_populate_failed(self):
        Action.store_populate_failed(self.module_name, session=self.session)

    def _store_drop(self):
        Action.store_drop(self.module_name, session=self.session)

    def __repr__(self):  # noqa: D105
        return f'<{self.module_name.capitalize()}Manager url={self.engine.url}>'


def build_engine_session(
    connection: str,
    echo: bool = False,
    autoflush: Optional[bool] = None,
    autocommit: Optional[bool] = None,
    expire_on_commit: Optional[bool] = None,
    scopefunc=None,
):
    """Build an engine and a session.

    :param connection: An RFC-1738 database connection string
    :param echo: Turn on echoing SQL
    :param autoflush: Defaults to True if not specified in kwargs or configuration.
    :param autocommit: Defaults to False if not specified in kwargs or configuration.
    :param expire_on_commit: Defaults to False if not specified in kwargs or configuration.
    :param scopefunc: Scoped function to pass to :func:`sqlalchemy.orm.scoped_session`
    :rtype: tuple[Engine,Session]

    From the Flask-SQLAlchemy documentation:

    An extra key ``'scopefunc'`` can be set on the ``options`` dict to
    specify a custom scope function.  If it's not provided, Flask's app
    context stack identity is used. This will ensure that sessions are
    created and removed with the request/response cycle, and should be fine
    in most cases.
    """
    engine = create_engine(connection, echo=echo)

    autoflush = autoflush if autoflush is not None else False
    autocommit = autocommit if autocommit is not None else False
    expire_on_commit = expire_on_commit if expire_on_commit is not None else True

    logger.debug('auto flush: %s, auto commit: %s, expire on commmit: %s', autoflush, autocommit, expire_on_commit)

    #: A SQLAlchemy session maker
    session_maker = sessionmaker(
        bind=engine,
        autoflush=autoflush,
        autocommit=autocommit,
        expire_on_commit=expire_on_commit,
    )

    #: A SQLAlchemy session object
    session = scoped_session(
        session_maker,
        scopefunc=scopefunc,
    )

    return engine, session
