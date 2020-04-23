# -*- coding: utf-8 -*-

"""This script downloads and parses IntAct data and maps the interaction types to BEL.

Run with ``python -m bio2bel.sources.intact``

IntAct is a interaction database with information about interacting proteins, their relation and the experiment by which
this interaction was found. Among the interactions that are documented in IntAct are protein modifications, associations,
direct interactions, binding interactions and cleavage reactions.
These interactions were grouped according to their biological interpretation and mapped to the corresponding BEL relation.
The interactions in IntAct had a higher granularity than the interactions in BioGRID. Especially with respect to the
protein modifications, exact terms specified the relations between the proteins here. Although many protein modifications
hat corresponding terms in BEL, there were some interaction types in IntAct that could not be mapped directly. Therefore,
other vocabularies like the Gene Ontology (GO) or the Molecular Process Ontology (MOP) were used to find corresponding
interaction terms. These terms were then annotated with the name, namespace and identifier. For negative protein
modifications in which a group is split from the protein like ´decarboxylation reaction´, the positive term ´carboxylation´
is taken and a interaction describing the decrease of the target is taken.
In the case of GTPase reaction and ATPase reaction, the notion of the source protein taking on the ability to catalyze
a GTP or ATP hydrolysis had to  be mentioned. Therefore, pybel.dsl.activity() was added as the subject_modifier of the
source protein.
A very special case was that of the DNA strand elongation. Here, the target was a gene and to capture the notion of the
DNA strand elogation process, the corresponding GO term was added as a ´GeneModification´. In the case of DNA or RNA
cleavage, the target was set as the entity of ´pybel.dsl.Gene´or ´pybel.dsl.Rna´.
For the relation ´isomerase reaction´ there was no corresponding term in BEL denoting this process. Therefore,
the molecular process ´isomerization´ from the MOP was used and annotated.

As IntAct and BioGRID are both interaction databases, the general code from biogrid.py could be taken as an inital
approach. Due to the higher granularity of IntACt concerning the interaction types, many modifications and special
cases as mentioned above had to be further investigated and were applied case-sensitive.

Moreover, a very interesting type of information in IntAct is the negative interaction data which means that a target
would not be activated by the source. This type of relations could also be mapped to negative BEL.

Complexes are also used in IntAct and documented with an internal IntAct ID. These complexes were not taken into
account in this script here.


# TODO: entity types/identifiers that were not normalized to uniprot

#TODO: summary
"""

import logging
from collections import Counter
from typing import Mapping, Optional, Tuple
from zipfile import ZipFile

import pandas as pd
import pyobo.xrefdb.sources.intact
from protmapper.uniprot_client import get_mnemonic
from tqdm import tqdm

import pybel.dsl
from bio2bel.utils import ensure_path
from pybel import BELGraph
from pybel.dsl import GeneModification, ProteinModification

logger = logging.getLogger(__name__)

