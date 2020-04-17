# -*- coding: utf-8 -*-

"""This script downloads and parses IntAct data and maps the interaction types to BEL."""

import logging
from zipfile import ZipFile

import pandas as pd
import pybel.dsl
from protmapper.uniprot_client import get_mnemonic
from pybel import BELGraph
from tqdm import tqdm

from bio2bel.utils import ensure_path

logger = logging.getLogger(__name__)

COLUMNS = [
    '#ID(s) interactor A',
    'ID(s) interactor B',
    'Interaction detection method(s)',
    'Interaction type(s)',
    'Source database(s)',
    'Confidence value(s)',
]

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

UNIPROTKB = 'uniprotkb'


def _process_pmid(s: str) -> str:
    """Filter for pubmed ids."""
    for id in s.split('|'):
        id = id.strip()
    if id.startswith('pubmed:'):
        return id


def get_processed_intact_df() -> pd.DataFrame:
    """Load, filter and rename intact dataframe.

    :return: processed dataframe
    """
    path = ensure_path(prefix=MODULE_NAME, url=URL)
    logger.info('reading IntAct from %s', path)
    with ZipFile(path) as zip_file:
        with zip_file.open('intact.txt') as file:
            df = pd.read_csv(file, sep='\t')

    # take relevant columns for source, target, relation and PubMed ID
    df = df[COLUMNS]

    # drop nan value rows for interactor B
    df = df[df['ID(s) interactor B'] != '-']

    # filter for uniprot ids
    df = df[df[SOURCE].str.contains("uniprot")]

    # filter for pubmed
    logger.info('mapping provenance')
    df['Publication Identifiers'] = df['Publication Identifiers'].map(_process_pmid)

    return df


def get_bel() -> BELGraph:
    """Get BEL graph.

    :return: BEL graph
    """
    df = get_processed_intact_df()
    graph = BELGraph(name=MODULE_NAME, version=VERSION)
    for _, row in tqdm(df.iterrows(), total=len(df.index), desc=f'mapping {MODULE_NAME}'):
        _add_my_row(graph, row)
    return graph


def _add_my_row(
        graph: BELGraph,
        relation: str,
        source_uniprot_id: str,
        target_uniprot_id: str,
        pubmed_id: str,
        int_detection_method: str,
        source_database: str,
        confidence: str,
) -> None:  # noqa:C901
    """Add for every pubmed ID an edge with information about relationship type, source and target.

    :param graph: graph to add edges to
    :param relation: row value of column relation
    :param source_uniprot_id: row value of column source
    :param target_uniprot_id: row value of column target
    :param pubmed_id: row value of column pubmed_id
    :param int_detection_method: row value of column interaction detection method
    :param confidence: row value of confidence score column
    :return: None
    """
    annotations = {
        'psi-mi': relation,
        'intact-detection': int_detection_method,
        'intact-source': source_database,
        'intact-confidence': confidence,
    }
    # map double spaces to single spaces in relation string
    relation = ' '.join(relation.split())

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
                annotations=annotations.copy(),
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
                annotations=annotations.copy(),
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
                annotations=annotations.copy(),
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
                annotations=annotations.copy(),
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
                annotations=annotations.copy(),
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
                annotations=annotations.copy(),
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
                annotations=annotations.copy(),
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
                annotations=annotations.copy(),
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
                annotations=annotations.copy(),
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
                annotations=annotations.copy(),
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
                annotations=annotations.copy(),
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
                annotations=annotations.copy(),
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
                annotations=annotations.copy(),
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
            annotations=annotations.copy(),
        )

    # ASSOCIATION:
    elif relation in INTACT_ASSOCIATION_ACTIONS:

        graph.add_association(
            source,
            target,
            citation=pubmed_id,
            evidence=EVIDENCE,
            annotations=annotations.copy(),
        )

    # REGULATES:
    elif relation in INTACT_REGULATES_ACTIONS:

        graph.add_regulates(
            source,
            target,
            citation=pubmed_id,
            evidence=EVIDENCE,
            annotations=annotations.copy(),
        )

    # BINDS
    elif relation in INTACT_BINDS_ACTIONS:

        graph.add_binds(
            source,
            target,
            citation=pubmed_id,
            evidence=EVIDENCE,
            annotations=annotations.copy(),
        )

    # reactions to omit
    elif relation in INTACT_OMIT_INTERACTIONS:
        continue

    # no specified relation
    else:
        raise ValueError(
            f"The relation {relation} between {source} and {target} is not in the specified relations.")


if __name__ == '__main__':
    # get_bel().summarize()
