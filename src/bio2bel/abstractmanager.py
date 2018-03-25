# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .utils import get_connection


class Bio2BELMissingNameError(TypeError):
    """Raised when an abstract manager is subclassed and instantiated without overriding the module name"""


class Bio2BELModuleCaseError(TypeError):
    """Raised when the module name in a subclassed and instantiated manager is not all lowercase"""


class AbstractManager(ABC):
    """Managers handle the database construction, population and querying.

    :cvar str module_name: The name of the module represented by this manager

    Needs several hooks/abstract methods to be set/overridden, but ultimately reduces redundant code

    Example for InterPro:

    >>> from sqlalchemy.ext.declarative import declarative_base
    >>> from bio2bel.abstractmanager import AbstractManager
    >>> Base = declarative_base()
    >>> class Manager(AbstractManager):
    >>>     module_name = 'interpro'
    >>>     def base(self):
    >>>         return Base
    >>>     def populate(self):
    >>>         ...
    """
    #: This represents the module name. Needs to be lower case
    module_name = ...

    def __init__(self, connection=None, check_first=True):
        """
        :param Optional[str] connection: SQLAlchemy connection string
        :param bool check_first: Defaults to True, don't issue CREATEs for tables already present
         in the target database. Defers to :meth:`bio2bel.abstractmanager.AbstractManager.create_all`
        """
        if not self.module_name or not isinstance(self.module_name, str):
            raise Bio2BELMissingNameError('module_name class variable not set on {}'.format(self.__class__.__name__))

        if self.module_name != self.module_name.lower():
            raise Bio2BELModuleCaseError('module_name class variable should be lowercase')

        self.connection = self.get_connection(connection=connection)
        self.engine = create_engine(self.connection)
        self.session_maker = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)
        self.session = scoped_session(self.session_maker)
        self.create_all(check_first=check_first)

    @classmethod
    def get_connection(cls, connection=None):
        """Gets the default connection string by wrapping :func:`bio2bel.utils.get_connection` and passing
        :data:`module_name` to it.

        :param Optional[str] connection: A custom connection to pass through
        :rtype: str
        """
        return get_connection(cls.module_name, connection=connection)

    @property
    @abstractmethod
    def base(self):
        """Returns the abstract base. Usually sufficient to return an instance that is module-level.

        :rtype: sqlalchemy.ext.declarative.api.DeclarativeMeta

        How to build an instance of :class:`sqlalchemy.ext.declarative.api.DeclarativeMeta`:

        >>> from sqlalchemy.ext.declarative import declarative_base
        >>> Base = declarative_base()

        Then just override this abstractmethod like:

        >>> def base(self):
        >>>     return Base
        """

    @abstractmethod
    def populate(self, *args, **kwargs):
        """Populate method should be overridden"""

    def create_all(self, check_first=True):
        """Create the empty database (tables)

        :param bool check_first: Defaults to True, don't issue CREATEs for tables already present
         in the target database. Defers to :meth:`sqlalchemy.sql.schema.MetaData.create_all`
        """
        self.base.metadata.create_all(self.engine, checkfirst=check_first)

    def drop_all(self, check_first=True):
        """Create the empty database (tables)

        :param bool check_first: Defaults to True, only issue DROPs for tables confirmed to be
          present in the target database. Defers to :meth:`sqlalchemy.sql.schema.MetaData.drop_all`
        """
        self.base.metadata.drop_all(self.engine, checkfirst=check_first)

    def _count_model(self, model):
        """Helps count the number of a given model in the database

        :param sqlalchemy.ext.declarative.api.DeclarativeMeta model: A SQLAlchemy model class
        :rtype: int
        """
        return self.session.query(model).count()

    @classmethod
    def ensure(cls, connection=None):
        """Checks and allows for a Manager to be passed to the function.

        :param connection: can be either a already build manager or a connection string to build a manager with.
        :type connection: Optional[str or AbstractManager]
        """
        if connection is None or isinstance(connection, str):
            return cls(connection=connection)

        if isinstance(connection, cls):
            return connection

        raise TypeError('passed invalid type: {}'.format(connection.__class__.__name__))

    def __repr__(self):
        return '<{module_name}Manager url={url}>'.format(
            module_name=self.module_name.capitalize(),
            url=self.engine.url
        )
