# -*- coding: utf-8 -*-

"""SQLAlchemy mixins for ComPath."""

from __future__ import annotations

from abc import abstractmethod
from typing import ClassVar, List, Set

from sqlalchemy import Column

import pybel.dsl
from ..manager.models import SpeciesMixin

__all__ = [
    'CompathPathwayMixin',
    'CompathProteinMixin',
]


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

    def get_hgnc_symbols(self) -> Set[str]:
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
