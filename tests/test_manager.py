# -*- coding: utf-8 -*-

import unittest

from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declarative_base

from bio2bel.constants import DEFAULT_CACHE_CONNECTION
from bio2bel.manager import Manager as BaseManager


class TestManagerFailures(unittest.TestCase):
    def test_manager_fails_module(self):
        class Manager(BaseManager):
            pass

        with self.assertRaises(ValueError):
            Manager()

    def test_manager_fails_base(self):
        class Manager(BaseManager):
            module_name = 'test'

        with self.assertRaises(ValueError):
            Manager()


class TestConnectionLoading(unittest.TestCase):
    def make_manager(self, connection=None):
        TestBase = declarative_base()

        class Model(TestBase):
            __tablename__ = 'test_test'
            id = Column(Integer, primary_key=True)

        class Manager(BaseManager):
            module_name = 'test'
            Base = TestBase

        return Manager(connection=connection)

    def test_manager_passes(self):
        manager = self.make_manager()
        self.assertEqual(DEFAULT_CACHE_CONNECTION, manager.connection)


if __name__ == '__main__':
    unittest.main()
