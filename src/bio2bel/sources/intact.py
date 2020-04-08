# -*- coding: utf-8 -*-

"""This script downloads and parses IntAct data and maps the interaction types to BEL."""

import pandas as pd

from typing import List
from protmapper.uniprot_client import get_mnemonic
from bio2bel.utils import ensure_path
import pybel.dsl
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
DATABASE_INT_A = 'database_intA'
DATABASE_INT_B = 'database_intB'
ONLY_ID_INT_A = 'id_intA'
ONLY_ID_INT_B = 'id_intB'
UNIPROTKB = 'uniprotkb'
ORIG_ALT_ID_COLUMN_NAMES = ['Alt. ID(s) interactor A', 'Alt. ID(s) interactor B']
NEW_ALT_ID_COLUMN_NAMES = ['alternative_intA', 'alternative_intB']


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
    df = pd.read_csv(path, sep=SEP)
    return df


def read_intact_file(df: pd.DataFrame) -> pd.DataFrame:
    """Read in a .txt file from IntAct containing the entire database and
    return a dataframe with additional columns:
    - 'intA_database' : the database for interactor A
    - 'intB_database' : the database for interactor B

    :param df: intact dataframe to be preprocessed

    :return: dataframe with IntAct information
    """
    print('Dataframe is being created from the file.')

    '''
    In the line below, the entries of '-' are excluded explicitly, because this is not a path
    we can continue along to find a transcription factor. Also if an interaction has led to
    this protein, it will be checked there as the second interactor. Therefore, these entries
    are not included.
    '''
    df = df.loc[df['ID(s) interactor B'] != '-', :]

    # add column for identifier database
    int_a = df.loc[:, ID_INTA]
    int_b = df.loc[:, ID_INTB]

    database_a = [x.split(':')[0] for x in int_a]
    database_b = [x.split(':')[0] for x in int_b]

    identifiers_a = [x.split(':')[1] for x in int_a]
    identifiers_b = [x.split(':')[1] for x in int_b]

    df[DATABASE_INT_A] = database_a
    df[DATABASE_INT_B] = database_b

    df[ONLY_ID_INT_A] = identifiers_a
    df[ONLY_ID_INT_B] = identifiers_b

    return df


def get_alternative_id(column_name: str) -> List[List]:
    """Split the "Alt. ID(s) interactor A" column into the individual IDs and
    filter for the uniprot IDs.

    :param column_name: the column name of the original df
        with the alternative ids to be transformed

    :return: nested list of alternative IDs for every protein
    """
    df = read_intact_file()
    alt_int_a = df.loc[:, column_name]
    all_alt_int_a = [x.split('|') for x in alt_int_a]

    new_list = []
    for protein in all_alt_int_a:
        protein_list = []
        for name in protein:
            if UNIPROTKB in name:
                name = name.split(':')[1]
                protein_list.append(name)
        new_list.append(protein_list)
    return new_list


def add_alternative_id(df: pd.DataFrame) -> pd.DataFrame:
    """Add a new column with the alternative IDs to the dataframe.

    :return: dataframe with additional columns for alternative IDs
    """
    for orig, new in zip(ORIG_ALT_ID_COLUMN_NAMES, NEW_ALT_ID_COLUMN_NAMES):
        df.loc[:, new] = get_alternative_id(orig)
    return df


def rename_all_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Input a dataframe, the function changes all column names to lower case, deletes non-alphabetical/numerical
    and replaces spaces with underscores.

    :return: dataframe with renamed columns
    """
    col_dict = {}

    for col in df.columns:
        col_dict[col] = col.lower().replace("(", "").replace(")", "").replace("#", "").replace(" ", "_").replace(
            ".", '')
    df = df.rename(columns=col_dict)

    return df



def get_bel() -> BELGraph:
    """Get BEL graph.

    :return:
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

def get_processed_intact_df():
    # original intact dataframe
    df = _get_my_df()
    # initally preprocess intact file
    df = read_intact_file(df)
    # additional ids
    df = add_alternative_id(df)
    # rename columns to easy accessible and understandable values
    df = rename_all_columns(df)

    print(df.head())


    #print(_get_my_df(sample_path).head())
    #print(_get_my_df(sample_path).loc[:5, 'Publication Identifier(s)'])


if __name__ == '__main__':
    get_processed_intact_df()
