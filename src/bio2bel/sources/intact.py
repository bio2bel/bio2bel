# -*- coding: utf-8 -*-

"""This script downloads and parses IntAct data and maps the interaction types to BEL."""

from typing import Dict, Iterable, List

import pandas as pd
from protmapper.uniprot_client import get_mnemonic

import pybel.dsl
from bio2bel.utils import ensure_path
from pybel import BELGraph

SEP = '\t'

INTACT2BEL_MAPPER = {
    # increases
    'phosphorylation reaction': 'increases',
    'sumoylation reaction': 'increases',
    'methylation reaction': 'increases',
    'transglutamination reaction': 'increases',
    'ubiquitination reaction': 'increases',
    'acetylation reaction': 'increases',
    'adp ribosylation reaction': 'increases',
    'neddylation reaction': 'increases',
    'hydroxylation reaction': 'increases',
    'phosphotransfer reaction': 'increases',
    'glycosylation reaction': 'increases',
    'palmitoylation reaction': 'increases',

    # decreases
    'deubiquitination reaction': 'decreases',
    'protein cleavage': 'decreases',
    'cleavage reaction': 'decreases',
    'deacetylation reaction': 'decreases',
    'lipoprotein cleavage reaction': 'decreases',
    'dna cleavage': 'decreases',
    'rna cleavage': 'decreases',
    'dephosphorylation reaction': 'decreases',

    # association
    'physical association': 'association',
    'association': 'association',
    'colocalization': 'association',
    'direct interaction': 'association',
    'enzymatic reaction': 'association',
    'atpase reaction': 'association',
    'self interaction': 'association',
    'gtpase reaction': 'association',
    'putative self interaction': 'association',

    # hasComponent  -> association
    'covalent binding': 'hasComponent',
    'disulfide bond': 'hasComponent',
}

INTACT2BEL_FUNCTION_MAPPER = {
    # complexAbundance
    'covalent binding': 'complexAbundance',

    # protein Modification
    'deubiquitination reaction': 'proteinModification(Ub)',
    'phosphorylation reaction': 'proteinModification(Ph)',
    'sumoylation reaction': 'proteinModification',
    'methylation reaction': 'proteinModification(Me)',
    'transglutamination reaction': 'proteinModification',
    'ubiquitination reaction': 'proteinModification(Ub)',
    'acetylation reaction': 'proteinModification',
    'adp ribosylation reaction': 'proteinModification',
    'dephosphorylation reaction': 'proteinModification(Ph)',
    'neddylation reaction': 'proteinModification',
    'hydroxylation reaction': 'proteinModification',

    # location
    'colocalization': 'location',

    # degradation
    'protein cleavage': 'degradation',
    'cleavage reaction': 'degradation',

    'physical association': '',
    'association': '',

    'direct interaction': '',

    'enzymatic reaction': '',

    'atpase reaction': 'reaction',
    'phosphotransfer reaction': 'proteinModification',
    'disulfide bond': 'complexAbundance',
    'self interaction': '',
    'deacetylation reaction': '',
    'lipoprotein cleavage reaction': 'proteinAbundance',
    'gtpase reaction': 'reaction',
    'glycosylation reaction': 'proteinModification(Glyco)',
    'palmitoylation reaction': 'proteinModification',
    'putative self interaction': '',
    'dna cleavage': 'geneAbundance',
    'rna cleavage': 'rnaAbundace',
}

MODULE_NAME = 'intact'
URL = 'ftp://ftp.ebi.ac.uk/pub/databases/intact/current/psimitab/intact.zip'
path = ensure_path(MODULE_NAME, URL)
sample_path = '/Users/sophiakrix/Downloads/intact_sample.txt'

ID_INTA = '#ID(s) interactor A'
ID_INTB = 'ID(s) interactor B'
INTERACTION_TYPES = 'Interaction Type(s)'
PUBLICATION_ID = 'Publication Identifier(s)'
DATABASE_INT_A = 'database_intA'
DATABASE_INT_B = 'database_intB'
ONLY_ID_INT_A = 'id_intA'
ONLY_ID_INT_B = 'id_intB'
UNIPROTKB = 'uniprotkb'
SOURCE = 'source'
TARGET = 'target'
RELATION = 'relation'
PUBMED_ID = 'pubmed_id'
columns_mapping = {
    '#ID(s) interactor A': SOURCE,
    'ID(s) interactor B': TARGET,
    'Interaction Type(s)': RELATION,
    'Publication Identifier(s)': PUBMED_ID,
}


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
    df = pd.read_csv(path, sep=SEP, compression='zip')
    return df


