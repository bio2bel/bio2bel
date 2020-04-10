# -*- coding: utf-8 -*-

"""This script downloads and parses IntAct data and maps the interaction types to BEL."""

from typing import Dict, Iterable, List
from zipfile import ZipFile

import pandas as pd
import pybel.dsl
from bio2bel.utils import ensure_path
from protmapper.uniprot_client import get_mnemonic
from pybel import BELGraph
from pybel.dsl import ProteinModification
from tqdm import tqdm

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
    'oxidoreductase activity electron transfer reaction',
    'amidation reaction',
    'dna strand elongation',
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
    'deformylation reaction',
    'demethylation reaction',
    'deneddylation reaction',
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

PROTEIN_MOD_DICT = {
    'phosphorylation reaction': 'Ph',
    'sumoylation reaction': 'Sumo',
    'methylation reaction': 'Me',
    'transglutamination reaction': 'Gln',
    'ubiquitination reaction': 'Ub',
    'acetylation reaction': 'Ac',
    'adp ribosylation reaction': 'ADPRib',
    'neddylation reaction': 'Nedd',
    'hydroxylation reaction': 'Hy',
    'phosphotransfer reaction': 'Ph',
    'glycosylation reaction': 'Glyco',
    'palmitoylation reaction': 'Palm',
    'deubiquitination reaction': 'Ub',
    'deacetylation reaction': 'Ac',
    'dephosphorylation reaction': 'Ph',
}

EVIDENCE = 'From IntAct'
SEP = '\t'

MODULE_NAME = 'intact'
VERSION = '2020-03-31'
URL = f'ftp://ftp.ebi.ac.uk/pub/databases/intact/{VERSION}/psimitab/intact.zip'

ID_INTA = '#ID(s) interactor A'
ID_INTB = 'ID(s) interactor B'
INTERACTION_TYPES = 'Interaction Type(s)'
PUBLICATION_ID = 'Publication Identifier(s)'
UNIPROTKB = 'uniprotkb'
SOURCE = 'source'
TARGET = 'target'
RELATION = 'relation'
PUBMED_ID = 'pubmed_id'
COLUMNS_MAPPING = {
    '#ID(s) interactor A': SOURCE,
    'ID(s) interactor B': TARGET,
    'Interaction type(s)': RELATION,
    'Publication Identifier(s)': PUBMED_ID,
}

sample_path = '/Users/sophiakrix/.bio2bel/intact/intact_sample.tsv'


def _get_my_df() -> pd.DataFrame:
    """Get my dataframe.

    :return: original intact dataframe
    """
    path = ensure_path(prefix=MODULE_NAME, url=URL)
    with ZipFile(path) as zip_file:
        with zip_file.open('intact.txt') as file:
            return pd.read_csv(file, sep='\t')


def rename_columns(df: pd.DataFrame, columns_mapping: Dict) -> pd.DataFrame:
    """Rename the columns in a dataframe according to the specified values in the dictionary.

    :param df: dataframe with columns to be renamed
    :param columns_mapping: mapping from original column names to new column names
    :return: renamed dataframe
    """
    return df.rename(columns=columns_mapping)


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


def get_processed_intact_df() -> pd.DataFrame:
    """Load, filter and rename intact dataframe.

    :return: processed dataframe
    """
    # original intact dataframe
    df = _get_my_df()

    # rename columns
    df = rename_columns(df=df, columns_mapping=COLUMNS_MAPPING)

    # take relevant columns for source, target, relation and PubMed ID
    df = df[[SOURCE, TARGET, RELATION, PUBMED_ID]]

    # drop nan value rows for interactor B
    df = df[df[TARGET] != '-']

    # filter for uniprot ids
    df = df[df[SOURCE].str.contains("uniprot")]

    # filter for pubmed
    df[PUBMED_ID] = filter_for_prefix_multi(
        list_ids=df[PUBMED_ID],
        prefix='pubmed'
    )

    # filter interaction types
    df[RELATION] = filter_for_prefix_single(
        list_ids=df[RELATION],
        rstrip=')',
        lstrip='(',
        separator='"',
        prefix='('
    )

    return df


def get_bel() -> BELGraph:
    """Get BEL graph.

    :return: BEL graph
    """
    df = get_processed_intact_df()
    graph = BELGraph(name=MODULE_NAME)
    for _, row in tqdm(df.iterrows(), total=len(df.index), desc=f'mapping {MODULE_NAME}'):
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

    pubmed_ids = row[PUBMED_ID]

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
            # oxidoreductase activity
            if relation == 'oxidoreductase activity electron transfer reaction':
                graph.add_increases(
                    source,
                    target,
                    citation=pubmed_id,
                    evidence=EVIDENCE,
                    subject_modifier=pybel.dsl.BiologicalProcess(
                        name='oxidoreductase activity',
                        namespace='GO',
                        identifier='0016491'
                    ),
                )
            # protein amidation
            elif relation == 'amidation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(
                        name='protein amidation',
                        namespace='GO',
                        identifier='0018032',
                    ),
                )
            # dna strand elongation
            elif relation == 'dna strand elongation':
                target_mod = pybel.dsl.Gene(
                    name='DNA strand elongation',
                    namespace='GO',
                    identifier='0022616',

                )
            # take mapping from relation to abbreviation of reaction
            # protein modification
            elif relation in PROTEIN_MOD_DICT.keys():
                abbreviation = PROTEIN_MOD_DICT[relation]
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(abbreviation),
                )

                graph.add_increases(
                    source,
                    target_mod,
                    citation=pubmed_id,
                    evidence=EVIDENCE,
                )

        # DECREASES
        elif relation in INTACT_DECREASES_ACTIONS:

            # dna cleavage
            if relation == 'dna cleavage':
                target_mod = pybel.dsl.Gene(
                    namespace='uniprot',
                    identifier=source_uniprot_id,
                    name=get_mnemonic(source_uniprot_id),
                )
            # rna cleavage
            elif relation == 'rna cleavage':
                target_mod = pybel.dsl.Rna(
                    namespace='uniprot',
                    identifier=source_uniprot_id,
                    name=get_mnemonic(source_uniprot_id),
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
                continue

            # deformylation reaction
            elif relation == 'deformylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(
                        name='protein formylation',
                        namespace='GO',
                        identifier='0018256', ),
                )

            # demethylation reaction
            elif relation == 'demethylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('Me'),
                )

            # deneddylation reaction
            elif relation == 'deneddylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('Nedd'),
                )

            # protein modification
            elif relation in PROTEIN_MOD_DICT.keys():
                abbreviation = PROTEIN_MOD_DICT[relation]
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(abbreviation),
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
                citation=pubmed_id,
                evidence=EVIDENCE,
            )

        # BINDS
        elif relation in INTACT_BINDS_ACTIONS:

            graph.add_binds(
                source,
                target,
                citation=pubmed_id,
                evidence=EVIDENCE,
            )
        # no specified relation
        else:
            raise ValueError(f"The relation {relation} is not in the specified relations.")


if __name__ == '__main__':
    get_bel().summarize()
