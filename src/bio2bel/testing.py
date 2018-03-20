# -*- coding: utf-8 -*-

import logging
import os
import tempfile
import unittest

log = logging.getLogger(__name__)

dir_path = os.path.dirname(os.path.realpath(__file__))


class TemporaryConnectionMixin(unittest.TestCase):
    """Creates a :class:`unittest.TestCase` that has a persistent file for use with SQLite during testing."""

    @classmethod
    def setUpClass(cls):
        """Creates a temporary file to use as a persistent database throughout tests in this class. Subclasses of
        :class:`TemporaryCacheClsMixin` can extend :func:`TemporaryCacheClsMixin.setUpClass` to populate the database
        """
        cls.fd, cls.path = tempfile.mkstemp()
        cls.connection = 'sqlite:///' + cls.path
        log.info('test database at %s', cls.connection)

    @classmethod
    def tearDownClass(cls):
        """Closes the connection to the database and removes the files created for it"""
        os.close(cls.fd)
        os.remove(cls.path)


class AbstractTemporaryCacheClassMixin(TemporaryConnectionMixin):
    Manager = ...

    @classmethod
    def setUpClass(cls):
        """Create temporary file"""
        if not cls.Manager:
            raise TypeError('no manager class defined')

        super(AbstractTemporaryCacheClassMixin, cls).setUpClass()

        cls.manager = cls.Manager(connection=cls.connection)

    @classmethod
    def tearDownClass(cls):
        """Closes the connection in the manager and deletes the temporary database"""
        cls.manager.session.close()

        super(AbstractTemporaryCacheClassMixin, cls).tearDownClass()


def make_temporary_cache_class_mixin(manager_cls):
    """
    :param  manager_cls:
    :type manager_cls: (str -> AbstractManager)
    :rtype: AbstractTemporaryCacheClassMixin
    """

    class TemporaryCacheClassMixin(AbstractTemporaryCacheClassMixin):
        Manager = manager_cls

    return TemporaryCacheClassMixin
