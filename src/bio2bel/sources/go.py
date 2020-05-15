# -*- coding: utf-8 -*-

"""Tools for gene ontology."""

from typing import Optional

import pandas as pd
import pyobo
import requests
from protmapper.uniprot_client import get_hgnc_id

import pybel


__all__ = [
    'enrich_graph',
]

URL = 'http://api.geneontology.org/api/bioentity/function/GO:{}/genes'


def get_graph(identifier: str, *, rows: Optional[int] = None) -> pybel.BELGraph:
    """Get the graph surrounding a given GO term and its descendants."""
    graph = pybel.BELGraph()
    enrich_graph(graph, identifier, rows=rows)
    return graph


def enrich_graph(graph: pybel.BELGraph, identifier, *, rows: Optional[int] = None) -> None:
    """Enrich a BEL graph with a given GO term and its descendants."""
    df = get_gene_associations_df(identifier, rows=rows)
    _enrich_graph_with_df(graph, df)
    _enrich_graph_with_hierarchy(graph, identifier)


def get_gene_associations_df(identifier: str, *, rows: Optional[int] = None) -> pd.DataFrame:
    """Get gene associations for the given GO identifier as a dataframe.

    - filtered for human onlay
    - filtered for proteins only
    - add HGNC identifier and entrez identifier
    """
    associations = get_gene_associations(identifier, rows=rows)
    df = pd.DataFrame(
        [
            (
                e['subject']['id'],
                e['subject']['label'],
                e['subject']['taxon']['id'][len('NCBITaxon:'):],
                e['object']['id'],
                e['object']['label'],
                e['negated'],
                # e['relation']['category'],
                # e['relation']['id'],
                # e['relation']['inverse'],
                # e['relation']['label'],
                # e['subject_extensions'],
            )
            for e in associations
        ],
        columns=[
            'source_id',
            'source_name',
            'taxonomy_id',
            'target_id',
            'target_label',
            'negated',
            # 'relation_category',
            # 'relation_id',
            # 'relation_inverse',
            # 'relation_label',
            # 'subject_extensions',
        ],
    )
    df = df[df['taxonomy_id'] == '9606']
    df = df[df['source_id'].str.startswith('UniProtKB:')]
    df['uniprot_id'] = df['source_id'].map(lambda s: s[len('UniProtKB:'):])
    del df['source_id']
    del df['taxonomy_id']

    df['hgnc_id'] = df['uniprot_id'].map(get_hgnc_id)
    df = df[df['hgnc_id'].notna()]

    df['ncbigene_id'] = df['hgnc_id'].map(pyobo.get_filtered_xrefs('hgnc', 'ncbigene').__getitem__)
    df['target_id'] = df['target_id'].map(lambda s: s[len('GO:'):])
    return df


def get_gene_associations(identifier: str, rows: Optional[int] = None):
    """Get gene associations."""
    res = requests.get(URL.format(identifier), params={'rows': rows or 100_00})
    return res.json()['associations']


def _enrich_graph_with_df(graph: pybel.BELGraph, df: pd.DataFrame) -> None:
    it = df[['ncbigene_id', 'source_name', 'target_id']].values
    for ncbigene_id, ncbi_name, go_id in it:
        graph.add_association(
            pybel.dsl.Protein('ncbigene', identifier=ncbigene_id, name=ncbi_name),
            pybel.dsl.BiologicalProcess('go', identifier=go_id, name=pyobo.get_name('go', go_id)),
            citation='',
            evidence='',
        )


def _enrich_graph_with_hierarchy(graph: pybel.BELGraph, identifier: str) -> None:
    hierarchy = pyobo.get_subhierarchy('go', identifier)

    adders = {
        'is_a': graph.add_is_a,
        'part_of': graph.add_part_of,
    }
    for child, parent, data in hierarchy.edges(data=True):
        relation = data['relation']
        child_name = pyobo.get_name_by_curie(child)
        parent_name = pyobo.get_name_by_curie(parent)
        child_prefix, child_id = pyobo.normalize_curie(child)
        parent_prefix, parent_id = pyobo.normalize_curie(parent)
        adders[relation](
            pybel.dsl.BiologicalProcess(namespace=child_prefix, identifier=child_id, name=child_name),
            pybel.dsl.BiologicalProcess(namespace=parent_prefix, identifier=parent_id, name=parent_name),
        )
