# -*- coding: utf-8 -*-

"""This script downloads and parses BioGRID data and maps the interaction types to BEL."""

import logging
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
ALT_SOURCE_ID = 'alt_source_id'
ALT_TARGET_ID = 'alt_target_id'
RELATION = 'relation'
PUBMED_ID = 'pubmed_id'
UNIPROT = 'uniprot'
EVIDENCE = 'From BioGRID'
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

BIOGRID_COLUMN_MAPPER = {
    '#ID Interactor A': SOURCE,
    'ID Interactor B': TARGET,
    'Alt IDs Interactor A': ALT_SOURCE_ID,
    'Alt IDs Interactor B': ALT_TARGET_ID,
    'Interaction Types': RELATION,
    'Publication Identifiers': PUBMED_ID,
}

log = logging.getLogger(__name__)


def _get_my_df() -> pd.DataFrame:
    """Get the BioGrid dataframe."""
    path = ensure_path(prefix=MODULE_NAME, url=URL)[:-3] + 'txt'
    log.info(path)
    return pd.read_csv(path, sep='\t', dtype=str)


def filter_for_prefix_single(list_ids: Iterable[str], prefix: str, rstrip: str = ' ', lstrip: str = ' ',
                             separator: str = '|') -> List[List[str]]:
    """Split the Iterable by the separator.

    :param separator: separator between ids
    :param prefix: prefix to filter for (e.g. 'pubmed')
    :param rstrip: characters to strip from split value from left
    :param lstrip: characters to strip from split value from right
    :param list_ids: list of identifiers
    :return: filtered list of ids
    """
    final_list = []
    for ids in list_ids:
        id_list = ids.split(separator)
        flag = False
        for i in id_list:
            if i.startswith(prefix):
                final_list.append(i.lstrip(lstrip).rstrip(rstrip))
                flag = True
        if not flag:
            final_list.append('nan')
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
        # if no matching value with prefix is found, append 'nan' as individual value
        if not flag:
            final_list.append('nan')
        # if at least one value is found, append list
        if len(row_list) > 0:
            final_list.append(row_list)
    return final_list


def expand_df(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """Add row with same content to dataframe if there are multiple values in one column.

    The specified column must contain an Iterable.

    :param column_name: name of column with multiple values to be simplified
    :param df: dataframe with multiple values in one column
    :return: dataframe with expanded values
    """
    for index, row in df.iterrows():
        # if there are multiple entries in the column
        if len(row[column_name]) > 1:
            # for every id, copy the entire row and add to df
            for item in row[column_name]:
                copied_row = df.loc[index, row]
                # replace multiple values by single value
                copied_row[index] = item
                # add expanded row to df
                df.append(copied_row)

            # remove row with multiple values
            df = df.drop([index])

    return df


def get_processed_biogrid() -> pd.DataFrame:
    """Load BioGRDID file, filter and rename columns and return a dataframe.

    :return: dataframe of preprocessed BioGRID data
    """
    df = _get_my_df()
    # rename columns
    df = df.rename(columns=BIOGRID_COLUMN_MAPPER)

    # take relevant columns for source, target, alternative ids, relation and PubMed ID
    df = df[[SOURCE, TARGET, ALT_SOURCE_ID, ALT_TARGET_ID, RELATION, PUBMED_ID]]

    # filter for uniprot
    df[SOURCE] = filter_for_prefix_single(list_ids=df[SOURCE], prefix=UNIPROT)
    df[TARGET] = filter_for_prefix_single(list_ids=df[TARGET], prefix=UNIPROT)
    # also in alternative ids
    df[ALT_SOURCE_ID] = filter_for_prefix_multi(list_ids=df[ALT_SOURCE_ID], prefix=UNIPROT)
    df[ALT_TARGET_ID] = filter_for_prefix_multi(list_ids=df[ALT_TARGET_ID], prefix=UNIPROT)

    # drop rows if no uniprot id
    df = df.dropna(subset=[SOURCE, ALT_SOURCE_ID], how='all')
    df = df.dropna(subset=[TARGET, ALT_TARGET_ID], how='all')

    # expand dataframe if multiple uniprot ids exist
    df = expand_df(df=df, column_name=ALT_SOURCE_ID)
    df = expand_df(df=df, column_name=ALT_TARGET_ID)

    # filter for relation
    df[RELATION] = filter_for_prefix_single(
        list_ids=df[RELATION],
        rstrip=')',
        lstrip='(',
        separator='"',
        prefix='(',
    )

    return df


def get_bel() -> BELGraph:
    """Get a BEL graph for IntAct.

    :return: BEL graph
    """
    df = get_processed_biogrid()
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
    print(get_processed_biogrid())
