# -*- coding: utf-8 -*-

"""Provides abstractions over the generation of a command line interface."""

import logging

import click

from ..version import get_version

__all__ = [
    'CliMixin',
]


class CliMixin:
    """A mixin for building a CLI.

    Must be used as a mixin for a subclass of :class:`bio2bel.manager.connection_manager.ConnectionManager`.
    """

    @classmethod
    def get_cli(cls) -> click.Group:
        """Build a :mod:`click` CLI main function.

        :param Type[AbstractManager] cls: A Manager class
        :return: The main function for click
        """
        group_help = f'Default connection at {cls._get_connection()}\n\nusing Bio2BEL v{get_version()}'

        @click.group(help=group_help)
        @click.option('-c', '--connection', default=cls._get_connection(), show_default=True)
        @click.pass_context
        def main(ctx, connection):
            """Bio2BEL CLI."""
            logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            logging.getLogger('bio2bel.utils').setLevel(logging.WARNING)
            ctx.obj = cls(connection=connection)

        return main
