# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from bio2bel.utils import get_connection


class Bio2BELMissingNameError(TypeError):
    """Raised when an abstract manager is subclassed and instantiated without overriding the module name"""


class Bio2BELModuleCaseError(TypeError):
    """Raised when the module name in a subclassed and instantiated manager is not all lowercase"""


class AbstractManager(ABC):
    """Managers handle the database construction, population and querying.

    Needs several hooks/absract methods to be set/overridden, but ultimately reduces redundant code

    Example for InterPro:

    >>> from sqlalchemy.ext.declarative import declarative_base
    >>> from bio2bel.abstractmanager import AbstractManager
    >>> Base = declarative_base()
    >>> class Manager(AbstractManager):
    >>>     module_name = 'interpro'
    >>>
    """
    #: This represents the module name. Needs to be lower case
    module_name = ...

    def __init__(self, connection=None, check_first=True):
        """
        :param Optional[str] connection:
        :param bool check_first:
        """
        if not self.module_name or not isinstance(self.module_name, str):
            raise Bio2BELMissingNameError('module_name class variable not set on {}'.format(self.__class__.__name__))

        if self.module_name != self.module_name.lower():
            raise Bio2BELModuleCaseError('module_name class variable should be lowercase')

        self.connection = get_connection(self.module_name, connection=connection)
        self.engine = create_engine(self.connection)
        self.session_maker = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)
        self.session = scoped_session(self.session_maker)
        self.create_all(check_first=check_first)

    @property
    @abstractmethod
    def base(self):
        """Returns the abstract base

        :rtype: sqlalchemy.ext.declarative.api.DeclarativeMeta

        Example:

        >>> from sqlalchemy.ext.declarative import declarative_base
        >>> from bio2bel.abstractmanager import AbstractManager
        >>> Base = declarative_base()
        >>> class Manager(AbstractManager):
        >>>     def base(self):
        >>>         return Base
        >>>     ...
        """

    @abstractmethod
    def populate(self, *args, **kwargs):
        """Populate method should be overridden"""

    def create_all(self, check_first=True):
        """Create the empty database (tables)"""
        self.base.metadata.create_all(self.engine, checkfirst=check_first)

    def drop_all(self, check_first=True):
        """Create the empty database (tables)"""
        self.base.metadata.drop_all(self.engine, checkfirst=check_first)
