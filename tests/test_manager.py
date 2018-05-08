# -*- coding: utf-8 -*-

import unittest

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base

import tests.constants
from bio2bel import AbstractManager
from bio2bel.exc import Bio2BELMissingNameError, Bio2BELModuleCaseError
from bio2bel.models import Action
from bio2bel.testing import AbstractTemporaryCacheClassMixin, MockConnectionMixin, TemporaryConnectionMixin
from tests.constants import NUMBER_TEST_MODELS

class TestManagerFailures(unittest.TestCase):
    """Test improperly implement AbstractManager."""

    def test_missing_all_abstract(self):
        """Test that the abstract class can't be instantiated."""

        class Manager(AbstractManager):
            """An incompletely implement AbstractManager"""

        with self.assertRaises(TypeError):  # cant's instantiate abstract class
            Manager()

    def test_fail_instantiation_2(self):
        """Test that the abstract class can't be instantiated."""
        base = declarative_base()

        class Manager(AbstractManager):
            """An incompletely implement AbstractManager"""

            @property
            def _base(self):
                return base

        with self.assertRaises(TypeError):
            Manager()

    def test_fail_instantiation_3(self):
        """Test that the abstract class can't be instantiated."""

        class Manager(AbstractManager):
            """An incompletely implement AbstractManager."""

            def populate(self):
                """Populate the database."""

        with self.assertRaises(TypeError):
            Manager()

    def test_undefined_module_name(self):
        """Test error thrown if module name isn't set."""
        base = declarative_base()

        class Manager(AbstractManager):
            """An improperly implemented AbstractManager that is missing the module_name class variable."""

            @property
            def _base(self):
                return base

            def is_populated(self):
                """Check if the database is already populated."""

            def populate(self):
                """Populate the database."""

        with self.assertRaises(Bio2BELMissingNameError):
            Manager()

    def test_module_name_case(self):
        """Test error thrown if module name is weird case."""
        base = declarative_base()

        class Manager(AbstractManager):
            module_name = 'TESTOMG'

            @property
            def _base(self):
                return base

            def is_populated(self):
                """Check if the database is already populated."""

            def populate(self):
                """Populate the database."""

        with self.assertRaises(Bio2BELModuleCaseError):
            Manager()


class TestManagerEnsure(TemporaryConnectionMixin):
    """Tests the ensure function of an AbstractManager works properly."""

    def test_type_error(self):
        """Test that the connection's type is checked properly."""
        with self.assertRaises(TypeError):
            tests.constants.Manager.ensure(connection=5)

    def test_build(self):
        """Test that a string can be passed."""
        m = tests.constants.Manager.ensure(connection=self.connection)
        self.assertIsInstance(m, tests.constants.Manager)

    def test_pass_through(self):
        """Test that a manager can be passed."""
        m = tests.constants.Manager(connection=self.connection)
        self.assertIsInstance(m, tests.constants.Manager)

        m2 = tests.constants.Manager.ensure(connection=m)
        self.assertIsInstance(m, tests.constants.Manager)
        self.assertEqual(m, m2)


class TestConnectionDropping(MockConnectionMixin, AbstractTemporaryCacheClassMixin):
    """Tests dropping the database."""
    Manager = tests.constants.Manager

    def test_no_exist(self):
        """Check if the database gets dropped that stuff breaks."""

        with self.mock_global_connection:  # don't want to worry about that drop_app hook
            self.assertEqual(0, Action.count())
            self.manager.drop_all()
            self.assertEqual(1, Action.count())

        with self.assertRaises(OperationalError):
            self.manager.get_model_by_model_id(5)


class TestConnectionLoading(AbstractTemporaryCacheClassMixin):
    """Tests the connection is loaded properly."""

    Manager = tests.constants.Manager

    def test_connection(self):
        """Tests the type of the connection"""
        self.assertIsNotNone(self.connection)
        self.assertIsInstance(self.connection, str)

    def test_manager_passes(self):
        """Test the connection is inside the manager properly"""
        self.assertEqual(self.connection, self.manager.connection)

    def test_repr(self):
        """Test the repr function of the AbstractManager."""
        self.assertEqual('<TestManager url={}>'.format(self.connection), repr(self.manager))

    def test_get_missing_model(self):
        """Test population."""
        self.assertFalse(self.manager.is_populated())
        self.manager.populate()
        self.assertTrue(self.manager.is_populated())

        self.assertEqual(NUMBER_TEST_MODELS, self.manager.count_model())

        self.assertIsNone(self.manager.get_model_by_model_id(0))
        self.assertIsNone(self.manager.get_model_by_model_id(1))
        self.assertIsNone(self.manager.get_model_by_model_id(2))
        self.assertIsNone(self.manager.get_model_by_model_id(3))
        self.assertIsNone(self.manager.get_model_by_model_id(4))
        self.assertIsNone(self.manager.get_model_by_model_id(150))


if __name__ == '__main__':
    unittest.main()
