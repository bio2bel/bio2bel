# -*- coding: utf-8 -*-

"""This script downloads and parses IntAct data and maps the interaction types to BEL."""

from typing import Dict, Iterable, List

import pandas as pd
from protmapper.uniprot_client import get_mnemonic

from zipfile import ZipFile
import pybel.dsl
from bio2bel.utils import ensure_path
from pybel import BELGraph

# from ..constants import INTACT_INCREASES_ACTIONS, INTACT_DECREASES_ACTIONS, INTACT_ASSOCIATION_ACTIONS, \
#     INTACT_BINDS_ACTIONS

#: Relationship types in IntAct that map to BEL relation 'increases'
INTACT_INCREASES_ACTIONS = {
    'phosphorylation reaction',
    'sumoylation reaction',
    'methylation reaction',
    'transglutamination reaction',
    'ubiquitination reaction',
    'acetylation reaction',
    'adp ribosylation reaction',
    'neddylation reaction',
    'hydroxylation reaction',
    'phosphotransfer reaction',
    'glycosylation reaction',
    'palmitoylation reaction',
}

#: Relationship types in IntAct that map to BEL relation 'decreases'
INTACT_DECREASES_ACTIONS = {
    # decreases
    'deubiquitination reaction',
    'protein cleavage',
    'cleavage reaction',
    'deacetylation reaction',
    'lipoprotein cleavage reaction',
    'dna cleavage',
    'rna cleavage',
    'dephosphorylation reaction',
}

#: Relationship types in IntAct that map to BEL relation 'association'
INTACT_ASSOCIATION_ACTIONS = {
    'physical association',
    'association',
    'colocalization',
    'direct interaction',
    'enzymatic reaction',
    'atpase reaction',
    'self interaction',
    'gtpase reaction',
    'putative self interaction',
}

#: Relationship types in IntAct that map to BEL relation 'hasComponent'
INTACT_BINDS_ACTIONS = {
    'covalent binding',
    'disulfide bond',
}

EVIDENCE = 'From IntAct'
SEP = '\t'

MODULE_NAME = 'intact'
VERSION = '2020-03-31'
URL = f'ftp://ftp.ebi.ac.uk/pub/databases/intact/{VERSION}/psimitab/intact.zip'
path = ensure_path(MODULE_NAME, URL)

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
    """Get my dataframe.

    :return: original intact dataframe
    """
    path = _load_file()
    with ZipFile(path) as zip_file:
        with zip_file.open('intact.txt') as file:
            return pd.read_csv(file, sep='\t')


def _get_sample_df() -> pd.DataFrame:
    """Get sample dataframe of intact.

    :return: sample dataframe
    """
    path = _load_file()
    with ZipFile(path) as zip_file:
        with zip_file.open('intact.txt') as file:
            head = file.readlines()[0:5]
            with open('sample_intact.txt', 'w') as f:
                f.writelines(head)

    return pd.read_csv('sample_intact.txt', sep=SEP)


def rename_columns(df: pd.DataFrame, columns_mapping: Dict) -> pd.DataFrame:
    """Rename the columns in a dataframe according to the specified values in the dictionary.

    :param df: dataframe with columns to be renamed
    :param columns_mapping: mapping from original column names to new column names
    :return: renamed dataframe
    """
    return df.rename(columns=columns_mapping)


def filter_intact_df(df: pd.DataFrame) -> pd.DataFrame:
    """Filter the original IntAct dataframe containing the entire database and return dataframe with columns \
    for source, target, relation and pubmed_id.

    :param df: intact dataframe to be preprocessed
    :return: dataframe with source, target, relation, pubmed_id columsn
    """
    # take relevant columns for source, target, relation and PubMed ID
    df = df[[SOURCE, TARGET, RELATION, PUBMED_ID]]

    # drop nan value rows for interactor B
    df = df[df[TARGET] != '-', :]

    return df


def filter_uniprot(df: pd.DataFrame) -> pd.DataFrame:
    """Filter the intact dataframe for uniprot ids.

    :param df: daframe with mixed protein identifiers
    :return: dataframe with only uniprot identifiers
    """
    return df[df[SOURCE].str.contains("uniprot")]


def split_to_list(unsplit_list: str, separator: str = '|') -> List:
    """Split a list of strings that contains multiple values that are separated by a defined separator into a list of lists.

    :param unsplit_list: list of strings to be splitted
    :param separator: separator between elements
    :return: list of lists of splitted elements
    """
    return [x.split(separator) for x in unsplit_list]


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
    df[[column_name]] = list_pubmed(df[[column_name]])
    return df


def get_processed_intact_df() -> pd.DataFrame:
    """Load, filter and rename intact dataframe.

    :return: processed dataframe
    """
    # original intact dataframe
    df = _get_my_df()
    # TODO: use original df

    # df = _get_sample_df()
    # rename columns
    df = rename_columns(df=df, columns_mapping=columns_mapping)

    # filter for uniprot ids
    df = filter_uniprot(df=df)

    # initally preprocess intact file
    df = filter_intact_df(df=df)

    # filter for pubmed
    df = filter_for_pubmed(df=df, column_name=PUBLICATION_ID)

    return df


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
        if relation in INTACT_INCREASES_ACTIONS:

            if relation == 'phosphorylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('Ph')
                )
            elif relation == 'sumoylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('Sumo')
                )
            elif relation == 'methylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('Me')
                )
            elif relation == 'transglutamination reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('Me')
                )
            elif relation == 'ubiquitination reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('Ub')
                )
            elif relation == 'acetylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('Ac')
                )
            elif relation == 'adp ribosylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('ADPRib')
                )
            elif relation == 'neddylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('Nedd')
                )
            elif relation == 'hydroxylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('Hy')
                )
            elif relation == 'phosphotransfer reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('Ph')
                )
            elif relation == 'glycosylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('Glyco')
                )
            elif relation == 'palmitoylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('Palm')
                )
            graph.add_increases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence=EVIDENCE,
            )

        # DECREASES
        elif relation in INTACT_DECREASES_ACTIONS:

            if relation == 'deubiquitination reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('Ub')
                )
            elif relation == 'deacetylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('Ac')
                )
            elif relation == 'dephosphorylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('Ph')
                )
            elif relation == 'dna cleavage':
                target_mod = pybel.dsl.Gene(
                    namespace='uniprot',
                    identifier=source_uniprot_id,
                    name=get_mnemonic(source_uniprot_id)
                )
            elif relation == 'rna cleavage':
                target_mod = pybel.dsl.Rna(
                    namespace='uniprot',
                    identifier=source_uniprot_id,
                    name=get_mnemonic(source_uniprot_id)
                )
            # both proteins
            elif relation == 'cleavage reaction' \
                    or relation == 'lipoprotein cleavage reaction' \
                    or relation == 'protein cleavage':
                graph.add_decreases(
                    source,
                    target,
                    citation=pubmed_id,
                    evidence=EVIDENCE,
                )

            graph.add_decreases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence=EVIDENCE,
            )

        # ASSOCIATION:
        elif relation in INTACT_ASSOCIATION_ACTIONS:

            graph.add_association(
                source,
                target,
                citaion=pubmed_id,
                evidence=EVIDENCE,
            )

        # BINDS
        elif relation in INTACT_BINDS_ACTIONS:

            graph.add_binds(
                source,
                target,
                citation=pubmed_id,
                evidence=EVIDENCE
            )
        # no specified relation -> association
        else:
            raise ValueError(f"The relation {relation} is not in the specified relations.")


if __name__ == '__main__':
    print(get_processed_intact_df())
