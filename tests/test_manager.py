# -*- coding: utf-8 -*-

import unittest

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base

import tests.constants
from bio2bel.abstractmanager import (
    AbstractManager,
)
from bio2bel.exc import Bio2BELMissingNameError, Bio2BELModuleCaseError
from bio2bel.models import Action
from bio2bel.testing import AbstractTemporaryCacheClassMixin, MockConnectionMixin, TemporaryConnectionMixin


class TestManagerFailures(unittest.TestCase):
    def test_missing_all_abstract(self):
        """Test that the abstract class can't be instantiated"""

        class Manager(AbstractManager):
            pass

        with self.assertRaises(TypeError):  # cant's instantiate abstract class
            Manager()

    def test_fail_instantiation_2(self):
        """Test that the abstract class can't be instantiated"""

        class Manager(AbstractManager):
            @property
            def base(self):
                return declarative_base()

        with self.assertRaises(TypeError):
            Manager()

    def test_fail_instantiation_3(self):
        """Test that the abstract class can't be instantiated"""

        class Manager(AbstractManager):
            def populate(self):
                pass

        with self.assertRaises(TypeError):
            Manager()

    def test_undefined_module_name(self):
        """Test error thrown if module name isn't set"""

        class Manager(AbstractManager):
            @property
            def base(self):
                return declarative_base()

            def populate(self):
                pass

        with self.assertRaises(Bio2BELMissingNameError):
            Manager()

    def test_module_name_case(self):
        """Test error thrown if module name is weird case"""

        class Manager(AbstractManager):
            module_name = 'TESTOMG'

            @property
            def base(self):
                return declarative_base()

            def populate(self):
                pass

        with self.assertRaises(Bio2BELModuleCaseError):
            Manager()


class TestManagerEnsure(TemporaryConnectionMixin):
    def test_type_error(self):
        with self.assertRaises(TypeError):
            tests.constants.Manager.ensure(connection=5)

    def test_build(self):
        m = tests.constants.Manager.ensure(connection=self.connection)
        self.assertIsInstance(m, tests.constants.Manager)

    def test_pass_through(self):
        m = tests.constants.Manager(connection=self.connection)
        self.assertIsInstance(m, tests.constants.Manager)

        m2 = tests.constants.Manager.ensure(connection=m)
        self.assertIsInstance(m, tests.constants.Manager)
        self.assertEqual(m, m2)


class TestConnectionDropping(MockConnectionMixin, AbstractTemporaryCacheClassMixin):
    Manager = tests.constants.Manager

    def test_no_exist(self):
        """Checks if the database gets dropped that stuff breaks"""

        with self.mock_global_connection:  # don't want to worry about that drop_app hook
            self.assertEqual(0, Action.count())
            self.manager.drop_all()
            self.assertEqual(1, Action.count())

        with self.assertRaises(OperationalError):
            self.manager.get_model_by_model_id(5)


class TestConnectionLoading(AbstractTemporaryCacheClassMixin):
    Manager = tests.constants.Manager

    def test_repr(self):
        self.assertEqual('<TestManager url={}>'.format(self.connection), repr(self.manager))

    def test_connection(self):
        self.assertIsInstance(self.connection, str)

    def test_manager_passes(self):
        self.assertEqual(self.connection, self.manager.connection)

    def test_get_missing_model(self):
        self.manager.populate()

        self.assertIsNone(self.manager.get_model_by_model_id(0))
        self.assertIsNone(self.manager.get_model_by_model_id(1))
        self.assertIsNone(self.manager.get_model_by_model_id(2))
        self.assertIsNone(self.manager.get_model_by_model_id(3))
        self.assertIsNone(self.manager.get_model_by_model_id(4))
        self.assertIsNone(self.manager.get_model_by_model_id(150))


if __name__ == '__main__':
    unittest.main()
