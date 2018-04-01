# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .exc import Bio2BELMissingModelsError, Bio2BELMissingNameError, Bio2BELModuleCaseError
from .models import Action
from .utils import get_connection

__all__ = ['AbstractManager', ]


class AbstractManagerConnectionMixin(object):
    """Represents the connection-building aspect of the abstract manager. Minimally requires the definition of the
    class-level variable, ``module_name``

    Example for InterPro:

    >>> from bio2bel.abstractmanager import AbstractManagerConnectionMixin
    >>> class Manager(AbstractManagerConnectionMixin):
    >>>     module_name = 'interpro'


    In general, this class won't be used directly except in the situation where the connection should be loaded
    in a different way and it can be used as a mixin.
    """

    #: This represents the module name. Needs to be lower case
    module_name = ...

    def __init__(self, connection=None):
        """
        :param Optional[str] connection: SQLAlchemy connection string
        """
        if not self.module_name or not isinstance(self.module_name, str):
            raise Bio2BELMissingNameError('module_name class variable not set on {}'.format(self.__class__.__name__))

        if self.module_name != self.module_name.lower():
            raise Bio2BELModuleCaseError('module_name class variable should be lowercase')

        self.connection = self.get_connection(connection=connection)
        self.engine = create_engine(self.connection)
        self.session_maker = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)
        self.session = scoped_session(self.session_maker)

    @classmethod
    def get_connection(cls, connection=None):
        """Gets the default connection string by wrapping :func:`bio2bel.utils.get_connection` and passing
        this class's :data:`module_name` to it.

        :param Optional[str] connection: A custom connection to pass through
        :rtype: str
        """
        return get_connection(cls.module_name, connection=connection)


class AbstractManagerBase(ABC, AbstractManagerConnectionMixin):  # TODO write docstring
    """"""

    def __init__(self, connection=None, check_first=True):
        """
        :param Optional[str] connection: SQLAlchemy connection string
        :param bool check_first: Defaults to True, don't issue CREATEs for tables already present
         in the target database. Defers to :meth:`bio2bel.abstractmanager.AbstractManager.create_all`
        """
        super().__init__(connection=connection)
        self.create_all(check_first=check_first)

    @property
    @abstractmethod
    def base(self):
        """Returns the abstract base. Usually sufficient to return an instance that is module-level.

        :rtype: sqlalchemy.ext.declarative.api.DeclarativeMeta

        How to build an instance of :class:`sqlalchemy.ext.declarative.api.DeclarativeMeta` by using
        :func:`sqlalchemy.ext.declarative.declarative_base`:

        >>> from sqlalchemy.ext.declarative import declarative_base
        >>> Base = declarative_base()

        Then just override this abstract property like:

        >>> @property
        >>> def base(self):
        >>>     return Base
        """

    def create_all(self, check_first=True):
        """Create the empty database (tables)

        :param bool check_first: Defaults to True, don't issue CREATEs for tables already present
         in the target database. Defers to :meth:`sqlalchemy.sql.schema.MetaData.create_all`
        """
        self.base.metadata.create_all(self.engine, checkfirst=check_first)


class AbstractManagerFlaskMixin(AbstractManagerConnectionMixin):
    """Mixin for making the AbstractManager build a Flask application"""

    #: Represents a list of SQLAlchemy classes to make a Flask-Admin interface
    flask_admin_models = ...

    def _add_admin(self, app, **kwargs):
        """Adds a Flask Admin interface to an application

        :param flask.Flask app: A Flask application
        :param kwargs:
        :rtype: flask_admin.Admin
        """
        if self.flask_admin_models is ...:
            raise Bio2BELMissingModelsError

        from flask_admin import Admin
        from flask_admin.contrib.sqla import ModelView

        admin = Admin(app, **kwargs)

        for Model in self.flask_admin_models:
            admin.add_view(ModelView(Model, self.session))

        return admin

    def get_flask_admin_app(self, url=None):
        """Creates a Flask application if this class has defined the :data:`flask_admin_models` variable a list of
        model classes.

        :param Optional[str] url: Optional mount point of the admin application. Defaults to ``'/'``.
        :rtype: flask.Flask
        """
        from flask import Flask

        app = Flask(__name__)
        self._add_admin(app, url=(url or '/'))
        return app


