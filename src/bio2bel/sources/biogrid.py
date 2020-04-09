# -*- coding: utf-8 -*-

"""This script downloads and parses BioGRID data and maps the interaction types to BEL."""

import pandas as pd

import pybel.dsl
from bio2bel.utils import ensure_path
from pybel import BELGraph

from protmapper.uniprot_client import get_mnemonic

SEP = '\t'

BIOGRID2BEL_MAPPER = {
    # increases
    'synthetic genetic interaction defined by inequality': 'increases',
    'additive genetic interaction defined by inequality': 'increases',

    # decreases
    'suppressive genetic interaction defined by inequality': 'decreases',

    # association
    'direct interaction': 'association',
    'physical association': 'association',
    'colocalization': 'association',
    'association': 'association',
}

BIOGRID2BEL_FUNCTION_MAPPER = {
    'direct interaction': '',
    'suppressive genetic interaction defined by inequality': 'geneAbundance',
    'physical association': '',
    'colocalization': 'location',
    'synthetic genetic interaction defined by inequality': 'geneAbundance',
    'association': '',
    'additive genetic interaction defined by inequality': 'geneAbundance'
}

MODULE_NAME = 'biogrid'
URL = 'https://downloads.thebiogrid.org/File/BioGRID/Release-Archive/BIOGRID-3.5.183/BIOGRID-ALL-3.5.183.mitab.zip'


def _load_file(module_name: str = MODULE_NAME, url: str = URL) -> str:
    """Load the file from the URL and place it into the bio2bel_sophia directory.

    :param module_name: name of module (database)
    :param url: URL to file from database
    :return: path of saved database file
    """
    return ensure_path(prefix=module_name, url=url)


def _get_my_df() -> pd.DataFrame:
    """Get my dataframe."""
    path = _load_file()
    df = pd.read_csv(path)
    return df


def _get_sample_df(path: str, separator: str = '\t') -> pd.DataFrame:
    """Get sample dataframe of biogrid.

    :param path: file path to original file
    :param separator: separator for tsv file
    :return: sample dataframe
    """
    # making data frame from csv file
    data = pd.read_csv(path, sep=separator)

    # generating sample dataframe
    return data.sample(n=5)


def get_bel() -> BELGraph:
    """Get a BEL graph for IntAct.

    :return: BEL graph
    """
    df = _get_my_df()
    graph = BELGraph(name='intact')
    for _, row in df.iterrows():
        _add_my_row(graph, row)
    return graph


def _add_my_row(graph: BELGraph, row) -> None:
    relation = row['relation']
    source_uniprot_id = row['source']
    target_uniprot_id = row['target']

    pubmed_ids = row['pubmed_ids']
    pubmed_ids = pubmed_ids.split('|')

    source = pybel.dsl.Protein(
        namespace='uniprot',
        identifier=source_uniprot_id,
        name=get_mnemonic(source_uniprot_id),
    )
    target = pybel.dsl.Protein(
        namespace='uniprot',
        identifier=target_uniprot_id,
        name=get_mnemonic(target_uniprot_id),
    )

    for pubmed_id in pubmed_ids:
        if relation == 'deubiquitination':
            target_ub = target.with_variants(
                pybel.dsl.ProteinModification('Ub')
            )
            graph.add_decreases(
                source,
                target_ub,
                citation=pubmed_id,
                evidence='From intact',
            )
        elif relation == 'ubiqutination':
            target_ub = target.with_variants(
                pybel.dsl.ProteinModification('Ub')
            )
            graph.add_increases(
                source,
                target_ub,
                citation=...,
                evidence='From intact',
            )

        elif relation == 'degratation':
            graph.add_decreases(
                source,
                target,
                citation=...,
                evidence='From intact',
            )

        elif relation == 'activates':
            graph.add_increases(
                source,
                target,
                ...,
                object_modifier=pybel.dsl.activity(),
            )
        elif relation == 'co-expressed':
            graph.add_correlation(
                pybel.dsl.Rna(
                    namespace='uniprot',
                    identifier=source_uniprot_id,
                    name=get_mnemonic(source_uniprot_id),
                ),
                pybel.dsl.Rna(
                    namespace='uniprot',
                    identifier=target_uniprot_id,
                    name=get_mnemonic(target_uniprot_id),
                ),
                annotations=dict(
                    cell_line={'HEK2': True}
                ),
            )


def preprocess_biogrid() -> pd.DataFrame:
    """Load BioGRDID file, filter and rename columns and return a dataframe.

    :return: dataframe of preprocessed BioGRID data
    """
    return _get_my_df()
