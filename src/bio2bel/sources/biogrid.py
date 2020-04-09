# -*- coding: utf-8 -*-

"""This script downloads and parses BioGRID data and maps the interaction types to BEL."""

import pandas as pd

import pybel.dsl
from bio2bel.utils import ensure_path
from pybel import BELGraph

from protmapper.uniprot_client import get_mnemonic

# from ..constants import BIOGRID_ASSOCIATION_ACTIONS, BIOGRID_DECREASES_ACTIONS, BIOGRID_INCREASES_ACTIONS

SEP = '\t'
BIOGRID = 'biogrid'
SOURCE = 'source'
TARGET = 'target'
RELATION = 'relation'
PUBMED_ID = 'pubmed_id'
MODULE_NAME = 'biogrid'
VERSION = '3.5.183'
BASE_URL = 'https://downloads.thebiogrid.org/Download/BioGRID/Release-Archive'
URL = f'{BASE_URL}/BIOGRID-{VERSION}/BIOGRID-ALL-{VERSION}.mitab.zip'

#: Relationship types in BioGRID that map to BEL relation 'increases'
BIOGRID_INCREASES_ACTIONS = {
    'synthetic genetic interaction defined by inequality',
    'additive genetic interaction defined by inequality',
}

#: Relationship types in BioGRID that map to BEL relation 'decreases'
BIOGRID_DECREASES_ACTIONS = {
    'suppressive genetic interaction defined by inequality',
}

#: Relationship types in BioGRID that map to BEL relation 'association'
BIOGRID_ASSOCIATION_ACTIONS = {
    'direct interaction',
    'physical association',
    'colocalization',
    'association',
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


def _load_file(module_name: str = MODULE_NAME, url: str = URL) -> str:
    """Load the file from the URL and place it into the bio2bel_sophia directory.

    :param module_name: name of module (database)
    :param url: URL to file from database
    :return: path of saved database file
    """
    return ensure_path(prefix=module_name, url=url)


def _get_my_df() -> pd.DataFrame:
    """Get my dataframe.

    :return: original dataframe
    """
    path = _load_file()
    df = pd.read_csv(path, sep=SEP, compression='zip')
    return df


def _get_sample_df(path: str, separator: str = '\t') -> pd.DataFrame:
    """Get sample dataframe of biogrid.

    :param path: file path to original file
    :param separator: separator for tsv file
    :return: sample dataframe
    """
    # making data frame from csv file
    # TODO: uncomment and solve zip file issue
    data = pd.read_csv('/Users/sophiakrix/Downloads/biogrid_sample.txt', sep=separator)
    #data = pd.read_csv(path, sep=separator)
    print(data.columns)
    # generating sample dataframe
    return data.sample(n=5)


def get_bel() -> BELGraph:
    """Get a BEL graph for IntAct.

    :return: BEL graph
    """
    df = _get_my_df()
    graph = BELGraph(name=BIOGRID)
    for _, row in df.iterrows():
        _add_my_row(graph, row)
    return graph


def get_processed_biogrid() -> pd.DataFrame:
    """Load BioGRDID file, filter and rename columns and return a dataframe.

    :return: dataframe of preprocessed BioGRID data
    """
    df = _get_my_df()

    return df


def _add_my_row(graph: BELGraph, row) -> None:  # noqa:C901
    """Add for every pubmed ID an edge with information about relationship type, source and target.

    :param graph: graph to add edges to
    :param row: row with metainformation about source, target, relation, pubmed_id
    :return: None
    """
    relation = row[RELATION]
    source_uniprot_id = row[SOURCE]
    target_uniprot_id = row[TARGET]

    pubmed_ids = row['pubmed_ids']
    # pubmed_ids = pubmed_ids.split('|')

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

        # INCREASE
        if relation in BIOGRID_INCREASES_ACTIONS:
            pass
    # =========================================
        if relation == 'deubiquitination':
            target_mod = target.with_variants(
                pybel.dsl.ProteinModification('Ub')
            )
            graph.add_decreases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence='From intact',
            )
        elif relation == 'ubiqutination':
            target_mod = target.with_variants(
                pybel.dsl.ProteinModification('Ub')
            )
            graph.add_increases(
                source,
                target_mod,
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


if __name__ == '__main__':
    print(get_processed_biogrid())
