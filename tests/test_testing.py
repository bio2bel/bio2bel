# -*- coding: utf-8 -*-

from bio2bel.testing import make_temporary_cache_class_mixin
from tests.constants import Manager


class TestTesting(make_temporary_cache_class_mixin(Manager)):
    def test_has_attributes(self):
        """Test class has a manager instance"""
        self.assertTrue(hasattr(self, 'manager'))
        self.assertIsNotNone(self.manager)
        self.assertIsInstance(self.manager, Manager)
