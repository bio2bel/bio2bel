# -*- coding: utf-8 -*-

"""ComPath is a project for using gene-centric (and later other types of entities) to compare pathway knowledge.

This package provides guidelines, tutorials, and tools for making standardized ``compath`` packages as well as a
unifying framework for integrating them.

Installation
------------
Easiest
~~~~~~~
Download the latest stable code from `PyPI <https://pypi.org/compath_utils>`_ with:

.. code-block:: sh

   $ python3 -m pip install compath-utils

Get the Latest
~~~~~~~~~~~~~~~
Download the most recent code from `GitHub <https://github.com/compath/compath_utils>`_ with:

.. code-block:: sh

   $ python3 -m pip install git+https://github.com/compath/compath_utils.git

For Developers
~~~~~~~~~~~~~~
Clone the repository from `GitHub <https://github.com/compath/compath_utils>`_ and install in editable mode with:

.. code-block:: sh

   $ git clone https://github.com/compath/compath_utils.git
   $ cd compath_utils
   $ python3 -m pip install -e .

Testing
-------
ComPath Utils is tested with Python3 on Linux using `Travis CI <https://travis-ci.org/compath/compath_utils>`_.
"""

from __future__ import annotations

import itertools as itt
import logging
import os
from abc import abstractmethod
from collections import Counter
from typing import ClassVar, Collection, Iterable, List, Mapping, Optional, Set, Tuple, Type

import click
import pandas as pd
from sqlalchemy import Column
from tqdm import tqdm

import pybel.dsl
from pybel import BELGraph
from pybel.manager.models import Namespace, NamespaceEntry
from .abstract_manager import AbstractManager
from .bel_manager import BELManagerMixin
from .flask_manager import FlaskMixin
from .models import SpeciesMixin
from .namespace_manager import BELNamespaceManagerMixin

__all__ = [
    'CompathManager',
    'CompathPathwayMixin',
    'CompathProteinMixin',
]

logger = logging.getLogger(__name__)


class CompathManagerTypeError(TypeError):
    """Raised when trying to instantiate an improperly implemented ComPath manager."""


class CompathManagerPathwayModelError(CompathManagerTypeError):
    """Raised when missing an appropriate pathway_model class variable."""


class CompathManagerPathwayIdentifierError(CompathManagerTypeError):
    """Raised when missing an appropriate pathway_model_standard_identifer class variable."""


class CompathManagerProteinModelError(CompathManagerTypeError):
    """Raised when missing an appropriate protein_model class variable."""


class CompathPathwayMixin:
    """This is the abstract class that the Pathway model in a ComPath repository should extend."""

    #: The database (Identifiers.org) prefix for this pathway
    prefix: str
    #: The local unique identifier for this pathway
    identifier: ClassVar[Column]
    #: The preferred label for this pathway
    name: ClassVar[Column]
    #: The proteins that this pathway is connected to
    proteins: List[CompathProteinMixin]
    #: The species for which the pathway is relevant
    species: SpeciesMixin

    def get_gene_set(self) -> Set[str]:
        """Return the set of HGNC gene symbols of human genes associated with the pathway (gene set)."""
        return {
            protein.hgnc_symbol
            for protein in self.proteins
            if protein.hgnc_symbol
        }

    @property
    def url(self) -> str:
        """Return the URL to the resource, usually based in the identifier for this pathway."""
        return f'https://identifiers.org/{self.prefix}:{self.identifier}'

    def to_pybel(self) -> pybel.dsl.BiologicalProcess:
        """Serialize this pathway to a PyBEL node."""
        return pybel.dsl.BiologicalProcess(
            namespace=self.prefix,
            name=self.name,
            identifier=self.identifier,
        )

    def add_to_bel_graph(self, graph: pybel.BELGraph) -> Set[str]:
        """Add the pathway to a BEL graph."""
        pathway_node = self.to_pybel()
        return {
            graph.add_part_of(protein.to_pybel(), pathway_node)
            for protein in self.proteins
        }

    def __repr__(self) -> str:
        return f'{self.prefix}:{self.identifier} ! {self.name}'


