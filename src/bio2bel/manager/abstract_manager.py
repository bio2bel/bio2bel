# -*- coding: utf-8 -*-

"""Provides abstractions over the management of SQLAlchemy connections and sessions."""

from abc import ABCMeta, abstractmethod
from functools import wraps
import logging
import os
import sys

import click

from .cli_manager import CliMixin
from .connection_manager import ConnectionManager
from ..utils import get_data_dir

__all__ = [
    'AbstractManager',
]

log = logging.getLogger(__name__)


class AbstractManagerMeta(ABCMeta):
    """Crazy metaclass to hack in a decorator to the populate function."""

    def __new__(mcs, name, bases, namespace, **kwargs):  # noqa: N804
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        cls._populate_original = cls.populate

        @wraps(cls._populate_original)
        def populate_wrapped(self, *populate_args, **populate_kwargs):
            """Populate the database."""
            cls._populate_original(self, *populate_args, **populate_kwargs)

            # Hack in the action storage
            self._store_populate()

        cls.populate = populate_wrapped

        return cls


class AbstractManager(ConnectionManager, CliMixin, metaclass=AbstractManagerMeta):
    """This is a base class for implementing your own Bio2BEL manager.

    It already includes functions to handle configuration, construction of a connection to a database using SQLAlchemy,
    creation of the tables defined by your own :func:`sqlalchemy.ext.declarative.declarative_base`, and has hooks to
    override that populate and make simple queries to the database. Since :class:`AbstractManager` inherits from
    :class:`abc.ABC` and is therefore an abstract class, there are a few class variables, functions, and properties
    that need to be overridden.

    **Overriding the Module Name**

    First, the class-level variable ``module_name`` must be set to a string corresponding to the name of the data
    source.

    .. code-block:: python

        from bio2bel import AbstractManager

        class Manager(AbstractManager):
            module_name = 'mirtarbase'  # note: use lower case module names

    In general, this should also correspond to the same value as ``MODULE_NAME`` set in ``constants.py`` and can also
    be set with an assignment to this value

    .. code-block:: python

        from bio2bel import AbstractManager
        from .constants import MODULE_NAME

        class Manager(AbstractManager):
            module_name = MODULE_NAME

    **Setting the Declarative Base**

    Building on the previous example, the (private) abstract property :data:`bio2bel.AbstractManager._base` must be
    overridden to return the value from your :func:`sqlalchemy.ext.declarative.declarative_base`. We chose to make this
    an instance-level property instead of a class-level variable so each manager could have its own information about
    connections to the database.

    As a minimal example:

    .. code-block:: python

        from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base

        from bio2bel import AbstractManager

        Base: DeclarativeMeta = declarative_base()

        class Manager(AbstractManager):
            module_name = 'mirtarbase'  # note: use lower case module names

            @property
            def _base(self) -> DeclarativeMeta:
                return Base


    In general, the models should be defined in a module called ``models.py`` so the ``Base`` can also be imported.

    .. code-block:: python

        from sqlalchemy.ext.declarative import DeclarativeMeta

        from bio2bel import AbstractManager

        from .constants import MODULE_NAME
        from .models import Base

        class Manager(AbstractManager):
            module_name = MODULE_NAME

            @property
            def _base(self) -> DeclarativeMeta:
                return Base

    **Populating the Database**

    Deciding how to populate the database using your SQLAlchemy models is incredibly creative and can't be given a good
    example without checking real code. See the previously mentioned `implementation of a Manager
    <https://github.com/bio2bel/mirtarbase/blob/master/src/bio2bel_mirtarbase/manager.py>`_.

    .. code-block:: python

        from sqlalchemy.ext.declarative import DeclarativeMeta

        from bio2bel import AbstractManager

        from .constants import MODULE_NAME
        from .models import Base

        class Manager(AbstractManager):
            module_name = MODULE_NAME

            @property
            def _base(self) -> DeclarativeMeta:
                return Base

            def populate(self) -> None:
                ...

    **Checking the Database is Populated**

    A method for checking if the database has been populated already must be implemented as well. The easiest way to
    implement this is to check that there's a non-zero count of whatever the most important model in the database is.

    .. code-block:: python

        from sqlalchemy.ext.declarative import DeclarativeMeta

        from bio2bel import AbstractManager

        from .constants import MODULE_NAME
        from .models import Base

        class Manager(AbstractManager):
            module_name = MODULE_NAME

            @property
            def _base(self) -> DeclarativeMeta:
                return Base

            def populate(self) -> None:
                ...

            def is_populated(self) -> bool:
                return 0 < self.session.query(MyImportantModel).count()

    There are several mixins that can be optionally inherited:

    1. :py:class:`bio2bel.manager.flask_manager.FlaskMixin`: the Flask Mixin creates a Flask-Admin web application.
    2. :py:class:`bio2bel.manager.namespace_manager.BELNamespaceManagerMixin`: the BEL Namespace Manager Mixin exports
       a BEL namespace and interact with PyBEL.
    3. :py:class:`bio2bel.manager.bel_manager.BELManagerMixin`: the BEL Manager Mixin exports a BEL script
       and interact with PyBEL.
    """

    @property
    @abstractmethod
    def _base(self):
        """Return the declarative base.

        It is usually sufficient to return an instance that is module-level.

        :rtype: sqlalchemy.ext.declarative.api.DeclarativeMeta

        How to build an instance of :class:`sqlalchemy.ext.declarative.api.DeclarativeMeta` by using
        :func:`sqlalchemy.ext.declarative.declarative_base`:

        >>> from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
        >>> Base: DeclarativeMeta = declarative_base()

        Then just override this abstract property like:

        >>> @property
        >>> def _base(self) -> DeclarativeMeta:
        >>>     return Base

        Note that this property could effectively also be a static method.
        """

    def __init__(self, *args, **kwargs):  # noqa: D107
        super().__init__(*args, **kwargs)
        self.create_all()

    @abstractmethod
    def is_populated(self):
        """Check if the database is already populated.

        :rtype: bool
        """

    @abstractmethod
    def populate(self, *args, **kwargs):
        """Populate the database."""

    @abstractmethod
    def summarize(self):
        """Summarize the database.

        :rtype: dict[str,int]
        """

    @property
    def _metadata(self):
        """Return the metadata object associated with this manager's declarative base."""
        return self._base.metadata

    def create_all(self, check_first=True):
        """Create the empty database (tables).

        :param bool check_first: Defaults to True, don't issue CREATEs for tables already present
         in the target database. Defers to :meth:`sqlalchemy.sql.schema.MetaData.create_all`
        """
        self._metadata.create_all(self.engine, checkfirst=check_first)

    def drop_all(self, check_first=True):
        """Drop all tables from the database.

        :param bool check_first: Defaults to True, only issue DROPs for tables confirmed to be
          present in the target database. Defers to :meth:`sqlalchemy.sql.schema.MetaData.drop_all`
        """
        self._metadata.drop_all(self.engine, checkfirst=check_first)
        self._store_drop()

    def _get_query(self, model):
        """Get a query for the given model using this manager's session.

        :param sqlalchemy.ext.declarative.api.DeclarativeMeta model: A SQLAlchemy model class
        :return: a SQLAlchemy query
        """
        return self.session.query(model)

    def _count_model(self, model):
        """Count the number of the given model in the database.

        :param sqlalchemy.ext.declarative.api.DeclarativeMeta model: A SQLAlchemy model class
        :rtype: int
        """
        return self._get_query(model).count()

    def _list_model(self, model):
        """Get all instances of the given model in the database.

        :param sqlalchemy.ext.declarative.api.DeclarativeMeta model: A SQLAlchemy model class
        :rtype: list
        """
        return self._get_query(model).all()

    @staticmethod
    def _cli_add_populate(main):
        """Add the populate command.

        :type main: click.Group
        :rtype: click.Group
        """
        return add_cli_populate(main)

    @staticmethod
    def _cli_add_drop(main):
        """Add the drop command.

        :type main: click.Group
        :rtype: click.Group
        """
        return add_cli_drop(main)

    @staticmethod
    def _cli_add_cache(main):
        """Add the cache command.

        :type main: click.Group
        :rtype: click.Group
        """
        return add_cli_cache(main)

    @staticmethod
    def _cli_add_summarize(main):
        """Add the summarize command.

        :type main: click.Group
        :rtype: click.Group
        """
        return add_cli_summarize(main)

    @classmethod
    def get_cli(cls):
        """Get the :mod:`click` main function to use as a command line interface.

        :rtype: click.Group
        """
        main = super().get_cli()

        cls._cli_add_populate(main)
        cls._cli_add_drop(main)
        cls._cli_add_cache(main)
        cls._cli_add_summarize(main)

        return main


