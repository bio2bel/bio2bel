# -*- coding: utf-8 -*-

import logging
import unittest

from bio2bel.models import Action, create_all
from bio2bel.testing import MockConnectionMixin, TemporaryConnectionMethodMixin
from tests.constants import Manager

log = logging.getLogger(__name__)


class TestActionUnmocked(TemporaryConnectionMethodMixin, MockConnectionMixin):
    def test_action(self):
        manager = Manager(connection=self.connection)
        create_all(manager.engine)

        self.assertEqual(0, Action.count(session=manager.session))

        manager.populate()

        self.assertEqual(1, Action.count(session=manager.session))
        actions = Action.ls(session=manager.session)
        action = actions[0]
        self.assertEqual(manager.module_name, action.resource)
        self.assertEqual('populate', action.action)


    def test_action_mocked(self):
        with self.mock_global_connection:
            self.assertEqual(0, Action.count())

            manager = Manager(connection=self.connection)
            manager.populate()

            self.assertEqual(1, Action.count())
            actions = Action.ls()
            action = actions[0]
            self.assertEqual(manager.module_name, action.resource)
            self.assertEqual('populate', action.action)


if __name__ == '__main__':
    unittest.main()
