# -*- coding: utf-8 -*-

"""Tests the Bio2BEL testing utilities."""

import unittest

from bio2bel.exc import Bio2BELManagerTypeError, Bio2BELTestMissingManagerError
from bio2bel.testing import (
    AbstractTemporaryCacheClassMixin, make_temporary_cache_class_mixin,
)
from tests.constants import Manager


class TestBuild(unittest.TestCase):
    """Tests the instantiation of concrete implementation of the :class:`AbstractManager`."""

    def test_missing_manager(self):
        """Test that an incorrectly built AbstractTemporaryCacheClassMixin won't run."""

        class TestMissingManagerMixin(AbstractTemporaryCacheClassMixin):
            """An :class:`AbstractTemporaryCacheClassMixin` that is missing the Manager class variable."""

            def test_dummy(self):
                """Test dummy."""
                self.assertTrue(True)

        with self.assertRaises(Bio2BELTestMissingManagerError):
            TestMissingManagerMixin.setUpClass()

    def test_manager_wrong_type(self):
        """Test that an incorrectly built AbstractTemporaryCacheClassMixin won't run."""

        class RandomClass(object):
            """This class is not the right type and should throw a Bio2BELManagerTypeError."""

        class TestManagerWrongTypeMixin(AbstractTemporaryCacheClassMixin):
            """This is a malformed :class:`AbstractTemporaryCacheClassMixin`."""

            Manager = RandomClass

            def test_dummy(self):
                """This is a dummy test."""
                self.assertTrue(True)

        with self.assertRaises(Bio2BELManagerTypeError):
            TestManagerWrongTypeMixin.setUpClass()


class TestTesting(make_temporary_cache_class_mixin(Manager)):
    """Tests :func:`bio2bel.testing.make_temporary_cache_class_mixin`."""

    def test_has_attributes(self):
        """Test class has a manager instance."""
        self.assertTrue(hasattr(self, 'manager'))
        self.assertIsNotNone(self.manager)
        self.assertIsInstance(self.manager, Manager)


class TestPopulated(TestTesting):
    """Test the :func:`bio2bel.testing.make_temporary_cache_class_mixin`."""

    @classmethod
    def populate(cls):
        """Populate the database."""
        cls.manager.populate()

    def test_populated(self):
        """Test that the correct number of models have been added to the database."""
        self.assertEqual(5, self.manager.count_model())
