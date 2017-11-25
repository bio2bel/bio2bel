# -*- coding: utf-8 -*-

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from bio2bel.utils import get_connection


class Manager(object):
    """Managers handle the database construction, population and querying."""

    # This needs to be replaced with a declarative base
    Base = None
    # This needs to be replaced with the module name for the current package
    module_name = None

    def __init__(self, connection=None, check_first=True):
        """

        :param Optional[str] connection:
        :param bool check_first:
        """
        self.connection = get_connection(self.module, connection=connection)
        self.engine = create_engine(self.connection)
        self.session_maker = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)
        self.session = scoped_session(self.session_maker)
        self.create_all(check_first=check_first)

    @property
    def module(self):
        """Gets the module name for this manager. Example: ``interpro``

        :rtype: str
        """
        if self.module_name is None:
            raise ValueError('Class variable, module_name, was not set in definition of {}'.format(self.__class__))

        return self.module_name

    @property
    def base(self):
        """Gets the SQLAlchemy Base for this manager"""
        if self.Base is None:
            raise ValueError('Class variable, Base, was not set in definition of {}'.format(self.__class__))

        return self.Base

    def create_all(self, check_first=True):
        """Create the empty database (tables)"""
        self.base.metadata.create_all(self.engine, checkfirst=check_first)

    def drop_all(self, check_first=True):
        """Create the empty database (tables)"""
        self.base.metadata.drop_all(self.engine, checkfirst=check_first)
