# -*- coding: utf-8 -*-

"""Provide abstractions over BEL generation procedures."""

import logging
import sys
from abc import ABC, abstractmethod
from typing import List

import click

import pybel
from pybel import to_bel, to_indra_statements
from .cli_manager import CliMixin

__all__ = [
    'BELManagerMixin',
]

log = logging.getLogger(__name__)


class BELManagerMixin(ABC, CliMixin):
    """A mixin for generating a :class:`pybel.BELGraph` representing BEL.

    First, you'll have to make sure that :mod:`pybel` is installed. This can be done with pip like:

    .. code-block:: bash

        $ pip install pybel

    To use this mixin, you need to properly implement the AbstractManager, and additionally define a function
    named ``to_bel`` that returns a BEL graph.

    .. code-block:: python

        >>> from bio2bel import AbstractManager
        >>> from bio2bel.manager.bel_manager import BELManagerMixin
        >>> from pybel import BELGraph
        >>>
        >>> class MyManager(AbstractManager, BELManagerMixin):
        ...     def to_bel(self) -> BELGraph:
        ...         pass
    """

    @abstractmethod
    def to_bel(self, *args, **kwargs) -> pybel.BELGraph:
        """Convert the database to BEL.

        Example implementation outline:

        .. code-block:: python

            from bio2bel import AbstractManager
            from bio2bel.manager.bel_manager import BELManagerMixin
            from pybel import BELGraph
            from .models import Interaction

            class MyManager(AbstractManager, BELManagerMixin):
                module_name = 'mirtarbase'
                def to_bel(self):
                    rv = BELGraph(
                        name='miRTarBase',
                        version='1.0.0',
                    )

                    for interaction in self.session.query(Interaction):
                        mirna = mirna_dsl('mirtarbase', interaction.mirna.mirtarbase_id)
                        rna = rna_dsl('hgnc', interaction.target.hgnc_id)

                        rv.add_qualified_edge(
                            mirna,
                            rna,
                            DECREASES,
                            ...
                        )

                    return rv
        """

    def to_indra_statements(self, *args, **kwargs) -> List['indra.Statement']:
        """Dump as a list of INDRA statements."""
        graph = self.to_bel(*args, **kwargs)
        return to_indra_statements(graph)

    @staticmethod
    def _cli_add_to_bel(main: click.Group) -> click.Group:
        """Add the export BEL command."""
        return add_cli_to_bel(main)

    @staticmethod
    def _cli_add_upload_bel(main: click.Group) -> click.Group:
        """Add the upload BEL command."""
        return add_cli_upload_bel(main)

    @classmethod
    def get_cli(cls) -> click.Group:
        """Get a :mod:`click` main function with added BEL commands."""
        main = super().get_cli()

        @main.group()
        def bel():
            """Manage BEL."""

        cls._cli_add_to_bel(bel)
        cls._cli_add_upload_bel(bel)

        return main


def add_cli_to_bel(main: click.Group) -> click.Group:  # noqa: D202
    """Add several command to main :mod:`click` function related to export to BEL."""

    @main.command()
    @click.option('-o', '--output', type=click.File('w'), default=sys.stdout)
    @click.pass_obj
    def write(manager: BELManagerMixin, output):
        """Write as BEL Script."""
        graph = manager.to_bel()
        to_bel(graph, output)
        click.echo(graph.summary_str())

    return main


def add_cli_upload_bel(main: click.Group) -> click.Group:  # noqa: D202
    """Add several command to main :mod:`click` function related to export to BEL."""

    @main.command()
    @click.option('-c', '--connection')
    @click.pass_obj
    def upload(manager: BELManagerMixin, connection):
        """Upload BEL to network store."""
        graph = manager.to_bel()
        pybel_manager = pybel.Manager(connection=connection)
        pybel.to_database(graph, manager=pybel_manager)

    return main
