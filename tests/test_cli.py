# -*- coding: utf-8 -*-

from click.testing import CliRunner
from sqlalchemy.exc import OperationalError

from bio2bel.testing import MockConnectionMixin
from bio2bel.cli_utils import build_cli
from tests.constants import Manager


class TestCli(MockConnectionMixin):
    def setUp(self):
        self.runner = CliRunner()
        self.main = build_cli(Manager)

    def test_populate(self):
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
