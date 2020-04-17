# -*- coding: utf-8 -*-

"""This script downloads and parses IntAct data and maps the interaction types to BEL."""

from zipfile import ZipFile

import pandas as pd
import pybel.dsl
from protmapper.uniprot_client import get_mnemonic
from pybel import BELGraph
from tqdm import tqdm
from typing import Dict, Iterable, List

from bio2bel.utils import ensure_path

#: Relationship types in IntAct that map to BEL relation 'increases'
INTACT_INCREASES_ACTIONS = {
    'psi-mi:"MI:1143"(aminoacylation reaction)',
    'psi-mi:"MI:0214"(myristoylation reaction)',
    'psi-mi:"MI:1237"(proline isomerization reaction)',
    'psi-mi:"MI:0211"(lipid addition)',
    'psi-mi:"MI:0213"(methylation reaction)',
    'psi-mi:"MI:0217"(phosphorylation reaction)',
    'psi-mi:"MI:0882"(atpase reaction)',
    'psi-mi:"MI:1250"(isomerase reaction)',
    'psi-mi:"MI:0210"(hydroxylation reaction)',
    'psi-mi:"MI:0883"(gtpase reaction)',
    'psi-mi:"MI:0557"(adp ribosylation reaction)',
    'psi-mi:"MI:0193"(amidation reaction)',
    'psi-mi:"MI:1327"(sulfurtransfer reaction)',
    'psi-mi:"MI:0567"(neddylation reaction)',
    'psi-mi:"MI:0556"(transglutamination reaction)',
    'psi-mi:"MI:0220"(ubiquitination reaction)',
    'psi-mi:"MI:0559"(glycosylation reaction)',
    'psi-mi:"MI:0192"(acetylation reaction)',
    'psi-mi:"MI:0216"(palmitoylation reaction)',
    'psi-mi:"MI:0945"(oxidoreductase activity electron transfer reaction)',
    'psi-mi:"MI:0701"(dna strand elongation)',
    'psi-mi:"MI:0844"(phosphotransfer reaction)',
    'psi-mi:"MI:1148"(ampylation reaction)',
    'psi-mi:"MI:0566"(sumoylation reaction)',
}

#: Relationship types in IntAct that map to BEL relation 'decreases'
INTACT_DECREASES_ACTIONS = {
    # decreases
    'psi-mi:"MI:0902"(rna cleavage)',
    'psi-mi:"MI:0572"(dna cleavage)',
    'psi-mi:"MI:0199"(deformylation reaction)',
    'psi-mi:"MI:2280"(deamidation reaction)',
    'psi-mi:"MI:0203"(dephosphorylation reaction)',
    'psi-mi:"MI:0212"(lipoprotein cleavage reaction)',
    'psi-mi:"MI:0570"(protein cleavage)',
    'psi-mi:"MI:0204"(deubiquitination reaction)',
    'psi-mi:"MI:0871"(demethylation reaction)',
    'psi-mi:"MI:0985"(deamination reaction)',
    'psi-mi:"MI:1355"(lipid cleavage)',
    'psi-mi:"MI:0569"(deneddylation reaction)',
    'psi-mi:"MI:1140"(decarboxylation reaction)',
    'psi-mi:"MI:0194"(cleavage reaction)',
    'psi-mi:"MI:0197"(deacetylation reaction)',
}

#: Relationship types in IntAct that map to BEL relation 'association'
INTACT_ASSOCIATION_ACTIONS = {
    'psi-mi:"MI:1127"(putative self interaction)',
    'psi-mi:"MI:0914"(association)',
    'psi-mi:"MI:1126"(self interaction)',
    'psi-mi:"MI:0915"(physical association)',
    'psi-mi:"MI:0414"(enzymatic reaction)',
    'psi-mi:"MI:0403"(colocalization)',
}

#: Relationship types in IntAct that map to BEL relation 'regulates'
INTACT_REGULATES_ACTIONS = {
    'psi-mi:"MI:0407"(direct interaction)',
}

#: Relationship types in IntAct that map to BEL relation 'hasComponent'
INTACT_BINDS_ACTIONS = {
    'psi-mi:"MI:0195"(covalent binding)',
    'psi-mi:"MI:0408"(disulfide bond)',
}

PROTEIN_INCREASES_MOD_DICT = {
    'phosphotransfer reaction': 'Ph',
    'glycosylation reaction': 'Glyco',
    'palmitoylation reaction': 'Palm',
    'sulfurtransfer reaction': 'Sulf',
    'psi-mi:"MI:0217"(phosphorylation reaction)': 'Ph',
    'psi-mi:"MI:0566"(sumoylation reaction)': 'Sumo',
    'psi-mi:"MI:0213"(methylation reaction)': 'Me',
    'psi-mi:"MI:0556"(transglutamination reaction)': 'Gln',
    'psi-mi:"MI:0220"(ubiquitination reaction)': 'Ub',
    'psi-mi:"MI:0192"(acetylation reaction)': 'Ac',
    'psi-mi:"MI:0557"(adp ribosylation reaction)': 'ADPRib',
    'psi-mi:"MI:0567"(neddylation reaction)': 'Nedd',
    'psi-mi:"MI:0210"(hydroxylation reaction)': 'Hy',
}

