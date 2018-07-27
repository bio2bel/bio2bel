# -*- coding: utf-8 -*-

"""Tests the CLI generation utilities."""

from bio2bel.testing import MockConnectionMixin
from click.testing import CliRunner
from sqlalchemy.exc import OperationalError
from tests.constants import Manager


class TestCli(MockConnectionMixin):
    """Tests the CLI generator."""

    def setUp(self):
        """Set up a CliRunner and an accompanying CLI for each test."""
        self.runner = CliRunner()
        self.main = Manager.get_cli()

    def test_populate(self):
        """Test the population function can be run."""
        args = [
            '--connection',
            self.connection,
            'populate'
        ]
        self.runner.invoke(self.main, args)

        manager = Manager(connection=self.connection)
        self.assertEqual(5, manager.count_model())

        args = [
            '--connection',
            self.connection,
            'drop',
            '-y'
        ]
        self.runner.invoke(self.main, args)

        with self.assertRaises(OperationalError):
            manager.count_model()