def rename_columns(df: pd.DataFrame, columns_mapping: Dict) -> pd.DataFrame:
    """Rename the columns in a dataframe according to the specified values in the dictionary.

    :param df: dataframe with columns to be renamed
    :param columns_mapping: mapping from original column names to new column names
    :return: renamed dataframe
    """
    return df.rename(columns=columns_mapping)


def read_intact_file(df: pd.DataFrame) -> pd.DataFrame:
    """Read in a .txt file from IntAct containing the entire database and return dataframe with columns \
    for source, target, relation and pubmed_id.

    :param df: intact dataframe to be preprocessed
    :return: dataframe with IntAct information
    """
    print('Dataframe is being created from the file.')

    # take relevant columns for source, target, relation and PubMed ID
    df = df.loc[:, [SOURCE, TARGET, RELATION, PUBMED_ID]]

    # drop nan value rows for interactor B
    df = df.loc[df[TARGET] != '-', :]

    return df


def split_to_list(unsplitted_list: str, separator: str = '|') -> List:
    """Split a list of strings that contains multiple values that are separated by a defined separator into a list of lists.

    :param unsplitted_list: list of strings to be splitted
    :param separator: separator between elements
    :return: list of lists of splitted elements
    """
    return [x.split(separator) for x in unsplitted_list]


def split_column_str_to_list(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """Split the values of a column that has a string containing multiple values by a separator.

    :param df: dataframe with string to be splitted
    :param column_name: column name of string to be splitted
    :return: dataframe with list of splitted elements
    """
    list_column = df.loc[:, column_name]
    splitted_lists = split_to_list(list_column, separator='|')

    df.loc[:, column_name] = splitted_lists

    return df


def list_pubmed(publication_ids: Iterable[str]) -> List[str]:
    """Filter the publication ids for Pubmed IDs.

    :param publication_ids: list of publication ids
    :return: filtered list of pubmed ids
    """
    final_list = []
    for publications in publication_ids:
        publications_list = split_to_list(publications, separator='|')
        flag = False
        for i in publications_list:
            if i.startswith('pubmed:'):
                final_list.append(i)
                flag = True
        if not flag:
            final_list.append('no pubmed id')

    return final_list


def filter_for_pubmed(df: pd.DataFrame, column_name: str):
    """Filter the publication ids for pubmed ids.

    :param df: dataframe
    :param column_name: column with publication ids
    :return: dataframe with filtered column
    """
    pubmed_list = list_pubmed(df.loc[:, column_name])
    df = add_to_df(df=df, column_name=column_name, list_to_add=pubmed_list)
    return df


def add_to_df(df: pd.DataFrame, column_name: str, list_to_add: List) -> pd.DataFrame:
    """Add a column to a dataframe.

    :param df: dataframe
    :param column_name: column name
    :param list_to_add: list to be added in column in the dataframe
    :return: df with updated column
    """
    df.loc[:, column_name] = list_to_add
    return df


def get_processed_intact_df() -> pd.DataFrame:
    """Load, filter and rename intact dataframe.

    :return: processed dataframe
    """
    print(_load_file())
    # original intact dataframe
    df = _get_my_df()

    # rename columns
    df = rename_columns(df=df, columns_mapping=columns_mapping)

    # initally preprocess intact file
    df = read_intact_file(df)

    # filter for pubmed
    df = filter_for_pubmed(df, PUBLICATION_ID)

    return df


# TODO: add edges


def get_bel() -> BELGraph:
    """Get BEL graph.

    :return: BEL graph#
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

        if relation == 'phosphorylation reaction':
            target_ub = target.with_variants(
                pybel.dsl.ProteinModification('Ph')
            )
            graph.add_decreases(
                source,
                target_ub,
                citation=pubmed_id,
                evidence='From intact',
            )

        # ===========CHARLIE==============

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


if __name__ == '__main__':
    get_processed_intact_df()
