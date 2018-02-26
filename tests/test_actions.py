# -*- coding: utf-8 -*-

import logging
import os
import tempfile
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bio2bel.models import Action, Base
from bio2bel.utils import bio2bel_populater
from tests.constants import MockConnectionMixin

log = logging.getLogger(__name__)


class TestActions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Create temporary file"""
        cls.fd, cls.path = tempfile.mkstemp()
        cls.connection = 'sqlite:///' + cls.path
        engine = create_engine(cls.connection)
        Base.metadata.create_all(engine, checkfirst=True)

        Session = sessionmaker(bind=engine)
        cls.session = Session()

    @classmethod
    def tearDownClass(cls):
        """Closes the connection in the manager and deletes the temporary database"""
        cls.session.close()
        os.close(cls.fd)
        os.remove(cls.path)

    def test_decorator(self):
        self.assertEqual(0, len(Action.ls(session=self.session)))

        @bio2bel_populater('test', session=self.session)
        def populate_something():
            """A dummy function that represents a population function. May even be a class function."""

        populate_something()

        actions = Action.ls(session=self.session)
        self.assertEqual(1, len(actions))
        action = actions[0]

        self.assertIsNotNone(action)
        self.assertEqual('test', action.resource)


class TestActionMock(MockConnectionMixin):
    def test_decorator(self):
        with self.mock_global_connection:
            self.assertEqual(0, len(Action.ls()), msg='should not already have entries')

            @bio2bel_populater('test')
            def populate_something():
                """A dummy function that represents a population function. May even be a class function."""

            populate_something()

            actions = Action.ls()
            self.assertEqual(1, len(actions), msg='entry was not stored')
            action = actions[0]

            self.assertIsNotNone(action)
            self.assertEqual('test', action.resource)


if __name__ == '__main__':
    unittest.main()
