# -*- coding: utf-8 -*-

import logging
import os
import tempfile
import unittest
from unittest import mock

log = logging.getLogger(__name__)


class MockConnectionMixin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Create temporary file"""
        cls.fd, cls.path = tempfile.mkstemp()
        cls.connection = 'sqlite:///' + cls.path

        def mock_connection():
            return cls.connection

        cls.mock_global_connection = mock.patch('bio2bel.models.get_global_connection', mock_connection)
        cls.mock_module_connection = mock.patch('bio2bel.utils.get_connection', mock_connection)

    @classmethod
    def tearDownClass(cls):
        """Closes the connection in the manager and deletes the temporary database"""
        os.close(cls.fd)
        os.remove(cls.path)