PROTEIN_DECREASES_MOD_DICT = {
    'deacetylation reaction': 'Ac',
     'psi-mi:"MI:0204"(deubiquitination reaction)': 'Ub',
     'psi-mi:"MI:0203"(dephosphorylation reaction)': 'Ph',
     'psi-mi:"MI:0569"(deneddylation reaction)': 'Nedd',
     'psi-mi:"MI:0871"(demethylation reaction)': 'Me',
}

INTACT_OMIT_INTERACTIONS = {
    'psi-mi:"MI:1110"(predicted interaction)',
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


def filter_for_prefix_single(
        list_ids: Iterable[str],
        prefix: str,
        rstrip: str = ' ',
        lstrip: str = ' ',
        separator: str = '|'
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
            final_list.append(f'no {prefix} id')
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
        prefix='pubmed',
    )

    # filter interaction types
    df[RELATION] = filter_for_prefix_single(
        list_ids=df[RELATION],
        rstrip=')',
        lstrip='(',
        separator='"',
        prefix='(',
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


def _add_my_row(graph: BELGraph, row) -> None:  # noqa:C901
    """Add for every pubmed ID an edge with information about relationship type, source and target.

    :param graph: graph to add edges to
    :param row: row with metainformation about source, target, relation, pubmed_id
    :return: None
    """

    # map double spaces to single spaces in relation string
    relation = ' '.join(row[RELATION].split())

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
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification('Red'),
                )

                graph.add_increases(
                    source,
                    target_mod,
                    citation=pubmed_id,
                    evidence=EVIDENCE,
                    subject_modifier=pybel.dsl.activity(),
                )
                continue
            # isomerase reaction
            elif relation in {'isomerase reaction', 'isomerization  reaction'}:
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(
                        name='isomerase activity',
                        namespace='GO',
                        identifier='0016853',
                    ),
                )

                graph.add_increases(
                    source,
                    target_mod,
                    citation=pubmed_id,
                    evidence=EVIDENCE,
                    subject_modifier=pybel.dsl.activity(),
                )
                continue
            # proline isomerase reaction
            elif relation == 'proline isomerization  reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(
                        name='protein peptidyl-prolyl isomerization',
                        namespace='GO',
                        identifier='0000413',
                    ),
                )

                graph.add_increases(
                    source,
                    target_mod,
                    citation=pubmed_id,
                    evidence=EVIDENCE,
                    subject_modifier=pybel.dsl.activity(),
                )
                continue
            # protein amidation
            elif relation == 'amidation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(
                        name='protein amidation',
                        namespace='GO',
                        identifier='0018032',
                    ),
                )
            # ampylation reaction
            elif relation == 'ampylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(
                        name='protein adenylylation',
                        namespace='GO',
                        identifier='0018117',
                    ),
                )
            # myristoylation reaction
            elif relation == 'myristoylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(
                        name='protein myristoylation',
                        namespace='GO',
                        identifier='0018377',
                    ),
                )
            # lipid addition
            elif relation == 'lipid addition':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(
                        name='lipid binding',
                        namespace='GO',
                        identifier='0008289',
                    ),
                )
                graph.add_increases(
                    source,
                    target_mod,
                    citation=pubmed_id,
                    evidence=EVIDENCE,
                    subject_modifier=pybel.dsl.activity(),
                )
                continue
            # aminoacylation reaction (tRNA-ligase activity)
            elif relation == 'aminoacylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(
                        name='tRNA aminoacylation',
                        namespace='GO',
                        identifier='0043039',
                    ),
                )

                graph.add_increases(
                    source,
                    target_mod,
                    citation=pubmed_id,
                    evidence=EVIDENCE,
                    object_modifier=pybel.dsl.activity(),
                )
                continue
            # 'gtpase reaction'
            elif relation == 'gtpase reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(
                        name='GTPase activity',
                        namespace='GO',
                        identifier='0003924',
                    ),
                )

                graph.add_increases(
                    source,
                    target_mod,
                    citation=pubmed_id,
                    evidence=EVIDENCE,
                    object_modifier=pybel.dsl.activity(),
                )
                continue
            # 'atpase reaction'
            elif relation == 'atpase reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(
                        name='ATPase activity',
                        namespace='GO',
                        identifier='0016887',
                    ),
                )

                graph.add_increases(
                    source,
                    target_mod,
                    citation=pubmed_id,
                    evidence=EVIDENCE,
                    object_modifier=pybel.dsl.activity(),
                )
                continue
            # dna strand elongation
            elif relation == 'dna strand elongation':
                target_mod = pybel.dsl.GeneModification(
                    name='DNA strand elongation',
                    namespace='GO',
                    identifier='0022616',
                )
                graph.add_increases(
                    source,
                    target_mod,
                    citation=pubmed_id,
                    evidence=EVIDENCE,
                    object_modifier=pybel.dsl.activity(),
                )
                continue
            # take mapping from relation to abbreviation of reaction
            # protein modification
            elif relation in PROTEIN_INCREASES_MOD_DICT:
                abbreviation = PROTEIN_INCREASES_MOD_DICT[relation]
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(abbreviation),
                )

                graph.add_increases(
                    source,
                    target_mod,
                    citation=pubmed_id,
                    evidence=EVIDENCE,
                )
                continue
            else:
                raise ValueError(f"The relation {relation} is not in INCREASE relations.")

        # DECREASES
        elif relation in INTACT_DECREASES_ACTIONS:

            #: dna cleavage: Covalent bond breakage of a DNA molecule leading to the formation of smaller fragments
            if relation == 'dna cleavage':
                target_mod = pybel.dsl.Gene(
                    namespace='uniprot',
                    identifier=source_uniprot_id,
                    name=get_mnemonic(source_uniprot_id),
                )
            #: rna cleavage: Any process by which an RNA molecule is cleaved at specific sites or in a regulated manner
            elif relation == 'rna cleavage':
                target_mod = pybel.dsl.Rna(
                    namespace='uniprot',
                    identifier=source_uniprot_id,
                    name=get_mnemonic(source_uniprot_id),
                )

            # cleavage
            elif relation in {
                #: Covalent bond breakage in a molecule leading to the formation of smaller molecules
                'cleavage reaction',
                #: Covalent modification of a polypeptide occuring during its maturation or its proteolytic degradation
                'protein cleavage',
            }:
                graph.add_decreases(
                    source,
                    target,
                    citation=pubmed_id,
                    evidence=EVIDENCE,
                )
                continue

            #: Reaction monitoring the cleavage (hydrolysis) or a lipid molecule
            elif relation == 'lipid cleavage':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(
                        name='lipid catabolic process',
                        namespace='GO',
                        identifier='0016042',
                    ),
                )

                graph.add_decreases(
                    source,
                    target_mod,
                    citation=pubmed_id,
                    evidence=EVIDENCE,
                    object_modifier=pybel.dsl.activity(),
                )

            #: 'lipoprotein cleavage reaction': Cleavage of a lipid group covalently bound to a protein residue
            elif relation == 'lipoprotein cleavage reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(
                        name='lipoprotein modification',
                        namespace='GO',
                        identifier='0042160',
                    ),
                )
                graph.add_decreases(
                    source,
                    target_mod,
                    citation=pubmed_id,
                    evidence=EVIDENCE,
                    object_modifier=pybel.dsl.activity(),
                )
                continue

            # deformylation reaction
            elif relation == 'deformylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(
                        name='protein formylation',
                        namespace='GO',
                        identifier='0018256',
                    ),
                )
            # protein deamidation
            elif relation == 'deamidation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(
                        name='protein amidation',
                        namespace='GO',
                        identifier='0018032',
                    ),
                )
                graph.add_decreases(
                    source,
                    target_mod,
                    citation=pubmed_id,
                    evidence=EVIDENCE,
                    object_modifier=pybel.dsl.activity(),
                )
                continue
            # protein decarboxylation
            elif relation == 'decarboxylation reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(
                        name='protein carboxylation',
                        namespace='GO',
                        identifier='0018214',
                    ),
                )

            # protein deamination
            elif relation == 'deamination reaction':
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(
                        name='amino acid binding',
                        namespace='GO',
                        identifier='0016597',
                    ),
                )
            # protein modification
            elif relation in PROTEIN_DECREASES_MOD_DICT.keys():
                abbreviation = PROTEIN_DECREASES_MOD_DICT[relation]
                target_mod = target.with_variants(
                    pybel.dsl.ProteinModification(abbreviation),
                )
            else:
                raise ValueError(f"The relation {relation} is not in DECREASE relations.")

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

        # REGULATES:
        elif relation in INTACT_REGULATES_ACTIONS:

            graph.add_regulates(
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

        # reactions to omit
        elif relation in INTACT_OMIT_INTERACTIONS:
            continue

        # no specified relation
        else:
            raise ValueError(
                f"The relation {relation} between {source} and {target} is not in the specified relations.")


def generate_psi_mi():
    df = _get_my_df()
    interaction_types = set(df['Interaction type(s)'])
    detection_methods = set(df['Interaction detection method(s)'])

    for s in [
        PROTEIN_DECREASES_MOD_DICT,
        PROTEIN_INCREASES_MOD_DICT
    ]:
        for interaction, abbreviation in s.items():
            for psi_interaction in interaction_types:
                if interaction in psi_interaction:
                    if psi_interaction[psi_interaction.find(interaction) - 1] == '(':
                        s[psi_interaction] = s.pop(interaction)
        yield s


if __name__ == '__main__':
    # get_bel().summarize()
    print(list(generate_psi_mi()))
    #df = _get_my_df()
    #print(df.loc[436001, :])
