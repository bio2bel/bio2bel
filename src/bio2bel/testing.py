# -*- coding: utf-8 -*-

"""This module has tools for quickly writing unit tests with :mod:`unittest` that involve the usage of a mock data with
a Bio2BEL manager."""

import logging
import os
import tempfile
import unittest
from unittest import mock

from .abstractmanager import AbstractManager
from .exc import Bio2BELManagerTypeError, Bio2BELTestMissingManagerError

log = logging.getLogger(__name__)


class TemporaryConnectionMixin(unittest.TestCase):
    """Creates a :class:`unittest.TestCase` that has a persistent file for use with SQLite during testing."""

    @classmethod
    def setUpClass(cls):
        """Creates a temporary file to use as a persistent database throughout tests in this class. Subclasses of
        :class:`TemporaryCacheClsMixin` can extend :func:`TemporaryCacheClsMixin.setUpClass` to populate the database
        """
        super(TemporaryConnectionMixin, cls).setUpClass()

        cls.fd, cls.path = tempfile.mkstemp()
        cls.connection = 'sqlite:///' + cls.path
        log.info('test database at %s', cls.connection)

    @classmethod
    def tearDownClass(cls):
        """Closes the connection to the database and removes the files created for it"""
        os.close(cls.fd)
        os.remove(cls.path)


class MockConnectionMixin(TemporaryConnectionMixin):
    """Allows for testing with a consistent connection without changing the configuration"""

    @classmethod
    def setUpClass(cls):
        """Adds two class-level variables: ``mock_global_connection`` and ``mock_module_connection`` that can be
        used as context managers to mock the bio2bel connection getter functions."""

        super(MockConnectionMixin, cls).setUpClass()

        def mock_connection():
            """Returns the connection enclosed by this class

            :rtype: str
            """
            return cls.connection

        cls.mock_global_connection = mock.patch('bio2bel.models.get_global_connection', mock_connection)
        cls.mock_module_connection = mock.patch('bio2bel.utils.get_connection', mock_connection)


class AbstractTemporaryCacheClassMixin(TemporaryConnectionMixin):
    """Allows for testing with a consistent connection and creation of a manager class wrapping that connection.

    Requires the class variable ``Manager`` to be overriden with the class corresponding to the manager to be used that
    is a subclass of :class:`bio2bel.AbstractManager`.
    """
    Manager = ...

    @classmethod
    def setUpClass(cls):
        """Sets up the class with the given manager and allows an optional populate hook to be overridden"""
        if cls.Manager is ...:
            raise Bio2BELTestMissingManagerError('Must override class variable "Manager" with subclass of '
                                                 'bio2bel.AbstractManager')

        if not issubclass(cls.Manager, AbstractManager):
            raise Bio2BELManagerTypeError('Manager must be a subclass of bio2bel.AbstractManager')

        super(AbstractTemporaryCacheClassMixin, cls).setUpClass()

        cls.manager = cls.Manager(connection=cls.connection)
        cls.populate()

    @classmethod
    def tearDownClass(cls):
        """Closes the connection in the manager and deletes the temporary database"""
        cls.manager.session.close()

        super(AbstractTemporaryCacheClassMixin, cls).tearDownClass()

    @classmethod
    def populate(cls):
        """A stub that can be overridden to populate the manager"""


def make_temporary_cache_class_mixin(manager_cls):
    """Builds a testing class that has a Bio2BEL manager instance ready to go

    :param type[bio2bel.AbstractManager] manager_cls: A Bio2BEL manager
    :rtype: type[AbstractTemporaryCacheClassMixin]
    """

    class TemporaryCacheClassMixin(AbstractTemporaryCacheClassMixin):
        Manager = manager_cls

    return TemporaryCacheClassMixin
