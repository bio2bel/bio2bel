# -*- coding: utf-8 -*-

"""Testing utilities for Bio2BEL.

This module has tools for quickly writing unit tests with :mod:`unittest` that involve the usage of a mock data with
a Bio2BEL manager.
"""

import logging
import os
import tempfile
import unittest
from unittest import mock

from .exc import Bio2BELManagerTypeError, Bio2BELTestMissingManagerError
from .manager.abstract_manager import AbstractManager

__all__ = [
    'TemporaryConnectionMethodMixin',
    'TemporaryConnectionMixin',
    'MockConnectionMixin',
    'AbstractTemporaryCacheMethodMixin',
    'AbstractTemporaryCacheClassMixin',
    'make_temporary_cache_class_mixin',
]

log = logging.getLogger(__name__)


class TemporaryConnectionMethodMixin(unittest.TestCase):
    """Creates a :class:`unittest.TestCase` that has a persistent file for use with SQLite during testing."""

    def setUp(self):
        """Create a temporary file to use as a persistent database throughout tests in this class."""
        super().setUp()

        self.fd, self.path = tempfile.mkstemp()
        self.connection = 'sqlite:///' + self.path
        log.info('test database at %s', self.connection)

    def tearDown(self):
        """Close the connection to the database and removes the files created for it."""
        os.close(self.fd)
        os.remove(self.path)


class TemporaryConnectionMixin(unittest.TestCase):
    """Creates a :class:`unittest.TestCase` that has a persistent file for use with SQLite during testing."""

    fd, path = None, None
    connection = None

    @classmethod
    def setUpClass(cls):
        """Create a temporary file to use as a persistent database throughout tests in this class.

        Subclasses of :class:`TemporaryCacheClsMixin` can extend :func:`TemporaryCacheClsMixin.setUpClass` to populate
        the database.
        """
        super().setUpClass()

        cls.fd, cls.path = tempfile.mkstemp()
        cls.connection = 'sqlite:///' + cls.path
        log.info('test database at %s', cls.connection)

    @classmethod
    def tearDownClass(cls):
        """Close the connection to the database and removes the files created for it."""
        os.close(cls.fd)
        os.remove(cls.path)


class MockConnectionMixin(TemporaryConnectionMixin):
    """Allows for testing with a consistent connection without changing the configuration."""

    def setUp(self):
        """Set up the test with a mock connection string.

        Add two class-level variables: ``mock_global_connection`` and ``mock_module_connection`` that can be
        used as context managers to mock the bio2bel connection getter functions.
        """
        super().setUp()

        def mock_connection():
            """Get the connection enclosed by this class.

            :rtype: str
            """
            return self.connection

        self.mock_global_connection = mock.patch('bio2bel.models.get_global_connection', mock_connection)
        self.mock_module_connection = mock.patch('bio2bel.utils.get_connection', mock_connection)


class AbstractTemporaryCacheMethodMixin(TemporaryConnectionMethodMixin):
    """Allows for testing with a consistent connection and creation of a manager class wrapping that connection.

    Requires the class variable ``Manager`` to be overriden with the class corresponding to the manager to be used that
    is a subclass of :class:`bio2bel.AbstractManager`.
    """

    Manager = ...
    manager = None

    def setUp(self):
        """Set up the class with the given manager and allows an optional populate hook to be overridden."""
        if self.Manager is ...:
            raise Bio2BELTestMissingManagerError('Must override class variable "Manager" with subclass of '
                                                 'bio2bel.AbstractManager')

        if not issubclass(self.Manager, AbstractManager):
            raise Bio2BELManagerTypeError('Manager must be a subclass of bio2bel.AbstractManager')

        super().setUp()

        self.manager = self.Manager(connection=self.connection)
        self.populate()

    def tearDown(self):
        """Close the connection in the manager and deletes the temporary database."""
        self.manager.session.close()
        super().tearDown()

    def populate(self):
        """Populate the database.

        This stub should be overridden.
        """


class AbstractTemporaryCacheClassMixin(TemporaryConnectionMixin):
    """Allows for testing with a consistent connection and creation of a manager class wrapping that connection.

    Requires the class variable ``Manager`` to be overriden with the class corresponding to the manager to be used that
    is a subclass of :class:`bio2bel.AbstractManager`.
    """

    Manager = ...
    manager = None

    @classmethod
    def setUpClass(cls):
        """Set up the class with the given manager and allows an optional populate hook to be overridden."""
        if cls.Manager is ...:
            raise Bio2BELTestMissingManagerError('Must override class variable "Manager" with subclass of '
                                                 'bio2bel.AbstractManager')

        if not issubclass(cls.Manager, AbstractManager):
            raise Bio2BELManagerTypeError('Manager must be a subclass of bio2bel.AbstractManager')

        super().setUpClass()

        cls.manager = cls.Manager(connection=cls.connection)
        cls.populate()

    @classmethod
    def tearDownClass(cls):
        """Close the connection in the manager and deletes the temporary database."""
        cls.manager.session.close()
        super().tearDownClass()

    @classmethod
    def populate(cls):
        """Populate the database.

        This stub should be overridden.
        """


def make_temporary_cache_class_mixin(manager_cls):
    """Build a testing class that has a Bio2BEL manager instance ready to go.

    :param type[bio2bel.AbstractManager] manager_cls: A Bio2BEL manager
    :rtype: type[AbstractTemporaryCacheClassMixin]
    """
    class TemporaryCacheClassMixin(AbstractTemporaryCacheClassMixin):
        Manager = manager_cls

    return TemporaryCacheClassMixin
