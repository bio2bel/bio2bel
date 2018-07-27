# -*- coding: utf-8 -*-

"""Test that actions are stored properly for population and dropping."""

import logging

from bio2bel.models import Action, create_all
from bio2bel.testing import MockConnectionMixin, TemporaryConnectionMethodMixin
from tests.constants import Manager

log = logging.getLogger(__name__)


class TestActions(TemporaryConnectionMethodMixin, MockConnectionMixin):
    """Test actions."""

    def test_action(self):
        """Test actions with live database."""
        manager = Manager(connection=self.connection)
        create_all(manager.engine)

        self.assertEqual(0, Action.count(session=manager.session))

        self.assertFalse(manager.is_populated())
        manager.populate(return_true=True)
        self.assertTrue(manager.is_populated())

        # just check this tiny implementation detail
        self.assertEqual(manager.last_populate_kwargs, {'return_true': True})

        self.assertEqual(1, Action.count(session=manager.session))
        actions = Action.ls(session=manager.session)
        action = actions[0]
        self.assertEqual(manager.module_name, action.resource)
        self.assertEqual('populate', action.action)

    def test_action_mocked(self):
        """Test actions with mocked database."""
        with self.mock_global_connection:
            self.assertEqual(0, Action.count())

            manager = Manager(self.connection)
            self.assertFalse(manager.is_populated())
            manager.populate()
            self.assertTrue(manager.is_populated())

            self.assertEqual(1, Action.count())
            actions = Action.ls()
            action = actions[0]
            self.assertEqual(manager.module_name, action.resource)
            self.assertEqual('populate', action.action)
