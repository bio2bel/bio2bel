# -*- coding: utf-8 -*-

"""PID Importer."""

import logging
from itertools import product
from typing import Iterable, Tuple

from pyobo import get_filtered_xrefs, get_name, get_name_id_mapping
from pyobo.ndex_utils import CX, iterate_aspect
from pyobo.sources.pid import get_obo, iter_networks
from pyobo.struct.typedef import pathway_has_part
from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import relationship
from tqdm import tqdm

import pybel
import pybel.dsl
from pybel import BELGraph
from ..compath import CompathManager, CompathPathwayMixin, CompathProteinMixin
from ..utils import get_data_dir

logger = logging.getLogger(__name__)

MODULE_NAME = 'pid'
DIRECTORY = get_data_dir(MODULE_NAME)

URL = 'https://github.com/NCIP/pathway-interaction-database/raw/master/download/NCI-Pathway-Info.xlsx'


def _get_hgnc_id_from_name(name):
    return get_name_id_mapping('hgnc').get(name)


def _map_hgnc_to_entrez(hgnc_id):
    return get_filtered_xrefs('hgnc', 'ncbigene').get(hgnc_id)


def _get_gene_name(protein_id: str, web_fallback: bool = True):
    from protmapper.uniprot_client import get_gene_name
    return get_gene_name(protein_id, web_fallback=web_fallback)


relation_to_adder = {
    'controls-state-change-of': BELGraph.add_regulates,
}

namespace_to_dsl = {
    'cas': pybel.dsl.Abundance,
    'uniprot': pybel.dsl.Protein,
    'hprd': pybel.dsl.Protein,
    'chebi': pybel.dsl.Abundance,
    'hgnc': pybel.dsl.Protein,
}

UNMAPPED = set()

MAPPING = {
    'RAS Family': pybel.dsl.Protein('fplx', 'RAS'),
    'Cyclin D': pybel.dsl.Protein('fplx', 'Cyclin_D'),
    'Gi family': pybel.dsl.Protein('fplx', 'G_i'),
}


def iterate_graphs() -> Iterable[Tuple[str, BELGraph]]:
    """List network uuids."""
    for network_uuid, cx in tqdm(iter_networks(), desc='networks'):
        yield network_uuid, get_graph_from_cx(network_uuid, cx)


def get_graph_from_cx(network_uuid: str, cx: CX) -> BELGraph:  # noqa: C901
    """Get a PID network from NDEx."""
    metadata = {}
    for entry in iterate_aspect(cx, 'networkAttributes'):
        member_name = entry['n']
        if member_name == 'name':
            metadata['name'] = entry['v']
        elif member_name == 'version':
            metadata['version'] = entry['v']
        elif member_name == 'description':
            metadata['description'] = entry['v']

    graph = BELGraph(**metadata)

    id_to_type = {}
    id_to_members = {}
    id_to_alias = {}
    # TODO nodeAttributes have list of protein definitions for some things
    for entry in iterate_aspect(cx, 'nodeAttributes'):
        node_id = entry['po']
        member_name = entry['n']
        if member_name == 'type':
            id_to_type[node_id] = entry['v']
        elif member_name == 'alias':
            id_to_alias[node_id] = entry['v']
        elif member_name == 'member':
            id_to_members[node_id] = entry['v']
        else:
            logger.warning(f'unhandled node attribute: {member_name}')

    id_to_citations = {}
    for entry in iterate_aspect(cx, 'edgeAttributes'):
        if entry['n'] == 'citation':
            id_to_citations[entry['po']] = [x[len('pubmed:'):] for x in entry['v']]

    id_to_dsl = {}
    for node in iterate_aspect(cx, 'nodes'):
        node_id = node['@id']
        reference = node['r']
        if reference in MAPPING:
            id_to_dsl[node_id] = [MAPPING[reference]]
            continue
        if node_id in id_to_members:
            node_type = id_to_type[node_id]
            members = id_to_members[node_id]
            if node_type != 'proteinfamily':
                logger.warning(f'unhandled node: {node_id} type={node_type} members={members}')

            _rv = []
            for member in members:
                if not member.startswith('hgnc.symbol:'):
                    logger.warning(f'unhandled member for node: {node_id} -> {member}')
                    continue
                member_name = member[len('hgnc.symbol:'):]
                member_identifier = _get_hgnc_id_from_name(member_name)
                if member_identifier is None:
                    logger.warning(f'unhandled member for node: {node_id} -> {member}')
                    continue
                _rv.append(pybel.dsl.Protein(namespace='hgnc', identifier=member_identifier, name=member_name))
            id_to_dsl[node_id] = _rv
            continue
        if ':' not in reference:
            logger.warning(f'no curie: {node_id} {reference}')
            UNMAPPED.add(reference)
            continue
        prefix, identifier = reference.split(':')
        if prefix == 'hprd':
            # nodes.write(f'unhandled hprd:{identifier}')
            continue
        elif prefix == 'cas':
            # nodes.write(f'unhandled cas:{identifier}')
            continue  # not sure what to do with this
        elif prefix == 'CHEBI':
            name = get_name('chebi', identifier)
            id_to_dsl[node_id] = [pybel.dsl.Abundance(namespace='chebi', identifier=identifier, name=name)]
        elif prefix == 'uniprot':
            name = node['n']
            hgnc_id = _get_hgnc_id_from_name(name)
            if hgnc_id:
                name = _get_gene_name(identifier)
                if name is None:
                    logger.warning('could not map uniprot to name')
            if identifier is None:
                logger.warning(f'could not map HGNC symbol {name}')
                continue
            id_to_dsl[node_id] = [pybel.dsl.Protein(namespace='hgnc', identifier=identifier, name=name)]
        else:
            logger.warning(f'unexpected prefix: {prefix}')
            continue

    for edge in iterate_aspect(cx, 'edges'):
        source_id, target_id = edge['s'], edge['t']
        if source_id not in id_to_dsl or target_id not in id_to_dsl:
            continue
        edge_type = edge['i']
        edge_id = edge['@id']

        sources = id_to_dsl[source_id]
        targets = id_to_dsl[target_id]
        citations = id_to_citations.get(edge_id, [('ndex', network_uuid)])
        for source, target, citation in product(sources, targets, citations):
            if edge_type == 'in-complex-with':
                graph.add_binds(source, target, citation=citation, evidence=edge_id)
            elif edge_type == 'controls-phosphorylation-of':
                graph.add_regulates(
                    source, target.with_variants(pybel.dsl.ProteinModification('Ph')),
                    citation=citation, evidence=edge_id,
                )
            elif edge_type in {'controls-transport-of', 'controls-transport-of-chemical'}:
                graph.add_regulates(
                    source, target, citation=citation, evidence=edge_id,
                    # object_modifier=pybel.dsl.translocation(),
                )
            elif edge_type == 'chemical-affects':
                graph.add_regulates(
                    source, target, citation=citation, evidence=edge_id, object_modifier=pybel.dsl.activity(),
                )
            elif edge_type in {'controls-expression-of', 'controls-production-of',
                               'consumption-controlled-by', 'controls-state-change-of',
                               'catalysis-precedes'}:
                graph.add_regulates(source, target, citation=citation, evidence=edge_id)
            elif edge_type == 'used-to-produce':
                graph.add_node_from_data(pybel.dsl.Reaction(
                    reactants=source, products=target,
                ))
            elif edge_type == 'reacts-with':
                graph.add_binds(source, target, citation=citation, evidence=edge_id)
                # graph.add_node_from_data(pybel.dsl.Reaction(
                #     reactants=[source, target],
                # ))

            else:
                logger.warning(f'unhandled edge type: {source} {edge_type} {target}')

    return graph