class CompathProteinMixin:
    """This is an abstract class that the Protein model in a ComPath repository should extend."""

    hgnc_id: ClassVar[Column]
    hgnc_symbol: ClassVar[Column]
    pathways: List[CompathPathwayMixin]

    def get_pathways_ids(self) -> Set[str]:
        """Get the identifiers of the pathways associated with this protein."""
        return {
            pathway.identifier
            for pathway in self.pathways
        }

    @abstractmethod
    def to_pybel(self) -> pybel.dsl.Protein:
        """Serialize this protein to a PyBEL node."""
        raise NotImplementedError


class CompathManager(AbstractManager, BELNamespaceManagerMixin, BELManagerMixin, FlaskMixin):
    """This is the abstract class that all ComPath managers should extend."""

    #: The standard pathway SQLAlchemy model
    pathway_model: Type[CompathPathwayMixin]

    #: The standard protein SQLAlchemy model
    protein_model: Type[CompathProteinMixin]

    def __init__(self, *args, **kwargs):
        """Doesn't let this class get instantiated if the pathway_model."""
        if not hasattr(self, 'pathway_model'):
            raise CompathManagerPathwayModelError('did not set class-level variable pathway_model')
        elif not issubclass(self.pathway_model, CompathPathwayMixin):
            raise TypeError(f'{self.pathway_model} should inherit from {CompathPathwayMixin}')
        if not hasattr(self, 'protein_model'):
            raise CompathManagerProteinModelError('did not set class-level variable protein_model')
        elif not issubclass(self.protein_model, CompathProteinMixin):
            raise TypeError(f'{self.protein_model} should inherit from {CompathProteinMixin}')

        if not hasattr(self, 'namespace_model') or not self.namespace_model:
            self.namespace_model = self.pathway_model

        if not hasattr(self,
                       'flask_admin_models') or not self.flask_admin_models:  # set flask models if not already set
            self.flask_admin_models = [self.pathway_model, self.protein_model]

        super().__init__(*args, **kwargs)

    def is_populated(self) -> bool:
        """Check if the database is already populated."""
        return 0 < self._count_model(self.pathway_model) and 0 < self._count_model(self.protein_model)

    def _query_pathway(self):
        return self.session.query(self.pathway_model)

    def count_pathways(self) -> int:
        """Count the pathways in the database."""
        return self._query_pathway().count()

    def list_pathways(self) -> List[CompathPathwayMixin]:
        """List the pathways in the database."""
        return self._query_pathway().all()

    def _query_protein(self):
        return self.session.query(self.protein_model)

    def count_proteins(self) -> int:
        """Count the proteins in the database."""
        return self._query_protein().count()

    def list_proteins(self) -> List[CompathProteinMixin]:
        """List the proteins in the database."""
        return self._query_protein().all()

    def get_protein_by_hgnc_symbol(self, hgnc_symbol: str) -> Optional[CompathProteinMixin]:
        """Get a protein by its HGNC gene symbol.

        :param hgnc_symbol: HGNC gene symbol
        """
        return self._query_protein().filter(self.protein_model.hgnc_symbol == hgnc_symbol).one_or_none()

    def summarize(self) -> Mapping[str, int]:
        """Summarize the database."""
        return dict(
            pathways=self.count_pathways(),
            proteins=self.count_proteins(),
        )

    def _query_proteins_in_hgnc_list(self, gene_set: Iterable[str]) -> List[CompathProteinMixin]:
        """Return the proteins in the database within the gene set query.

        :param gene_set: hgnc symbol lists
        :return: list of proteins models
        """
        return self._query_protein().filter(self.protein_model.hgnc_symbol.in_(gene_set)).all()

    def query_similar_hgnc_symbol(self, hgnc_symbol: str, top: Optional[int] = None) -> Optional[CompathPathwayMixin]:
        """Filter genes by hgnc symbol.

        :param hgnc_symbol: hgnc_symbol to query
        :param top: return only X entries
        """
        similar_genes = self._query_protein().filter(self.protein_model.hgnc_symbol.contains(hgnc_symbol)).all()

        if top:
            return similar_genes[:top]

        return similar_genes

    def query_similar_pathways(self, pathway_name: str, top: Optional[int] = None) -> List[Tuple[str, str]]:
        """Filter pathways by name.

        :param pathway_name: pathway name to query
        :param top: return only X entries
        """
        similar_pathways = self._query_pathway().filter(self.pathway_model.name.contains(pathway_name)).all()

        similar_pathways = [
            (pathway.resource_id, pathway.name)
            for pathway in similar_pathways
        ]

        if top:
            return similar_pathways[:top]

        return similar_pathways

    def query_gene(self, hgnc_gene_symbol: str) -> List[Tuple[str, str, int]]:
        """Return the pathways associated with a gene.

        :param hgnc_gene_symbol: HGNC gene symbol
        :return: associated with the gene
        """
        protein = self.get_protein_by_hgnc_symbol(hgnc_gene_symbol)
        if protein is None:
            return []

        pathway_ids = protein.get_pathways_ids()
        enrichment_results = []

        for pathway_id in pathway_ids:
            pathway = self.get_pathway_by_id(pathway_id)
            if pathway is None:
                continue
            pathway_gene_set = pathway.get_gene_set()  # Pathway gene set
            enrichment_results.append((pathway_id, pathway.name, len(pathway_gene_set)))

        return enrichment_results

    def query_gene_set(self, hgnc_gene_symbols: Iterable[str]) -> Mapping[str, Mapping]:
        """Calculate the pathway counter dictionary.

        :param hgnc_gene_symbols: An iterable of HGNC gene symbols to be queried
        :return: Enriched pathways with mapped pathways/total
        """
        proteins = self._query_proteins_in_hgnc_list(hgnc_gene_symbols)

        pathways_lists = [
            protein.get_pathways_ids()
            for protein in proteins
        ]

        # Flat the pathways lists and applies Counter to get the number matches in every mapped pathway
        pathway_counter = Counter(itt.chain.from_iterable(pathways_lists))

        enrichment_results = dict()

        for pathway_id, proteins_mapped in pathway_counter.items():
            pathway = self.get_pathway_by_id(pathway_id)
            if pathway is None:
                logger.warning('could not find pathway %s', pathway_id)
                continue

            pathway_gene_set = pathway.get_gene_set()  # Pathway gene set

            enrichment_results[pathway_id] = {
                "pathway_id": pathway_id,
                "pathway_name": pathway.name,
                "mapped_proteins": proteins_mapped,
                "pathway_size": len(pathway_gene_set),
                "pathway_gene_set": pathway_gene_set,
            }

        return enrichment_results

    def get_pathway_by_id(self, pathway_id: str) -> Optional[CompathPathwayMixin]:
        """Get a pathway by its database-specific identifier. Not to be confused with the standard column called "id".

        :param pathway_id: Pathway identifier
        """
        return self._query_pathway().filter(self.pathway_model.identifier == pathway_id).one_or_none()

    def get_pathway_by_name(self, pathway_name: str) -> Optional[CompathPathwayMixin]:
        """Get a pathway by its database-specific name.

        :param pathway_name: Pathway name
        """
        pathways = self._query_pathway().filter(self.pathway_model.name == pathway_name).all()

        if not pathways:
            return None

        return pathways[0]

    def get_all_pathways(self) -> List[CompathPathwayMixin]:
        """Get all pathways stored in the database."""
        return self._query_pathway().all()

    def get_all_pathway_names(self) -> List[str]:
        """Get all pathway names stored in the database."""
        return [
            pathway.name
            for pathway in self._query_pathway().all()
        ]

    def get_all_hgnc_symbols(self) -> Set[str]:
        """Return the set of genes present in all Pathways."""
        return {
            gene.hgnc_symbol
            for pathway in self.get_all_pathways()
            for gene in pathway.proteins
            if pathway.proteins
        }

    def get_pathway_size_distribution(self) -> Mapping[str, Tuple[str, int]]:
        """Return pathway sizes."""
        pathways = self.get_all_pathways()

        return {
            pathway.identifier: (pathway.name, len(pathway.proteins))
            for pathway in pathways
            if pathway.proteins
        }

    def query_pathway_by_name(self, query: str, limit: Optional[int] = None) -> List[CompathPathwayMixin]:
        """Return all pathways having the query in their names.

        :param query: query string
        :param limit: limit result query
        """
        q = self._query_pathway().filter(self.pathway_model.name.contains(query))

        if limit:
            q = q.limit(limit)

        return q.all()

    def export_gene_sets(self, use_tqdm: bool = True) -> Mapping[str, Set[str]]:
        """Return the pathway - genesets mapping."""
        it = self._query_pathway().all()
        if use_tqdm:
            it = tqdm(it, total=self._query_pathway().count())
        return {
            pathway.name: {
                protein.hgnc_symbol
                for protein in pathway.proteins
                if protein.hgnc_symbol
            }
            for pathway in it
        }

    def get_gene_distribution(self) -> Counter:
        """Return the proteins in the database within the gene set query.

        :return: pathway sizes
        """
        return Counter(
            protein.hgnc_symbol
            for pathway in self.get_all_pathways()
            if pathway.proteins
            for protein in pathway.proteins
            if protein.hgnc_symbol
        )

    def _create_namespace_entry_from_model(self, model: CompathPathwayMixin, namespace: Namespace) -> NamespaceEntry:
        """Create a namespace entry from the model."""
        return NamespaceEntry(encoding='B', name=model.name, identifier=model.identifier, namespace=namespace)

    @staticmethod
    def _add_cli_export(main: click.Group) -> click.Group:  # noqa: D202
        """Add the pathway export function to the CLI."""

        @main.command()
        @click.option('-d', '--directory', default=os.getcwd(), help='Defaults to CWD',
                      type=click.Path(dir_okay=True, exists=True, file_okay=False))
        @click.option('-f', '--fmt', default='excel', type=click.Choice(['xlsx', 'tsv']), show_default=True)
        @click.pass_obj
        def export_gene_sets(manager: CompathManager, directory: str, fmt: str):
            """Export all pathway - gene info to a excel file."""
            # https://stackoverflow.com/questions/19736080/creating-dataframe-from-a-dictionary-where-entries-have-different-lengths
            gene_sets_dict = manager.export_gene_sets()

            path = os.path.join(directory, f'{manager.module_name}_gene_sets.{fmt}')
            if fmt == 'xlsx' or format is None:
                write_dict(gene_sets_dict, path)
            elif fmt == 'tsv':
                with open(path, 'w') as file:
                    for key, values in gene_sets_dict.items():
                        for value in values:
                            print(key, value, file=file, sep='\t')

        return main

    @classmethod
    def get_cli(cls) -> click.Group:
        """Get a :mod:`click` main function to use as a command line interface."""
        main = super().get_cli()
        cls._add_cli_export(main)
        return main

    def get_pathway_graph(self, pathway_id: str) -> Optional[BELGraph]:
        """Return a new graph corresponding to the pathway.

        :param pathway_id: A pathway identifier
        """
        pathway = self.get_pathway_by_id(pathway_id)
        if pathway is None:
            return None

        graph = BELGraph(name=f'{pathway.name} graph')
        pathway.add_to_bel_graph(graph)
        return graph

    def to_bel(self) -> BELGraph:
        """Serialize the database as BEL."""
        graph = BELGraph(
            name=f'Pathway Definitions from bio2bel_{self.module_name}',
            version='1.0.0',
        )

        for pathway in self._query_pathway():
            pathway.add_to_bel_graph(graph)

        return graph


def write_dict(data: Mapping[str, Collection[str]], path: str) -> None:
    """Write a dictionary to a file as an Excel document."""
    gene_sets_df = dict_to_df(data)
    logger.info("Exporting gene sets to %s", path)
    gene_sets_df.to_excel(path, index=False)
    logger.info("Exported gene sets to %s", path)


def dict_to_df(data: Mapping[str, Collection[str]]) -> pd.DataFrame:
    """Convert a dictionary to a DataFrame."""
    return pd.DataFrame({
        key: pd.Series(list(values))
        for key, values in data.items()
    })
