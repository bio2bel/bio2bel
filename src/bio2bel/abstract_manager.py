# -*- coding: utf-8 -*-

"""Provides abstractions over the management of SQLAlchemy connections and sessions."""

import click
import logging
from abc import ABCMeta, abstractmethod
from functools import wraps
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .cli_utils import add_cli_cache, add_cli_drop, add_cli_flask, add_cli_populate, add_cli_summarize
from .exc import Bio2BELMissingModelsError, Bio2BELMissingNameError, Bio2BELModuleCaseError
from .models import Action, create_all
from .utils import get_connection, get_version

__all__ = [
    'AbstractManager',
]

log = logging.getLogger(__name__)


class AbstractManagerMeta(ABCMeta):
    """Crazy metaclass to hack in a decorator to the populate function."""

    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        cls._populate_original = cls.populate

        @wraps(cls._populate_original)
        def populate_wrapped(self, *populate_args, **populate_kwargs):
            """Populates the database."""
            cls._populate_original(self, *populate_args, **populate_kwargs)

            # Hack in the action storage
            self._store_populate()

        cls.populate = populate_wrapped

        return cls


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


class AbstractManagerConnectionMixin(object):
    """Represents the connection-building aspect of the abstract manager.

    Minimally requires the definition of the class-level variable, ``module_name``.

    Example for InterPro:

    >>> from bio2bel.abstract_manager import AbstractManagerConnectionMixin
    >>> class Manager(AbstractManagerConnectionMixin):
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

    def __repr__(self):
        return '<{module_name}Manager url={url}>'.format(
            module_name=self.module_name.capitalize(),
            url=self.engine.url
        )


class _QueryMixin(AbstractManagerConnectionMixin):
    """A mixin with convenient functions for querying the database."""

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


class _CliMixin(AbstractManagerConnectionMixin):
    """Functions for building a CLI."""

    @classmethod
    def _get_cli_main(cls):
        """Build a :mod:`click` CLI main function.

        :param Type[AbstractManager] cls: A Manager class
        :return: The main function for click
        :rtype: click.core.Command
        """

        @click.group(help='Default connection at {}\n\nusing Bio2BEL v{}'.format(cls._get_connection(), get_version()))
        @click.option('-c', '--connection', default=cls._get_connection(),
                      help='Defaults to {}'.format(cls._get_connection()))
        @click.pass_context
        def main(ctx, connection):
            """Bio2BEL CLI."""
            logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            logging.getLogger('bio2bel.utils').setLevel(logging.WARNING)
            ctx.obj = cls(connection=connection)

        return main

    @staticmethod
    def _cli_add_populate(main):
        """Add the populate command.

        :type main: click.core.Group
        :rtype: click.core.Group
        """
        return add_cli_populate(main)

    @staticmethod
    def _cli_add_drop(main):
        """Add the drop command.

        :type main: click.core.Group
        :rtype: click.core.Group
        """
        return add_cli_drop(main)

    @staticmethod
    def _cli_add_cache(main):
        """Add the cache command.

        :type main: click.core.Group
        :rtype: click.core.Group
        """
        return add_cli_cache(main)

    @staticmethod
    def _cli_add_summarize(main):
        """Add the summarize command.

        :type main: click.core.Group
        :rtype: click.core.Group
        """
        return add_cli_summarize(main)

    @classmethod
    def get_cli(cls):
        """Gets a :mod:`click` main function to use as a command line interface.

        :rtype: click.core.Group
        """
        main = cls._get_cli_main()

        cls._cli_add_populate(main)
        cls._cli_add_drop(main)
        cls._cli_add_cache(main)

        if hasattr(cls, 'summarize'):
            cls._cli_add_summarize(main)

        return main


class _FlaskMixin(_CliMixin, AbstractManagerConnectionMixin):
    """Mixin for making the AbstractManager build a Flask application."""

    #: Represents a list of SQLAlchemy classes to make a Flask-Admin interface.
    flask_admin_models = ...

    def _add_admin(self, app, **kwargs):
        """Add a Flask Admin interface to an application.

        :param flask.Flask app: A Flask application
        :param kwargs: Keyword arguments are passed through to :class:`flask_admin.Admin`
        :rtype: flask_admin.Admin
        """
        if self.flask_admin_models is ...:
            raise Bio2BELMissingModelsError

        from flask_admin import Admin
        from flask_admin.contrib.sqla import ModelView

        admin = Admin(app, **kwargs)

        for flask_admin_model in self.flask_admin_models:
            if isinstance(flask_admin_model, tuple):  # assume its a 2 tuple
                if len(flask_admin_model) != 2:
                    raise TypeError

                model, view = flask_admin_model
                admin.add_view(view(model, self.session))

            else:
                admin.add_view(ModelView(flask_admin_model, self.session))

        return admin

    def get_flask_admin_app(self, url=None):
        """Create a Flask application.

        :param Optional[str] url: Optional mount point of the admin application. Defaults to ``'/'``.
        :rtype: flask.Flask
        """
        from flask import Flask

        app = Flask(__name__)
        self._add_admin(app, url=(url or '/'))
        return app

    @staticmethod
    def _cli_add_flask(main):
        """Add the web command.

        :type main: click.core.Group
        :rtype: click.core.Group
        """
        return add_cli_flask(main)

    @classmethod
    def get_cli(cls):
        """Add  a :mod:`click` main function to use as a command line interface.

        :rtype: click.core.Group
        """
        main = super().get_cli()

        cls._cli_add_flask(main)

        return main


class AbstractManager(_FlaskMixin, _QueryMixin, _CliMixin, metaclass=AbstractManagerMeta):
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

    **Checking the Database Is Populated**

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


    **Preparing Flask Admin (Optional)**

    This class also contains a function to build a :mod:`flask` application for easy viewing of the contents of the
    database. Besides installing the optional requirements with ``python3 -m pip install flask flask-admin``, all
    that's necessary to make this available is to override the class variable ``flask_admin_models``.

    .. code-block:: python

        from sqlalchemy.ext.declarative import DeclarativeMeta

        from bio2bel import AbstractManager

        from .constants import MODULE_NAME
        from .models import Base, Evidence, Interaction, Mirna, Species, Target

        class Manager(AbstractManager):
            module_name = MODULE_NAME
            flask_admin_models = [Evidence, Interaction, Mirna, Species, Target]

            @property
            def _base(self) -> DeclarativeMeta:
                return Base

            def populate(self) -> None:
                ...

    **Exporting a BEL Namespace (Optional)**

    To enable a Bio2BEL manager to use the namespace utilities, the :mod:`pybel`
    library needs to be installed and the :py:class:`bio2bel.namespace_manager.NamespaceManagerMixin`
    needs to be used as one of the parent classes of the manager. See its documentation for a guide.

    **Exporting to BEL (Optional)**

    To enable a Bio2BEL manager to use BEL utilities, the :mod:`pybel` libary needs to be installed
    and the :py:class:`bio2bel.BELManagerMixin` needs to be used as a parent class.
    """

    @property
    @abstractmethod
    def _base(self):
        """Returns the declarative base.

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

    def __init__(self, *args, **kwargs):
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

    def register_transformations(self):
        """Register transformation functions from this instance to the global Pipeline framework.

        Must be overridden, otherwise does not do anything.
        """
