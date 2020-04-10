# -*- coding: utf-8 -*-

"""This script downloads and parses BioGRID data and maps the interaction types to BEL."""

import os
from typing import Iterable, List

import pandas as pd
from protmapper.uniprot_client import get_mnemonic
from tqdm import tqdm

import pybel.dsl
from bio2bel.utils import ensure_path
from pybel import BELGraph

SEP = '\t'
BIOGRID = 'biogrid'
SOURCE = 'source'
TARGET = 'target'
RELATION = 'relation'
PUBMED_ID = 'pubmed_id'
UNIPROT = 'uniprot'
EVIDENCE = 'From BioGRID'
MODULE_NAME = 'biogrid'

VERSION = '3.5.183'
BASE_URL = 'https://downloads.thebiogrid.org/Download/BioGRID/Release-Archive'
URL = f'{BASE_URL}/BIOGRID-{VERSION}/BIOGRID-ALL-{VERSION}.mitab.zip'

HOME = os.path.expanduser('~')
BIO2BEL_DIR = os.path.join(HOME, '.bio2bel')
BIOGRID_FILE = os.path.join(BIO2BEL_DIR, 'biogrid/BIOGRID-ALL-3.5.183.mitab.txt')
SAMPLE_BIOGRID_FILE = os.path.join(BIO2BEL_DIR, 'biogrid/biogrid_sample.txt')

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

BIOGRID_COLUMN_MAPPER = {
    'Alt IDs Interactor A': SOURCE,
    'Alt IDs Interactor B': TARGET,
    'Interaction Types': RELATION,
    'Publication Identifiers': PUBMED_ID,

}


def _get_my_df() -> pd.DataFrame:
    """Get the BioGrid dataframe."""
    path = ensure_path(prefix=MODULE_NAME, url=URL)
    return pd.read_csv(path, sep='\t', compression='zip', dtype=str)

def _write_sample_df() -> None:
    """Write a sample dataframe to file."""
    path = ensure_path(prefix=MODULE_NAME, url=URL)
    with ZipFile(path) as zip_file:
        with zip_file.open(f'BIOGRID-ALL-{VERSION}.mitab.txt') as file:
            df = pd.read_csv(file, sep='\t')
            df.head().to_csv(SAMPLE_BIOGRID_FILE, sep=SEP)


def _get_sample_df() -> pd.DataFrame:
    """Get sample dataframe of intact.

    :return: sample dataframe
    """
    return pd.read_csv(SAMPLE_BIOGRID_FILE, sep=SEP)


def filter_biogrid_df(df: pd.DataFrame) -> pd.DataFrame:
    """Filter the original BioGRID dataframe containing the entire database and return dataframe with columns \
    for source, target, relation and pubmed_id.

    :param df: intact dataframe to be preprocessed
    :return: dataframe with source, target, relation, pubmed_id columsn
    """
    # take relevant columns for source, target, relation and PubMed ID
    df = df[[SOURCE, TARGET, RELATION, PUBMED_ID]]

    return df


def filter_for_prefix_single(list_ids: Iterable[str], prefix: str, separator: str = '|') -> List[List[str]]:
    """Split the Iterable by the separator.

    :param separator: separator between ids
    :param prefix: prefix to filter for (e.g. 'pubmed')
    :param list_ids: list of identifiers
    :return: filtered list of ids
    """
    final_list = []
    for ids in list_ids:
        id_list = ids.split(separator)
        flag = False
        for i in id_list:
            if i.startswith(prefix):
                final_list.append(i)
                flag = True
        if not flag:
            final_list.append(f'no {prefix} id')
    return final_list


def filter_for_prefix_multi(list_ids: Iterable[str], prefix: str, separator: str = '|') -> List[List[str]]:
    """Split the Iterable by the separator.

    :param separator: separator between ids
    :param prefix: prefix to filter for (e.g. 'pubmed')
    :param list_ids: list of identifiers
    :return: filtered list of lists of ids
    """
    final_list = []
    for ids in list_ids:
        id_list = ids.split(separator)
        flag = False
        row_list = []
        for i in id_list:
            if i.startswith(prefix):
                row_list.append(i)
                flag = True
        if not flag:
            row_list.append(f'no {prefix} id')
        final_list.append(row_list)
    return final_list


def get_processed_biogrid() -> pd.DataFrame:
    """Load BioGRDID file, filter and rename columns and return a dataframe.

    :return: dataframe of preprocessed BioGRID data
    """
    df = _get_my_df()
    # rename columns
    df = df.rename(columns=BIOGRID_COLUMN_MAPPER)

    # filter for source, target, relation, pubmed ids
    df = filter_biogrid_df(df)

    # filter for uniprot
    df[SOURCE] = filter_for_prefix_single(list_ids=df[SOURCE], prefix=UNIPROT)
    df[TARGET] = filter_for_prefix_single(list_ids=df[TARGET], prefix=UNIPROT)

    return df


def get_bel() -> BELGraph:
    """Get a BEL graph for IntAct.

    :return: BEL graph
    """
    df = _get_my_df()
    graph = BELGraph(name=BIOGRID)
    for _, row in tqdm(df.iterrows(), total=len(df.index), desc=f'mapping {BIOGRID}'):
        _add_my_row(graph, row)
    return graph


def _add_my_row(graph: BELGraph, row) -> None:  # noqa:C901
    """Add for every pubmed ID an edge with information about relationship type, source and target.

    :param graph: graph to add edges to
    :param row: row with metainformation about source, target, relation, pubmed_id
    :return: None
    """
    relation = row[RELATION]
    source_uniprot_id = row[SOURCE]
    target_uniprot_id = row[TARGET]

    pubmed_ids = row[PUBMED_ID]

    source = pybel.dsl.Protein(
        namespace='uniprot/swiss-prot',
        identifier=source_uniprot_id,
        name=get_mnemonic(source_uniprot_id),
    )
    target = pybel.dsl.Protein(
        namespace='uniprot/swiss-prot',
        identifier=target_uniprot_id,
        name=get_mnemonic(target_uniprot_id),
    )

    for pubmed_id in pubmed_ids:

        # INCREASES
        if relation in BIOGRID_INCREASES_ACTIONS:
            graph.add_increases(
                source,
                target,
                citation=pubmed_id,
                evidence=EVIDENCE,
            )

        # DECREASES
        elif relation in BIOGRID_DECREASES_ACTIONS:
            graph.add_decreases(
                source,
                target,
                citation=pubmed_id,
                evidence=EVIDENCE,
            )

        # ASSOCIATION
        elif relation in BIOGRID_ASSOCIATION_ACTIONS:
            graph.add_association(
                source,
                target,
                citaion=pubmed_id,
                evidence=EVIDENCE,
            )

        # no specified relation
        else:
            raise ValueError(f"The relation {relation} is not in the specified relations.")


if __name__ == '__main__':
    get_bel().summarize()