COLUMNS = [
    '#ID(s) interactor A',
    'ID(s) interactor B',
    'Interaction type(s)',
    'Publication Identifier(s)',
    'Interaction detection method(s)',
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

SUBJECT_ACTIVITIES = {

    'psi-mi:"MI:0883"(gtpase reaction)': pybel.dsl.activity(
        name='GTPase activity',
        namespace='GO',
        identifier='0003924',
    ),
    'psi-mi:"MI:0882"(atpase reaction)': pybel.dsl.activity(
        name='ATPase activity',
        namespace='GO',
        identifier='0016887',
    ),
}

PROTEIN_INCREASES_MOD_DICT: Mapping[str, ProteinModification] = {
    'psi-mi:"MI:0844"(phosphotransfer reaction)': ProteinModification('Ph'),
    'psi-mi:"MI:0559"(glycosylation reaction)': ProteinModification('Glyco'),
    'psi-mi:"MI:0216"(palmitoylation reaction)': ProteinModification('Palm'),
    'psi-mi:"MI:1327"(sulfurtransfer reaction)': ProteinModification('Sulf'),
    'psi-mi:"MI:0217"(phosphorylation reaction)': ProteinModification('Ph'),
    'psi-mi:"MI:0566"(sumoylation reaction)': ProteinModification('Sumo'),
    'psi-mi:"MI:0213"(methylation reaction)': ProteinModification('Me'),
    'psi-mi:"MI:0556"(transglutamination reaction)': ProteinModification('Gln'),
    'psi-mi:"MI:0220"(ubiquitination reaction)': ProteinModification('Ub'),
    'psi-mi:"MI:0192"(acetylation reaction)': ProteinModification('Ac'),
    'psi-mi:"MI:0557"(adp ribosylation reaction)': ProteinModification('ADPRib'),
    'psi-mi:"MI:0567"(neddylation reaction)': ProteinModification('Nedd'),
    'psi-mi:"MI:0210"(hydroxylation reaction)': ProteinModification('Hy'),
    'psi-mi:"MI:0945"(oxidoreductase activity electron transfer reaction)': ProteinModification('Red'),


    'psi-mi:"MI:1250"(isomerase reaction)': ProteinModification(
        name='isomerization',
        namespace='MOP',
        identifier='0000789',
    ),

    'psi-mi:"MI:1237"(proline isomerization reaction)': ProteinModification(
        name='protein peptidyl-prolyl isomerization',
        namespace='GO',
        identifier='0000413',
    ),
    'psi-mi:"MI:0193"(amidation reaction)': ProteinModification(
        name='protein amidation',
        namespace='GO',
        identifier='0018032',
    ),
    'psi-mi:"MI:1148"(ampylation reaction)': ProteinModification(
        name='protein adenylylation',
        namespace='GO',
        identifier='0018117',
    ),
    'psi-mi:"MI:0214"(myristoylation reaction)': ProteinModification(
        name='protein myristoylation',
        namespace='GO',
        identifier='0018377',
    ),

    'psi-mi:"MI:0211"(lipid addition)': ProteinModification(
        name='protein lipidation',
        namespace='GO',
        identifier='0006497',
    ),
    'psi-mi:"MI:1143"(aminoacylation reaction)': ProteinModification(
        name='tRNA aminoacylation',
        namespace='GO',
        identifier='0043039',
    ),

    'psi-mi:"MI:0883"(gtpase reaction)': ProteinModification(
        name='GTPase activity',
        namespace='GO',
        identifier='0003924',
    ),

    'psi-mi:"MI:0882"(atpase reaction)': ProteinModification(
        name='ATPase activity',
        namespace='GO',
        identifier='0016887',
    ),

}

PROTEIN_DECREASES_MOD_DICT: Mapping[str, ProteinModification] = {
    'psi-mi:"MI:0197"(deacetylation reaction)': ProteinModification('Ac'),
    'psi-mi:"MI:0204"(deubiquitination reaction)': ProteinModification('Ub'),
    'psi-mi:"MI:0203"(dephosphorylation reaction)': ProteinModification('Ph'),
    'psi-mi:"MI:0569"(deneddylation reaction)': ProteinModification('Nedd'),
    'psi-mi:"MI:0871"(demethylation reaction)': ProteinModification('Me'),
}

INTACT_OMIT_INTERACTIONS = {
    'psi-mi:"MI:1110"(predicted interaction)',
}

EVIDENCE = 'From IntAct'

MODULE_NAME = 'intact'
VERSION = '2020-03-31'
URL = f'ftp://ftp.ebi.ac.uk/pub/databases/intact/{VERSION}/psimitab/intact.zip'

UNIPROTKB = 'uniprotkb'


def _process_pmid(s: str = '|', prefix: str = 'pubmed:') -> str:
    """Filter for pubmed ids.

    :param s: string to be filtered for pubmed ids
    :return: PubMed id
    """
    for identifier in s.split(s):
        identifier = identifier.strip()
        if identifier.startswith(prefix):
            return identifier


def _process_score(s: str = '|', prefix: str = 'intact-miscore:') -> str or None:
    """Filter for pubmed ids.

    :param s: string to be filtered for pubmed ids
    :return: PubMed id
    """
    flag = False
    if s:
        for identifier in s.split(s):
            identifier = identifier.strip()
            if identifier.startswith(prefix):
                flag = True
                return identifier
    if not flag:
            return None


intact_complexportal_mapping = pyobo.xrefdb.sources.intact.get_complexportal_mapping()
intact_reactome_mapping = pyobo.xrefdb.sources.intact.get_reactome_mapping()

_unhandled = Counter()


def _process_interactor(s: str) -> Optional[Tuple[str, str]]:
    if s.startswith('uniprotkb:'):
        return 'uniprot', s[len('uniprotkb:'):]
    if s.startswith('chebi:"CHEBI:'):
        return 'chebi', s[len('chebi:"CHEBI:'):-1]
    if s.startswith('intact:'):
        prefix, identifier = 'intact', s[len('intact:'):]

        if identifier in intact_complexportal_mapping:
            return 'complexportal', intact_complexportal_mapping[identifier]
        elif identifier in intact_reactome_mapping:
            return 'reactome', intact_reactome_mapping[identifier]
        else:
            _unhandled[prefix] += 1
            logger.warning('could not find complexportal/reactome mapping for %s:%s', prefix, identifier)
            return

    """
    Counter({'chebi': 9534,
         'ensembl': 3156,
         'refseq': 444,
         'ensemblgenomes': 439,
         'ddbj/embl/genbank': 204,
         'wwpdb': 163,
         'matrixdb': 102,
         'reactome': 87,
         'intenz': 43,
         'signor': 15,
         'chembl target': 11,
         'dip': 4,
         'entrezgene/locuslink': 2,
         'protein ontology': 2,
         'emdb': 2})
    """
    _unhandled[s.split(':')[0]] += 1
    logger.warning('unhandled identifier: %s', s)
    return


def get_processed_intact_df() -> pd.DataFrame:
    """Load, filter and rename intact dataframe."""
    path = ensure_path(prefix=MODULE_NAME, url=URL)
    logger.info('reading IntAct from %s', path)
    with ZipFile(path) as zip_file:
        with zip_file.open('intact.txt') as file:
            df = pd.read_csv(file, sep='\t', usecols=COLUMNS, na_values={'-'})

    df.dropna(inplace=True)

    # Omit certain interaction types
    df = df[~df['Interaction type(s)'].isin(INTACT_OMIT_INTERACTIONS)]

    df['#ID(s) interactor A'] = df['#ID(s) interactor A'].map(_process_interactor)
    df['ID(s) interactor B'] = df['ID(s) interactor B'].map(_process_interactor)

    # filter for pubmed
    logger.info('mapping provenance')
    df['Publication Identifier(s)'] = df['Publication Identifier(s)'].map(_process_pmid)

    # filter for intact-miscore
    df['Confidence value(s)'] = df['Publication Identifier(s)'].map(_process_score)

    return df


def get_bel() -> BELGraph:
    """Get BEL graph."""
    df = get_processed_intact_df()
    graph = BELGraph(name=MODULE_NAME, version=VERSION)
    it = tqdm(df[COLUMNS].values, total=len(df.index), desc=f'mapping {MODULE_NAME}', unit_scale=True)
    for source_uniprot_id, target_uniprot_id, relation, pubmed_id, detection_method, source_db, confidence in it:
        if pd.isna(source_uniprot_id) or pd.isna(target_uniprot_id):
            continue

        _add_my_row(
            graph,
            relation=relation,
            source_uniprot_id=source_uniprot_id,
            target_uniprot_id=target_uniprot_id,
            pubmed_id=pubmed_id,
            int_detection_method=detection_method,
            source_database=source_db,
            confidence=confidence,
        )
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
    if pubmed_id is None:
        return
    print(confidence)
    annotations = {
        'psi-mi': relation,
        'intact-detection': int_detection_method,
        'intact-source': source_database,
        'intact-confidence': confidence,
    }
    # map double spaces to single spaces in relation string
    relation = ' '.join(relation.split())  # FIXME how often does this happen? can you tweet Intact with the number?
    # I only found it in 'psi-mi:"MI:1237"(proline isomerization reaction)', nowhere else
    source = pybel.dsl.Protein(
        namespace='uniprot',
        identifier=source_uniprot_id[1],
        name=get_mnemonic(source_uniprot_id[1]),
    )
    target = pybel.dsl.Protein(
        namespace='uniprot',
        identifier=target_uniprot_id[1],
        name=get_mnemonic(target_uniprot_id[1]),
    )

    if relation in PROTEIN_INCREASES_MOD_DICT:
        graph.add_increases(
            source,
            target.with_variants(PROTEIN_INCREASES_MOD_DICT[relation]),
            citation=pubmed_id,
            evidence=EVIDENCE,
            annotations=annotations.copy(),
            subject_modifier=SUBJECT_ACTIVITIES.get(relation),
        )

    # dna strand elongation
    elif relation == 'psi-mi:"MI:0701"(dna strand elongation)':
        target_mod = pybel.dsl.Gene(
            namespace='uniprot',
            identifier=target_uniprot_id,
            name=get_mnemonic(target_uniprot_id),
            variants=[
                GeneModification(
                    name='DNA strand elongation',
                    namespace='GO',
                    identifier='0022616',
                ),
            ],
        )
        graph.add_increases(
            source,
            target_mod,
            citation=pubmed_id,
            evidence=EVIDENCE,
            annotations=annotations.copy(),
        )

    # DECREASES
    elif relation in INTACT_DECREASES_ACTIONS:
        #: dna cleavage: Covalent bond breakage of a DNA molecule leading to the formation of smaller fragments
        if relation == 'psi-mi:"MI:0572"(dna cleavage)':
            target_mod = pybel.dsl.Gene(
                namespace='uniprot',
                identifier=source_uniprot_id,
                name=get_mnemonic(source_uniprot_id),
            )
            graph.add_decreases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence=EVIDENCE,
                annotations=annotations.copy(),
            )
        #: rna cleavage: Any process by which an RNA molecule is cleaved at specific sites or in a regulated manner
        elif relation == 'psi-mi:"MI:0902"(rna cleavage)':
            target_mod = pybel.dsl.Rna(
                namespace='uniprot',
                identifier=source_uniprot_id,
                name=get_mnemonic(source_uniprot_id),
            )
            graph.add_decreases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence=EVIDENCE,
                annotations=annotations.copy(),
            )

        # cleavage
        elif relation in {
            #: Covalent bond breakage in a molecule leading to the formation of smaller molecules
            'psi-mi:"MI:0194"(cleavage reaction)',
            #: Covalent modification of a polypeptide occuring during its maturation or its proteolytic degradation
            'psi-mi:"MI:0570"(protein cleavage)',
        }:
            graph.add_decreases(
                source,
                target,
                citation=pubmed_id,
                evidence=EVIDENCE,
                annotations=annotations.copy(),
            )

        #: Reaction monitoring the cleavage (hydrolysis) or a lipid molecule
        elif relation == 'psi-mi:"MI:1355"(lipid cleavage)':
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
        elif relation == 'psi-mi:"MI:0212"(lipoprotein cleavage reaction)':
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

        # deformylation reaction
        elif relation == 'psi-mi:"MI:0199"(deformylation reaction)':
            target_mod = target.with_variants(
                pybel.dsl.ProteinModification(
                    name='protein formylation',
                    namespace='GO',
                    identifier='0018256',
                ),
            )
            graph.add_decreases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence=EVIDENCE,
                annotations=annotations.copy(),
            )
        # protein deamidation
        elif relation == 'psi-mi:"MI:2280"(deamidation reaction)':
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

        # protein decarboxylation
        elif relation == 'psi-mi:"MI:1140"(decarboxylation reaction)':
            target_mod = target.with_variants(
                pybel.dsl.ProteinModification(
                    name='protein carboxylation',
                    namespace='GO',
                    identifier='0018214',
                ),
            )
            graph.add_decreases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence=EVIDENCE,
                annotations=annotations.copy(),
            )
        # protein deamination:
        elif relation == 'psi-mi:"MI:0985"(deamination reaction)':
            target_mod = target.with_variants(
                pybel.dsl.ProteinModification(
                    name='amine binding',
                    namespace='GO',
                    identifier='0043176',
                ),
            )
            graph.add_decreases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence=EVIDENCE,
                annotations=annotations.copy(),
            )
        # protein modification
        elif relation in PROTEIN_DECREASES_MOD_DICT:
            target_mod = target.with_variants(PROTEIN_DECREASES_MOD_DICT[relation])
            graph.add_decreases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence=EVIDENCE,
                annotations=annotations.copy(),
            )
        else:
            raise ValueError(f"The relation {relation} is not in DECREASE relations.")

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

    # no specified relation
    else:
        raise ValueError(f"Unspecified relation {relation} between {source} and {target}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    _graph = get_bel()
    _graph.summarize()
    import os

    pybel.dump(_graph, os.path.expanduser('~/Desktop/intact.bel.nodelink.json'))

