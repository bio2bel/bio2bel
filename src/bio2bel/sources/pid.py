# -*- coding: utf-8 -*-

"""PID Importer."""

import logging
from collections import Mapping
from pprint import pprint

import ndex2

import pybel.dsl
from bio2bel import get_data_dir
from pybel import BELGraph

logger = logging.getLogger(__name__)

MODULE_NAME = 'pid'
DIRECTORY = get_data_dir(MODULE_NAME)

NETWORKSET_UUID = '8a2d7ee9-1513-11e9-bb6a-0ac135e8bacf'

client = ndex2.Ndex2()

relation_to_adder = {
    'controls-state-change-of': BELGraph.add_regulates,
}

namespace_to_dsl = {
    'cas': pybel.dsl.Abundance,
    'uniprot': pybel.dsl.Protein,
    'CHEBI': pybel.dsl.Abundance,
}


def get_graphs() -> Mapping[str, BELGraph]:
    """List network uuids"""
    r = client.get_network_set(NETWORKSET_UUID)
    pprint(r)
    network_uuids = r['networks']

    return {
        network_uuid: get_graph_from_uuid(network_uuid)
        for network_uuid in network_uuids
    }


def get_graph_from_uuid(network_uuid: str) -> BELGraph:
    """Get a PID network from NDEx."""
    graph = BELGraph()

    id_to_reference = {}
    res = client.get_network_aspect_as_cx_stream(network_uuid, 'nodes')
    for node in res.json():
        node_id = node['@id']
        reference = node['r']
        if ':' not in reference:
            logger.warning(f'no curie: {node_id} {reference}')
            continue
        prefix, identifier = reference.split(':')
        dsl = namespace_to_dsl.get(prefix)
        if dsl is None:
            logger.warning(f'unhandled prefix: {prefix}')
            continue
        id_to_reference[node_id] = dsl(namespace=prefix, identifier=identifier)

    res = client.get_network_aspect_as_cx_stream(network_uuid, 'edges')
    for edge in res.json():
        source_id, target_id = edge['s'], edge['t']
        if source_id not in id_to_reference or target_id not in id_to_reference:
            continue
        source = id_to_reference[source_id]
        target = id_to_reference[target_id]
        edge_type = edge['i']
        citation, evidence = ('ndex', network_uuid), edge['@id']
        if edge_type == 'in-complex-with':
            graph.add_binds(source, target, citation=citation, evidence=evidence)
        elif edge_type == 'controls-state-change-of':
            graph.add_regulates(source, target, citation=citation, evidence=evidence)
        elif edge_type == 'controls-phosphorylation-of':
            graph.add_regulates(
                source, target.with_variants(pybel.dsl.ProteinModification('Ph')),
                citation=citation, evidence=evidence,
            )
        elif edge_type == 'controls-transport-of':
            graph.add_regulates(
                source, target.with_variants(pybel.dsl.ProteinModification('Ph')),
                citation=citation, evidence=evidence,
                # object_modifier=pybel.dsl.translocation(),
            )
        elif edge_type == 'chemical-affects':
            graph.add_regulates(
                source, target, citation=citation, evidence=evidence, object_modifier=pybel.dsl.activity(),
            )
        elif edge_type == 'controls-expression-of':
            pass
        elif edge_type == 'controls-production-of':
            pass
        elif edge_type == 'consumption-controlled-by':
            pass
        elif edge_type == 'used-to-produce':
            pass
        elif edge_type == 'reacts-with':
            pass
        elif edge_type == 'catalysis-precedes':
            pass
        else:
            logger.warning(f'unhandled edge type: {edge_type}')

    return graph


if __name__ == '__main__':
    get_graphs()
