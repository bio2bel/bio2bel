# -*- coding: utf-8 -*-

"""PID Importer."""

import logging
from itertools import product
from typing import Iterable, Tuple

import ndex2
from protmapper.uniprot_client import get_gene_name
from pyobo import get_id_name_mapping, get_name_id_mapping
from tqdm import tqdm

import pybel
import pybel.dsl
from pybel import BELGraph
from ..utils import get_data_dir

logger = logging.getLogger(__name__)

MODULE_NAME = 'pid'
DIRECTORY = get_data_dir(MODULE_NAME)

NETWORKSET_UUID = '8a2d7ee9-1513-11e9-bb6a-0ac135e8bacf'

client = ndex2.Ndex2()

chebi_id_to_name = get_id_name_mapping('chebi')
hgnc_name_to_id = get_name_id_mapping('hgnc')

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
    res = client.get_network_set(NETWORKSET_UUID)
    network_uuids = res['networks']
    for network_uuid in tqdm(network_uuids, desc='networks'):
        # from pprint import pprint
        # r = client.get_network_as_cx_stream(network_uuid)
        # pprint(r.json())
        yield network_uuid, get_graph_from_uuid(network_uuid)


def get_graph_from_uuid(network_uuid: str) -> BELGraph:  # noqa: C901
    """Get a PID network from NDEx."""
    res = client.get_network_aspect_as_cx_stream(network_uuid, 'networkAttributes')
    metadata = {}
    for entry in res.json():
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
    res = client.get_network_aspect_as_cx_stream(network_uuid, 'nodeAttributes')
    for entry in res.json():
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
    res = client.get_network_aspect_as_cx_stream(network_uuid, 'edgeAttributes')
    for entry in res.json():
        if entry['n'] == 'citation':
            id_to_citations[entry['po']] = [x[len('pubmed:'):] for x in entry['v']]

    id_to_dsl = {}
    res = client.get_network_aspect_as_cx_stream(network_uuid, 'nodes')
    nodes = res.json()
    # nodes = tqdm(nodes, desc='nodes', leave=False)
    for node in nodes:
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
                member_identifier = hgnc_name_to_id.get(member_name)
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
            name = chebi_id_to_name[identifier]
            id_to_dsl[node_id] = [pybel.dsl.Abundance(namespace='chebi', identifier=identifier, name=name)]
        elif prefix == 'uniprot':
            name = node['n']
            if name not in hgnc_name_to_id:
                name = get_gene_name(identifier)
                if name is None:
                    logger.warning('could not map uniprot to name')
            identifier = hgnc_name_to_id.get(name)
            if identifier is None:
                logger.warning(f'could not map HGNC symbol {name}')
                continue
            id_to_dsl[node_id] = [pybel.dsl.Protein(namespace='hgnc', identifier=identifier, name=name)]
        else:
            logger.warning(f'unexpected prefix: {prefix}')
            continue

    res = client.get_network_aspect_as_cx_stream(network_uuid, 'edges')
    edges = res.json()
    # edges = tqdm(edges, desc='edges', leave=False)
    for edge in edges:
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


def main():
    """Get and output graphs to desktop."""
    import os
    directory = os.path.join(os.path.expanduser('~'), 'Desktop', 'pid')
    os.makedirs(directory, exist_ok=True)
    for network_uuid, graph in iterate_graphs():
        pybel.to_nodelink_file(graph, os.path.join(directory, f'{network_uuid}.bel.nodelink.json'), indent=2)
    with open(os.path.join(directory, 'UNMAPPED.txt'), 'w') as file:
        for unmapped in sorted(UNMAPPED):
            print(unmapped, file=file)


if __name__ == '__main__':
    main()
