# -*- coding: utf-8 -*-

"""Provide abstractions over BEL generation procedures."""

from abc import ABC, abstractmethod
import logging
import sys

import click
from pybel import Manager, to_bel, to_database

from .cli_manager import CliMixin

log = logging.getLogger(__name__)

__all__ = [
    'BELManagerMixin',
]


class BELManagerMixin(ABC, CliMixin):
    """This mixin adds functions for making a BEL from a repository.

    *How to Use This Mixin*

    1. Either include it as a second inheriting class after :class:`AbstractManager` (this is how mixins are usually
    used):

    ..code-block:: python


        from bio2bel import AbstractManager
        from bio2bel.bel_manager import BELManagerMixin

        class MyManager(AbstractManager, BELManagerMixin):
            ...


    1. Or subclass it directly, since it also inherits from :class:`AbstractManager`, like:

    ..code-block:: python

        from bio2bel.bel_manager import BELManagerMixin

        class MyManager(BELManagerMixin):
            ...
    """

    @abstractmethod
    def to_bel(self, *args, **kwargs):
        """Convert the database to BEL.

        :rtype: pybel.BELGraph
        """

    @staticmethod
    def _cli_add_to_bel(main):
        """Add the export BEL command.

        :type main: click.core.Group
        :rtype: click.core.Group
        """
        return add_cli_to_bel(main)

    @staticmethod
    def _cli_add_upload_bel(main):
        """Add the upload BEL command.

        :type main: click.core.Group
        :rtype: click.core.Group
        """
        return add_cli_upload_bel(main)

    @classmethod
    def get_cli(cls):
        """Get a :mod:`click` main function to use as a command line interface.

        :rtype: click.core.Group
        """
        main = super().get_cli()

        @main.group()
        def bel():
            """Manage BEL."""

        cls._cli_add_to_bel(bel)
        cls._cli_add_upload_bel(bel)

        return main


def add_cli_to_bel(main):
    """Add several command to main :mod:`click` function related to export to BEL.

    :param click.core.Group main: A click-decorated main function
    :rtype: click.core.Group
    """
    @main.command()
    @click.option('-o', '--output', type=click.File('w'), default=sys.stdout)
    @click.pass_obj
    def write(manager, output):
        """Write as BEL Script."""
        graph = manager.to_bel()
        to_bel(graph, output)


def add_cli_upload_bel(main):
    """Add several command to main :mod:`click` function related to export to BEL.

    :param click.core.Group main: A click-decorated main function
    :rtype: click.core.Group
    """
    @main.command()
    @click.option('-c', '--connection')
    @click.pass_obj
    def upload(manager, connection):
        """Upload BEL to network store."""
        graph = manager.to_bel()
        manager = Manager(connection=connection)
        to_database(graph, manager=manager)

    return main