class AbstractManager(AbstractManagerFlaskMixin, AbstractManagerBase):
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

    Building on the previous example, the abstract property :data:`bio2bel.AbstractManager.base` must be overridden
    to return the value from your :func:`sqlalchemy.ext.declarative.declarative_base`. We chose to make this an
    instance-level property instead of a class-level variable so each manager could have its own information about
    connections to the database.

    As a minimal example:

    .. code-block:: python

        from bio2bel import AbstractManager
        from sqlalchemy.ext.declarative import declarative_base

        Base = declarative_base()

        class Manager(AbstractManager):
            module_name = 'mirtarbase'  # note: use lower case module names

            @property
            def base(self):
                return Base


    In general, the models should be defined in a module called ``models.py`` so the ``Base`` can also be imported.

    .. code-block:: python

        from bio2bel import AbstractManager
        from .constants import MODULE_NAME
        from .models import Base

        class Manager(AbstractManager):
            module_name = MODULE_NAME

            @property
            def base(self):
                return Base

    **Populating the Database**

    Deciding how to populate the database using your SQLAlchemy models is incredibly creative and can't be given a good
    example without checking real code. See the previously mentioned `implementation of a Manager <https://github.com/bio2bel/mirtarbase/blob/master/src/bio2bel_mirtarbase/manager.py>`_.

    .. code-block:: python

        from bio2bel import AbstractManager
        from .constants import MODULE_NAME
        from .models import Base

        class Manager(AbstractManager):
            module_name = MODULE_NAME

            @property
            def base(self):
                return Base

            def populate(self):
                ...

    **Preparing Flask Admin (Optional)**

    This class also contains a function to build a :mod:`flask` application for easy viewing of the contents of the
    database. Besides installing the optional requirements with ``python3 -m pip install flask flask-admin``, all
    that's necessary to make this available is to override the class variable ``flask_admin_models``.

    .. code-block:: python

        from bio2bel import AbstractManager
        from .constants import MODULE_NAME
        from .models import Base, Evidence, Interaction, Mirna, Species, Target

        class Manager(AbstractManager):
            module_name = MODULE_NAME
            flask_admin_models = [Evidence, Interaction, Mirna, Species, Target]

            @property
            def base(self):
                return Base

            def populate(self):
                ...

    **Exporting to BEL (Optional)**

    If a function named ``to_bel`` is implemented that returns a :class:`pybel.BELGraph`, then the manager and CLI
    will have access to several other functions that would rely on this.
    """

    @classmethod
    def ensure(cls, connection=None):
        """Allows a manager to be build from a string, or a pre-built manager to be passed through.

        This function is a polymorphic constructor inspired by the
        `Factory Method <https://en.wikipedia.org/wiki/Factory_method_pattern>`_

        :param connection: can be either a already build manager or a connection string to build a manager with.
        :type connection: Optional[str or AbstractManager]
        """
        if connection is None or isinstance(connection, str):
            return cls(connection=connection)

        if isinstance(connection, cls):
            return connection

        raise TypeError('passed invalid type: {}'.format(connection.__class__.__name__))

    @abstractmethod
    def populate(self, *args, **kwargs):
        """Populate method should be overridden"""

    def _count_model(self, model):
        """Helps count the number of a given model in the database

        :param sqlalchemy.ext.declarative.api.DeclarativeMeta model: A SQLAlchemy model class
        :rtype: int
        """
        return self.session.query(model).count()

    def drop_all(self, check_first=True):
        """Create the empty database (tables)

        :param bool check_first: Defaults to True, only issue DROPs for tables confirmed to be
          present in the target database. Defers to :meth:`sqlalchemy.sql.schema.MetaData.drop_all`
        """
        self.base.metadata.drop_all(self.engine, checkfirst=check_first)
        Action.store_drop(self.module_name)

    def __repr__(self):
        return '<{module_name}Manager url={url}>'.format(
            module_name=self.module_name.capitalize(),
            url=self.engine.url
        )