def add_cli_populate(main):
    """Add a ``populate`` command to main :mod:`click` function.

    :param click.Group main: A click-decorated main function
    :rtype: click.Group
    """
    @main.command()
    @click.option('--reset', is_flag=True, help='Nuke database first')
    @click.option('--force', is_flag=True, help='Force overwrite if already populated')
    @click.pass_obj
    def populate(manager, reset, force):
        """Populate the database."""
        if reset:
            click.echo('Deleting the previous instance of the database')
            manager.drop_all()
            click.echo('Creating new models')
            manager.create_all()

        if manager.is_populated() and not force:
            click.echo('Database already populated. Use --force to overwrite')
            sys.exit(0)

        manager.populate()

    return main


def add_cli_drop(main):
    """Add a ``drop`` command to main :mod:`click` function.

    :param click.Group main: A click-decorated main function
    :rtype: click.Group
    """
    @main.command()
    @click.option('-y', '--yes', is_flag=True)
    @click.pass_obj
    def drop(manager, yes):
        """Drop the database."""
        if yes or click.confirm('Drop everything?'):
            manager.drop_all()

    return main


def add_cli_cache(main):
    """Add several commands to main :mod:`click` function for handling the cache.

    :param click.Group main: A click-decorated main function
    :rtype: click.Group
    """
    @main.group()
    def cache():
        """Manage cached data."""

    @cache.command()
    @click.pass_obj
    def ls(manager):
        """List files in the cache."""
        data_dir = get_data_dir(manager.module_name)

        for path in os.listdir(data_dir):
            click.echo(path)

    @cache.command()
    @click.pass_obj
    def clear(manager):
        """Clear all files from the cache."""
        data_dir = get_data_dir(manager.module_name)

        for path in os.listdir(data_dir):
            if path in {'config.ini', 'cache.db'}:
                continue
            os.remove(os.path.join(data_dir, path))

    return main


def add_cli_summarize(main):
    """Add a ``summarize`` command to main :mod:`click` function.

    :param click.Group main: A click-decorated main function
    :rtype: click.Group
    """
    @main.command()
    @click.pass_obj
    def summarize(manager):
        """Summarize the contents of the database."""
        for name, count in sorted(manager.summarize().items()):
            click.echo('{}: {}'.format(name.capitalize(), count))

    return main
