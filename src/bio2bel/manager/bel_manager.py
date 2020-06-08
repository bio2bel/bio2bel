# -*- coding: utf-8 -*-

"""Provide abstractions over BEL generation procedures."""

import os
from abc import ABC, abstractmethod

import click
from pyobo.cli_utils import verbose_option

import pybel
from pybel import to_indra_statements
from pybel.cli import host_option
from .cli_manager import CliMixin
from ..constants import directory_option

__all__ = [
    'BELManagerMixin',
    'Bio2BELMissingEdgeModelError',
]


class Bio2BELMissingEdgeModelError(TypeError):
    """Raised when the edge_model class variable is not defined."""


class BELManagerMixin(ABC, CliMixin):
    """A mixin for generating a :class:`pybel.BELGraph` representing BEL.

    First, you'll have to make sure that :mod:`pybel` is installed. This can be done with pip like:

    .. code-block:: bash

        $ pip install pybel

    To use this mixin, you need to properly implement the :class:`bio2bel.AbstractManager`, and additionally define a
    function named ``to_bel`` that returns a BEL graph.

    .. code-block:: python

        >>> from bio2bel import AbstractManager
        >>> from bio2bel.manager.bel_manager import BELManagerMixin
        >>> from pybel import BELGraph
        >>>
        >>> class MyManager(AbstractManager, BELManagerMixin):
        ...     def to_bel(self) -> BELGraph:
        ...         pass
    """

    edge_model = ...

    def count_relations(self) -> int:
        """Count the number of BEL relations generated."""
        if self.edge_model is ...:
            raise Bio2BELMissingEdgeModelError('edge_edge model is undefined/count_bel_relations is not overridden')
        elif isinstance(self.edge_model, list):
            return sum(self._count_model(m) for m in self.edge_model)
        else:
            return self._count_model(self.edge_model)

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

    def to_indra_statements(self, *args, **kwargs):
        """Dump as a list of INDRA statements.

        :rtype: List[indra.Statement]
        """
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


def add_cli_to_bel(main: click.Group) -> click.Group:
    """Add several command to main :mod:`click` function related to export to BEL."""
    @main.command()
    @click.option('-o', '--output')
    @verbose_option
    @click.pass_obj
    def write(manager: BELManagerMixin, output: str):
        """Write as BEL Script."""
        graph = manager.to_bel()
        click.echo(graph.summary_str())
        pybel.dump(graph, output)

    @main.command()
    @directory_option
    @verbose_option
    @click.pass_obj
    def write_edgelist(manager: BELManagerMixin, directory: str):
        """Write as an edge list and node list file."""
        graph = manager.to_bel()
        edgelist_path = os.path.join(directory, f'{manager.module_name}.edgelist')
        nodelist_path = os.path.join(directory, 'node_list.txt')

        node_to_id = {}

        with open(nodelist_path, 'w') as file:
            print('index', 'node', 'type', file=file)  # noqa:T001
            for i, node in enumerate(sorted(graph)):
                print(i, node, node.function, file=file)  # noqa:T001
                node_to_id[node] = i

        with open(edgelist_path, 'w') as file:
            for u, v in graph.edges():
                print(node_to_id[u], node_to_id[v], file=file)  # noqa:T001

    return main


def add_cli_upload_bel(main: click.Group) -> click.Group:  # noqa: D202
    """Add several command to main :mod:`click` function related to export to BEL."""

    @main.command()
    @host_option
    @verbose_option
    @click.pass_obj
    def upload(manager: BELManagerMixin, host: str):
        """Upload BEL to BEL Commons."""
        graph = manager.to_bel()
        pybel.to_bel_commons(graph, host=host, public=True)

    return main
