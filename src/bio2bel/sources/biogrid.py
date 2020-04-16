# -*- coding: utf-8 -*-

"""This script downloads and parses BioGRID data and maps the interaction types to BEL."""

import logging
import os

import numpy as np
import pandas as pd
import pybel.dsl
from protmapper.uniprot_client import get_mnemonic
from pybel import BELGraph
from tqdm import tqdm
from typing import Iterable, List

from bio2bel.constants import BIOGRID_RESULTS_DIR
from bio2bel.utils import ensure_path

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

GENETIC_INTERACTIONS_PATH = os.path.join(BIOGRID_RESULTS_DIR, 'genetic_interactions.tsv')

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

logger = logging.getLogger(__name__)


def _get_my_df() -> pd.DataFrame:
    """Get the BioGrid dataframe."""
    path = ensure_path(prefix=MODULE_NAME, url=URL)[:-3] + 'txt'
    # TODO use original df
    # path = '/Users/sophiakrix/.bio2bel/biogrid/biogrid_sample.tsv'
    logger.info(path)
    return pd.read_csv(path, sep='\t', dtype=str)


def filter_for_prefix_single(
        list_ids: Iterable[str],
        prefix: str,
        rstrip: str = ' ',
        lstrip: str = ' ',
        separator: str = '|',
) -> List[List[str]]:
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


def filter_for_prefix_multi(
        list_ids: Iterable[str],
        prefix: str,
        separator: str = '|',
) -> List[List[str]]:
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
    # identify columns with single values that do not need to be expanded
    columns_to_keep = df.columns.to_list()
    columns_to_keep.remove(column_name)

    # create expanded df
    lens = [len(item) for item in df[column_name]]

    # create dictionary of columns and values (repeated)
    df_to_keep = {column: np.repeat(a=df[column].values, repeats=lens) for column in columns_to_keep}
    # flatten array of column with multiple values to 1d
    array_flattened = np.array(df[column_name].values).flatten()
    # expand array to 2d
    array_expanded = array_flattened.reshape(len(df_to_keep[columns_to_keep[0]]), 1)
    df_expanded = {column_name: array_expanded}

    df_merged = {**df_to_keep, **df_expanded}

    return pd.DataFrame.from_dict(data=df_merged, orient='index')


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
    for column in [SOURCE, TARGET]:
        df[column] = filter_for_prefix_single(list_ids=df[column], prefix=UNIPROT)

    # also in alternative ids
    for column in [ALT_SOURCE_ID, ALT_TARGET_ID]:
        df[column] = filter_for_prefix_multi(list_ids=df[column], prefix=UNIPROT)

    # drop rows if no uniprot id
    for column, alt_column in zip([SOURCE, TARGET], [ALT_SOURCE_ID, ALT_TARGET_ID]):
        df = df.dropna(subset=[column, alt_column], how='all', inplace=True)

    # change uniprot/swiss-prot prefix to uniprot
    df = df.replace(r'^uniprot/swissprot:.*', r'uniprot:.*', regex=True)

    # TODO: get working
    # expand dataframe if multiple uniprot ids exist
    # df = expand_df(df=df, column_name=ALT_SOURCE_ID)
    # df = expand_df(df=df, column_name=ALT_TARGET_ID)

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
        _add_my_row(
            graph,
            relation=row[RELATION],
            source_uniprot_id=row[SOURCE],
            target_uniprot_id=row[TARGET],
            pubmed_ids=row[PUBMED_ID,
        )
    return graph


def _add_my_row(
        graph: BELGraph,
        relation: str,
        source_uniprot_id: str,
        target_uniprot_id: str,
        pubmed_ids: str,
) -> None:  # noqa:C901
    """Add for every pubmed ID an edge with information about relationship type, source and target.

    :param graph: graph to add edges to
    :param relation: row value of column relation
    :param source_uniprot_id: row value of column source
    :param target_uniprot_id: row value of column target
    :param pubmed_ids: row value of column pubmed_ids
    :return: None
    """
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
            raise ValueError(f'Unhandled BioGrid relation: {relation}')


def get_genetic_interactions():
    df = get_processed_biogrid()
    df_syn = df.loc[df[RELATION] == 'synthetic genetic interaction defined by inequality']
    df_add = df.loc[df[RELATION] == 'additive genetic interaction defined by inequality']
    df_sup = df.loc[df[RELATION] == 'suppressive genetic interaction defined by inequality']

    frames = [df_syn, df_add, df_sup]

    return pd.concat(frames)


def get_genetic_interactions_pmid():
    df = pd.read_csv(GENETIC_INTERACTIONS_PATH)
    print(df.columns)
    return set(df[PUBMED_ID].values)


if __name__ == '__main__':
    # get_processed_biogrid()
    # df = get_processed_biogrid()

    # get_genetic_interactions().to_csv(GENETIC_INTERACTIONS_PATH)

    print(get_genetic_interactions_pmid())
