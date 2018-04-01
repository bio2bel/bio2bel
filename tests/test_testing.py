# -*- coding: utf-8 -*-

import unittest

from bio2bel.exc import Bio2BELManagerTypeError, Bio2BELTestMissingManagerError
from bio2bel.testing import (
    AbstractTemporaryCacheClassMixin, make_temporary_cache_class_mixin,
)
from tests.constants import Manager


class TestBuild(unittest.TestCase):
    def test_missing_manager(self):
        """Test that an incorrectly built AbstractTemporaryCacheClassMixin won't run"""

        class TestMixin(AbstractTemporaryCacheClassMixin):
            def test_dummy(self):
                self.assertTrue(True)

        with self.assertRaises(Bio2BELTestMissingManagerError):
            TestMixin.setUpClass()

    def test_manager_wrong_type(self):
        """Test that an incorrectly built AbstractTemporaryCacheClassMixin won't run"""

        class RandomClass(object):
            pass

        class TestMixin(AbstractTemporaryCacheClassMixin):
            Manager = RandomClass

            def test_dummy(self):
                self.assertTrue(True)

        with self.assertRaises(Bio2BELManagerTypeError):
            TestMixin.setUpClass()


class TestTesting(make_temporary_cache_class_mixin(Manager)):
    """Tests :func:`bio2bel.testing.make_temporary_cache_class_mixin`"""

    def test_has_attributes(self):
        """Test class has a manager instance"""
        self.assertTrue(hasattr(self, 'manager'))
        self.assertIsNotNone(self.manager)
        self.assertIsInstance(self.manager, Manager)


class TestPopulated(TestTesting):
    """Tests :func:`bio2bel.testing.make_temporary_cache_class_mixin`"""

    @classmethod
    def populate(cls):
        cls.manager.populate()

    def test_populated(self):
        self.assertEqual(5, self.manager.count_model())
