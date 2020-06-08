# -*- coding: utf-8 -*-

"""Manager for ComPath."""

from __future__ import annotations

import logging
import os
import types
import typing
from collections import Counter
from typing import Iterable, List, Mapping, Optional, Set, Tuple, Type

import click
from pyobo.io_utils import multidict
from sqlalchemy import func, or_
from tqdm import tqdm

import pybel
import pybel.dsl
from pybel import BELGraph
from pybel.manager.models import Namespace, NamespaceEntry
from .exc import CompathManagerPathwayModelError, CompathManagerProteinModelError
from .mixins import CompathPathwayMixin, CompathProteinMixin
from .utils import write_dict
from ..manager.abstract_manager import AbstractManager
from ..manager.bel_manager import BELManagerMixin
from ..manager.flask_manager import FlaskMixin
from ..manager.namespace_manager import BELNamespaceManagerMixin
from ..utils import _get_managers, _get_modules

__all__ = [
    'CompathManager',
    'get_compath_manager_classes',
]

logger = logging.getLogger(__name__)


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

        # set flask models if not already set
        if not hasattr(self, 'flask_admin_models') or not self.flask_admin_models:
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

    def summarize(self) -> Mapping[str, int]:
        """Summarize the database."""
        return {
            'pathways': self.count_pathways(),
            'proteins': self.count_proteins(),
        }

    def get_protein_by_hgnc_symbol(self, hgnc_symbol: str) -> Optional[CompathProteinMixin]:
        """Get a protein by its HGNC gene symbol.

        :param hgnc_symbol: HGNC gene symbol
        """
        return self._help_get_protein(self.protein_model.hgnc_symbol, hgnc_symbol)

    def get_protein_by_hgnc_id(self, hgnc_id: str) -> Optional[CompathProteinMixin]:
        """Get a protein by its HGNC gene identifier.

        :param hgnc_id: HGNC gene identifier
        """
        return self._help_get_protein(self.protein_model.hgnc_id, hgnc_id)

    def _help_get_protein(self, protein_column, query: str) -> Optional[CompathProteinMixin]:
        return self._query_protein().filter(protein_column == query).one_or_none()

    def get_proteins_by_hgnc_symbols(self, hgnc_symbols: Iterable[str]) -> List[CompathProteinMixin]:
        """Return the proteins in the database within the gene set query.

        :param hgnc_symbols: HGNC gene symbols
        """
        return self._help_get_proteins(self.protein_model.hgnc_symbol, hgnc_symbols)

    def get_proteins_by_hgnc_ids(self, hgnc_ids: Iterable[str]) -> List[CompathProteinMixin]:
        """Return the proteins in the database within the gene set query.

        :param hgnc_ids: HGNC gene identifiers
        """
        return self._help_get_proteins(self.protein_model.hgnc_id, hgnc_ids)

    def _help_get_proteins(self, protein_column, queries: Iterable[str]) -> List[CompathProteinMixin]:
        return self._query_protein().filter(protein_column.in_(queries)).all()

    def search_genes(self, query: str, *, limit: Optional[int] = None) -> Optional[CompathPathwayMixin]:
        """Filter genes by HGNC gene symbol.

        :param query: part of an HGNC identifier or gene symbol
        :param limit: limit number of results
        """
        _query = self._query_protein().filter(or_(
            self.protein_model.hgnc_symbol.contains(query),
            self.protein_model.hgnc_id.contains(query),
        ))

        if limit:
            _query = _query.limit(limit)

        return _query.all()

    def search_pathways(self, query: str, *, limit: Optional[int] = None) -> List[CompathPathwayMixin]:
        """Return all pathways having the query in their names.

        :param query: query string
        :param limit: limit number of results
        """
        _query = self._query_pathway().filter(or_(
            self.pathway_model.name.contains(query),
            self.pathway_model.identifier.contains(query),
        ))

        if limit:
            _query = _query.limit(limit)

        return _query.all()

    def query_hgnc_symbol(self, hgnc_symbol: str) -> List[Tuple[str, str, int]]:
        """Return the pathways associated with a gene.

        :param hgnc_symbol: HGNC gene symbol
        :return: associated with the gene
        """
        # FIXME reimplement with better query
        protein = self.get_protein_by_hgnc_symbol(hgnc_symbol)
        if protein is None:
            return []

        pathway_ids = protein.get_pathways_ids()
        enrichment_results = []

        for pathway_id in pathway_ids:
            pathway = self.get_pathway_by_id(pathway_id)
            if pathway is None:
                continue
            pathway_gene_set = pathway.get_hgnc_symbols()  # Pathway gene set
            enrichment_results.append((pathway_id, pathway.name, len(pathway_gene_set)))

        return enrichment_results

    def get_pathways_by_hgnc_ids(self, hgnc_ids: Iterable[str]) -> Set[CompathPathwayMixin]:
        """Get a set of pathways linked to a set of genes by HGNC identifiers."""
        # TODO re-implement! This is terribly inefficient
        return {
            pathway
            for protein in self.get_proteins_by_hgnc_ids(hgnc_ids)
            for pathway in protein.pathways
        }

    def query_hgnc_symbols(self, hgnc_symbols: Iterable[str]) -> Mapping[str, Mapping]:
        """Calculate the pathway counter dictionary.

        :param hgnc_symbols: An iterable of HGNC gene symbols to be queried
        :return: Enriched pathways with mapped pathways/total
        """
        proteins = self.get_proteins_by_hgnc_symbols(hgnc_symbols)

        # Flat the pathways lists and applies Counter to get the number matches in every mapped pathway
        pathway_counter = Counter([
            pathway
            for protein in proteins
            for pathway in protein.get_pathways_ids()
        ])

        enrichment_results = {}

        for pathway_id, proteins_mapped in pathway_counter.items():
            pathway = self.get_pathway_by_id(pathway_id)
            if pathway is None:
                logger.warning('could not find pathway %s', pathway_id)
                continue

            pathway_gene_set = pathway.get_hgnc_symbols()  # Pathway gene set

            enrichment_results[pathway_id] = {
                "pathway_id": pathway_id,
                "pathway_name": pathway.name,
                "mapped_proteins": proteins_mapped,
                "pathway_size": len(pathway_gene_set),
                "pathway_gene_set": pathway_gene_set,
            }

        return enrichment_results

    def get_pathway_by_id(self, pathway_id: str) -> Optional[CompathPathwayMixin]:
        """Get a pathway by its database-specific identifier.

        Not to be confused with the standard column called "id".

        :param pathway_id: Pathway identifier
        """
        return self._query_pathway().filter(self.pathway_model.identifier == pathway_id).one_or_none()

    def get_pathways_by_name(self, pathway_name: str) -> List[CompathPathwayMixin]:
        """Get a list of pathways by its database-specific name.

        There might be multiple because of the same pathways in multiple species.

        :param pathway_name: Pathway name
        """
        return self._query_pathway().filter(self.pathway_model.name == pathway_name).all()

    def get_pathway_id_name_mapping(self) -> Mapping[str, str]:
        """Get all pathway identifiers to names."""
        return dict(self.session.query(self.pathway_model.identifier, self.pathway_model.name).all())

    def get_all_pathway_names(self) -> List[str]:
        """Get all pathway names stored in the database."""
        return [name for name, in self.session.query(self.pathway_model.name).all()]

    def get_all_hgnc_symbols(self) -> Set[str]:
        """Return the set of genes present in all Pathways."""
        return {
            gene.hgnc_symbol
            for pathway in self.list_pathways()
            for gene in pathway.proteins
            if pathway.proteins
        }

    def get_pathway_id_to_symbols(self) -> Mapping[str, Set[str]]:
        """Return the set of genes in each pathway."""
        return self._help_get_pathway_to_protein(self.pathway_model.identifier, self.protein_model.hgnc_symbol)

    def get_pathway_id_to_hgnc_ids(self) -> Mapping[str, Set[str]]:
        """Return the set of genes in each pathway."""
        return self._help_get_pathway_to_protein(self.pathway_model.identifier, self.protein_model.hgnc_id)

    def get_pathway_name_to_hgnc_symbols(self) -> Mapping[str, Set[str]]:
        """Return the set of HGNC gene symbols in each pathway."""
        return self._help_get_pathway_to_protein(self.pathway_model.name, self.protein_model.hgnc_symbol)

    def get_pathway_name_to_hgnc_ids(self) -> Mapping[str, Set[str]]:
        """Return the set of HGNC gene identifiers in each pathway."""
        return self._help_get_pathway_to_protein(self.pathway_model.name, self.protein_model.hgnc_id)

    def _help_get_pathway_to_protein(self, pathway_column, protein_column) -> Mapping[str, Set[str]]:
        """Return the set of genes in each pathway."""
        rv = multidict(self._help_query_pathway_protein(pathway_column, protein_column))
        return {k: set(v) for k, v in rv.items()}

    def _help_query_pathway_protein(self, pathway_column, protein_column):
        return (
            self.session
                .query(pathway_column, protein_column)
                .join(self.pathway_model.proteins)
                .filter(protein_column.isnot(None))
                .all()  # noqa:C812
        )

    def get_pathway_size_distribution(self) -> typing.Counter[str]:
        """Map pathway identifier to the size of each pathway."""
        return self._help_get_pathway_size_distribution(self.protein_model.hgnc_id)

    def _help_get_pathway_size_distribution(self, protein_column) -> typing.Counter[str]:
        return Counter(dict(
            self.session
                .query(self.pathway_model.identifier, func.count(protein_column))
                .join(self.pathway_model.proteins)
                .group_by(self.pathway_model.identifier)
                .having(func.count(protein_column) > 0)
                .all()  # noqa:C812
        ))

    def get_hgnc_symbol_size_distribution(self) -> typing.Counter[str]:
        """Map HGNC gene symbol to number of pathways associated with each."""
        return self._help_get_gene_size_distribution(self.protein_model.hgnc_symbol)

    def get_hgnc_id_size_distribution(self) -> typing.Counter[str]:
        """Map HGNC gene identifier to number of pathways associated with each."""
        return self._help_get_gene_size_distribution(self.protein_model.hgnc_id)

    def _help_get_gene_size_distribution(self, protein_column) -> typing.Counter[str]:
        return Counter(dict(
            self.session
                .query(protein_column, func.count(self.pathway_model.identifier))
                .join(self.protein_model.pathways)
                .group_by(protein_column)
                .having(func.count(protein_column) > 0)
                .all()  # noqa:C812
        ))

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
            gene_sets_dict = manager.get_pathway_name_to_hgnc_symbols()

            path = os.path.join(directory, f'{manager.module_name}_gene_sets.{fmt}')
            if fmt == 'xlsx' or format is None:
                write_dict(gene_sets_dict, path)
            elif fmt == 'tsv':
                with open(path, 'w') as file:
                    for key, values in gene_sets_dict.items():
                        for value in values:
                            print(key, value, file=file, sep='\t')  # noqa:T001

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

        graph = BELGraph(name=str(pathway))
        pathway.add_to_bel_graph(graph)
        return graph

    def to_bel(self) -> BELGraph:
        """Serialize the database as BEL."""
        graph = BELGraph(
            name=f'Pathway Definitions from bio2bel_{self.module_name}',
            version='1.0.0',
        )

        for pathway in tqdm(self._query_pathway(), total=self.count_pathways()):
            pathway.add_to_bel_graph(graph)

        return graph

    def enrich_pathways(self, graph: BELGraph) -> None:
        """Enrich all proteins belonging to pathway nodes in the graph."""
        pathway_identifiers = {
            node.identifier
            for node in graph
            if isinstance(node,
                          pybel.dsl.BiologicalProcess) and node.namespace.lower() == self.module_name and node.identifier
        }
        for pathway_identifier in pathway_identifiers:
            pathway = self.get_pathway_by_id(pathway_identifier)
            pathway.add_to_bel_graph(graph)

    def enrich_proteins(self, graph: BELGraph) -> None:
        """Enrich all pathways associated with proteins in the graph."""
        hgnc_ids = {
            node.identifier
            for node in graph
            if isinstance(node, pybel.dsl.CentralDogma) and node.namespace.lower() == 'hgnc' and node.identifier
        }
        for pathway in self.get_pathways_by_hgnc_ids(hgnc_ids):
            pathway.add_to_bel_graph(graph)


def get_compath_modules() -> Mapping[str, types.ModuleType]:
    """Get all ComPath modules."""
    return dict(_get_modules('compath'))


def get_compath_manager_classes() -> Mapping[str, Type[CompathManager]]:
    """Get all ComPath manager classes."""
    return dict(_get_managers('compath'))