# Manager, models

PATHWAY_TABLE = f'{MODULE_NAME}_pathway'
PROTEIN_TABLE = f'{MODULE_NAME}_protein'
PATHWAY_PROTEIN_TABLE = f'{MODULE_NAME}_pathway_protein'

Base: DeclarativeMeta = declarative_base()

pathway_protein = Table(
    PATHWAY_PROTEIN_TABLE,
    Base.metadata,
    Column('pathway_id', Integer, ForeignKey(f'{PATHWAY_TABLE}.id'), primary_key=True),
    Column('protein_id', Integer, ForeignKey(f'{PROTEIN_TABLE}.id'), primary_key=True),
)


class Protein(Base, CompathProteinMixin):
    """Protein from PID."""

    __tablename__ = PROTEIN_TABLE

    id = Column(Integer, primary_key=True)  # noqa:A003

    entrez_id = Column(String(255), doc='entrez id of the protein')
    hgnc_id = Column(String(255), doc='HGNC id of the protein')
    hgnc_symbol = Column(String(255), doc='HGN symbol of the protein')

    def to_pybel(self) -> pybel.dsl.Protein:
        """Return a protein."""
        return pybel.dsl.Protein(namespace='hgnc', name=self.hgnc_symbol, identifier=self.hgnc_id)


class Pathway(Base, CompathPathwayMixin):
    """Pathway from PID."""

    __tablename__ = PATHWAY_TABLE

    prefix = 'pid.pathway'
    id = Column(Integer, primary_key=True)  # noqa:A003

    identifier = Column(String(255), doc='HGNC gene family id of the protein')
    name = Column(String(255), doc='HGNC gene family name of the protein')

    proteins = relationship(
        Protein,
        secondary=pathway_protein,
        backref='pathways',
    )


class Manager(CompathManager):
    """Manager for PID."""

    module_name = MODULE_NAME
    _base = Base
    flask_admin_models = [Pathway, Protein]
    namespace_model = pathway_model = Pathway
    edge_model = pathway_protein
    protein_model = Protein

    def populate(self, *args, **kwargs) -> None:
        """Populate the PID database."""
        obo = get_obo()

        x = {
            reference.identifier: Protein(
                entrez_id=_map_hgnc_to_entrez(reference.identifier),
                hgnc_id=reference.identifier,
                hgnc_symbol=reference.name,
            )
            for term in obo
            for reference in term.get_relationships(pathway_has_part)
        }
        logger.info('extracted %d proteins from pid.pathway', len(x))

        for term in obo:
            pathway = Pathway(
                identifier=term.identifier,
                name=term.name,
                proteins=[
                    x[reference.identifier]
                    for reference in term.get_relationships(pathway_has_part)
                ],
            )
            self.session.add(pathway)
        self.session.commit()


main = Manager.get_cli()

# def main():
#     """Get and output graphs to desktop."""
#     import os
#     directory = os.path.join(os.path.expanduser('~'), 'Desktop', 'pid')
#     os.makedirs(directory, exist_ok=True)
#     for network_uuid, graph in iterate_graphs():
#         pybel.to_nodelink_file(graph, os.path.join(directory, f'{network_uuid}.bel.nodelink.json'), indent=2)
#     with open(os.path.join(directory, 'UNMAPPED.txt'), 'w') as file:
#         for unmapped in sorted(UNMAPPED):
#             print(unmapped, file=file)


if __name__ == '__main__':
    main()
