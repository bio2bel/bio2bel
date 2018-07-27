# -*- coding: utf-8 -*-

"""Provides abstractions over the management of SQLAlchemy connections and sessions."""

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from ..exc import Bio2BELMissingNameError, Bio2BELModuleCaseError
from ..models import Action, create_all
from ..utils import get_connection

log = logging.getLogger(__name__)

__all__ = [
    'ConnectionManager',
]


class ConnectionManager(object):
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
    module_name = ...

    def __init__(self, connection=None, engine=None, session=None, **kwargs):
        """Build an abstract manager from either a connection or an engine/session.

        The remaining keyword arguments are passed to :func:`build_engine_session`.

        :param Optional[str] connection:
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

    @property
    def connection(self):
        """Return this manager's connection string."""
        return str(self.engine.url)

    @classmethod
    def _assert_module_name(cls):
        if cls.module_name is ...:
            raise Bio2BELMissingNameError('module_name class variable not set on {}'.format(cls.__name__))

        if not isinstance(cls.module_name, str):
            raise TypeError('module_name class variable not set as str: {}'.format(cls.__name__))

        if cls.module_name != cls.module_name.lower():
            raise Bio2BELModuleCaseError('module_name class variable should be lowercase')

    @classmethod
    def _get_connection(cls, connection=None):
        """Get a default connection string.

        Wraps :func:`bio2bel.utils.get_connection` and passing this class's :data:`module_name` to it.

        :param Optional[str] connection: A custom connection to pass through
        :rtype: str
        """
        return get_connection(cls.module_name, connection=connection)

    def _store_populate(self):
        create_all(self.engine)
        Action.store_populate(self.module_name, session=self.session)

    def _store_drop(self):
        create_all(self.engine)
        Action.store_drop(self.module_name, session=self.session)

    def __repr__(self):  # noqa: D105
        return '<{module_name}Manager url={url}>'.format(
            module_name=self.module_name.capitalize(),
            url=self.engine.url
        )


def build_engine_session(connection, echo=False, autoflush=None, autocommit=None, expire_on_commit=None,
                         scopefunc=None):
    """Build an engine and a session.

    :param str connection: An RFC-1738 database connection string
    :param bool echo: Turn on echoing SQL
    :param Optional[bool] autoflush: Defaults to True if not specified in kwargs or configuration.
    :param Optional[bool] autocommit: Defaults to False if not specified in kwargs or configuration.
    :param Optional[bool] expire_on_commit: Defaults to False if not specified in kwargs or configuration.
    :param scopefunc: Scoped function to pass to :func:`sqlalchemy.orm.scoped_session`
    :rtype: tuple[Engine,Session]

    From the Flask-SQLAlchemy documentation:

    An extra key ``'scopefunc'`` can be set on the ``options`` dict to
    specify a custom scope function.  If it's not provided, Flask's app
    context stack identity is used. This will ensure that sessions are
    created and removed with the request/response cycle, and should be fine
    in most cases.
    """
    if connection is None:
        raise ValueError('can not build engine when connection is None')

    engine = create_engine(connection, echo=echo)

    autoflush = autoflush if autoflush is not None else False
    autocommit = autocommit if autocommit is not None else False
    expire_on_commit = expire_on_commit if expire_on_commit is not None else True

    log.debug('auto flush: %s, auto commit: %s, expire on commmit: %s', autoflush, autocommit, expire_on_commit)

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
        scopefunc=scopefunc
    )

    return engine, session
