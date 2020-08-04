# -*- coding: utf-8 -*-

"""Exporter for TFregulons."""

import logging
from functools import lru_cache
from typing import Set

import pandas as pd
from pyobo import get_name_id_mapping

import pybel.dsl
from pybel import BELGraph
from .. import ensure_path

logger = logging.getLogger(__name__)

MODULE = 'tfregulons'
VERSION = '20180915'
URL = f'https://github.com/saezlab/DoRothEA/blob/master/data/' \
      f'TFregulons/consensus/table/database_normal_{VERSION}.csv.zip?raw=true'


@lru_cache()
def get_df() -> pd.DataFrame:
    """Get the TFregulons dataframe."""
    path = ensure_path(MODULE, URL)
    return _read_df(path)


def _read_df(path) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        compression='zip',
        usecols=['TF', 'target', 'effect', 'score', 'pubmedID_from_curated_resources'],
    )
    df.rename(
        columns={
            'pubmedID_from_curated_resources': 'pmids',
            'TF': 'tf_hgnc_symbol',
            'target': 'target_hgnc_symbol',
        },
        inplace=True,
    )
    df = df[df['score'].isin(set('ABC'))]  # there are also D and E

    hgnc_name_to_id = get_name_id_mapping('hgnc')
    df['tf_hgnc_id'] = df['tf_hgnc_symbol'].map(hgnc_name_to_id.get)
    df['target_hgnc_id'] = df['target_hgnc_symbol'].map(hgnc_name_to_id.get)

    tf_missing_id = df['tf_hgnc_id'].isna()
    if tf_missing_id.any():
        missing_tf_symbols = df.loc[tf_missing_id, 'tf_hgnc_symbol'].unique()
        logger.warning(f'missing HGNC id for {len(missing_tf_symbols)} transcription factors')
        df = df[~tf_missing_id]

    target_missing_id = df['target_hgnc_id'].isna()
    if target_missing_id.any():
        missing_target_symbols = df.loc[target_missing_id, 'target_hgnc_symbol'].unique()
        logger.warning(f'missing HGNC id for {len(missing_target_symbols)} targets')
        df = df[~target_missing_id]

    return df


def get_hgnc_ids(graph: BELGraph) -> Set[str]:
    """Get HGNC identifiers for nodes in the graph."""
    return {
        node.identifier
        for node in graph
        if isinstance(node, pybel.dsl.CentralDogma) and node.namespace.lower() == 'hgnc'
    }


def get_bel() -> BELGraph:
    """Get the entirety of TFregulons as BEL."""
    graph = BELGraph(name='TFRegulons')
    df = get_df()
    _add_rows(df, graph)
    return graph


def enrich_graph(graph: BELGraph) -> None:
    """Enrich a graph with transcription factors effecting the genes/rnas/proteins in the graph."""
    hgnc_ids = get_hgnc_ids(graph)
    df = get_df()
    df = df[df['target_hgnc_id'].isin(hgnc_ids)]
    _add_rows(df, graph)


def _add_rows(df: pd.DataFrame, graph: BELGraph) -> None:
    for _, row in df.iterrows():
        effect = row['effect']
        if effect == 0:
            continue  # no binding. Could add negative BEL later

        tf_protein = pybel.dsl.Protein(
            namespace='hgnc',
            identifier=row['tf_hgnc_id'],
            name=row['tf_hgnc_symbol'],
        )
        target_rna = pybel.dsl.Rna(
            namespace='hgnc',
            identifier=row['target_hgnc_id'],
            name=row['target_hgnc_symbol'],
        )
        target_gene = target_rna.get_gene()

        if 'pmids' in row:
            citations = [pmid.strip() for pmid in row['pmids'].split(',')]
        else:
            citations = [('database', 'tfregulons')]

        evidence = 'From TFregulons'

        for citation in citations:
            if effect == 1:
                binds_dna_adder, affects_expression_adder = graph.add_directly_increases, graph.add_increases
            else:
                binds_dna_adder, affects_expression_adder = graph.add_directly_decreases, graph.add_decreases
            binds_dna_adder(
                pybel.dsl.ComplexAbundance([tf_protein, target_gene]),
                target_rna,
                citation=citation,
                evidence=evidence,
            )
            affects_expression_adder(
                tf_protein,
                target_rna,
                citation=citation,
                evidence=evidence,
            )
            graph.add_transcription(target_gene, target_rna)
