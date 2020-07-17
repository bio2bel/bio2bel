# -*- coding: utf-8 -*-

"""Download and convert IntAct to BEL.

Run with ``python -m bio2bel.sources.intact``

`IntAct <https://www.ebi.ac.uk/intact/>`_ is a interaction database with information about interacting proteins,
their relation, and the experiments, in which these interactions were found.
Among the interactions that are documented in IntAct are protein modifications, associations, direct interactions,
binding interactions and cleavage reactions.
These interactions were grouped according to their biological interpretation and mapped to the corresponding BEL
relation. The interactions in IntAct had a higher granularity than the interactions in BioGRID.

Due to the default BEL
namespace of protein modifications :data:`pybel.language.pmod_namespace`, the post-translational protein modification
can be identified very accurately. For example, the glycosylation of a protein can be described in BEL by
:code:`pybel.dsl.ProteinModification('Glyco')`.  Although many protein modifications had corresponding terms in BEL,
there were some interaction types in IntAct that could not be mapped directly, like `gtpase reaction <https://www.ebi.ac.uk/ols/ontologies/mi/terms?iri=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FMI_0883>`_
or `aminoacylation reaction <https://www.ebi.ac.uk/ols/ontologies/mi/terms?iri=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FMI_1143>`_.


Therefore, other vocabularies like the `Gene Ontology (GO) <https://www.ebi.ac.uk/QuickGO/>`_ or the
`Molecular Process Ontology (MOP) <https://www.ebi.ac.uk/ols/ontologies/mop>`_ were used to find corresponding
interaction terms. These terms were then annotated with the name, namespace and identifier.
IntAct uses the `PSI-MI <https://psicquic.github.io/MITAB25Format.html>`_
(Proteomics Standards Initiative - Molecular Interactions Controlled Vocabulary) format to identify interaction types
The following tables shows examples of how the interactions from IntAct were mapped to BEL or other ontologies.

+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Source Type | Target Type | Interaction Type                                                     | BEL Example                                                 |
+=============+=============+======================================================================+=============================================================+
| Protein     | Protein     | psi-mi:"MI:0193"(amidation reaction)                                 | p('uniprot', 'P62865') increases p('uniprot', 'P10731')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:1327"(sulfurtransfer reaction)                            | p('uniprot', 'Q46925') increases p('uniprot', 'P0AGF2')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0945"(oxidoreductase activity electron transfer reaction) | p('uniprot', 'P0A3E0') increases p('uniprot', 'P21890')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0217"(phosphorylation reaction)                           | p('uniprot', 'P53999') increases p('uniprot', 'P68400')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0567"(neddylation reaction)                               | p('uniprot', 'Q86XK2') increases p('uniprot', 'Q15843')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:1148"(ampylation reaction)                                | p('uniprot', 'P60953-2') increases p('uniprot', 'Q9BVA6')   |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0883"(gtpase reaction)                                    | p('chebi', '15996') increases p('uniprot', 'Q9HCN4')        |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0557"(adp ribosylation reaction)                          | p('uniprot', 'P09874') increases p('uniprot', 'P13010')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0211"(lipid addition)                                     | p('chebi', '15532') increases p('uniprot', 'Q9BR61')        |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0192"(acetylation reaction)                               | p('uniprot', 'O15350') increases p('uniprot', 'Q09472')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0844"(phosphotransfer reaction)                           | p('chebi', '15422') increases p('uniprot', 'O13297')        |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0220"(ubiquitination reaction)                            | p('uniprot', 'P32121') increases p('uniprot', 'Q00987')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0213"(methylation reaction)                               | p('uniprot', 'O60016') increases p('uniprot', 'P09988')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0214"(myristoylation reaction)                            | p('chebi', '15532') increases p('uniprot', 'Q9BR61')        |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0216"(palmitoylation reaction)                            | p('uniprot', 'P60880') increases p('uniprot', 'Q8IUH5')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Gene        | psi-mi:"MI:0701"(dna strand elongation)                              | p('uniprot', 'Q9NYJ8') increases g('uniprot', 'Q62073')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:1250"(isomerase reaction)                                 | p('uniprot', 'Q13526') increases p('uniprot', 'Q3UVX5')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0559"(glycosylation reaction)                             | p('uniprot', 'P18177') increases p('uniprot', 'P63000')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0566"(sumoylation reaction)                               | p('uniprot', 'P56693') increases p('uniprot', 'P63165')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0882"(atpase reaction)                                    | p('chebi', '15422') increases p('uniprot', 'Q9ZNT0')        |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:1146"(phospholipase reaction)                             | p('chebi', '40265') increases p('uniprot', 'P30041')        |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0556"(transglutamination reaction)                        | p('uniprot', 'P40337') increases p('uniprot', 'P21980')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:1143"(aminoacylation reaction)                            | p('uniprot', 'Q89VT6') increases p('uniprot', 'Q89VT8')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0210"(hydroxylation reaction)                             | p('uniprot', 'Q16665') increases p('uniprot', 'Q96KS0')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:1355"(lipid cleavage)                                     | p('chebi', '64583') decreases p('uniprot', 'F1N588')        |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0212"(lipoprotein cleavage reaction)                      | p('uniprot', 'P10515') decreases p('uniprot', 'Q9Y6E7')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:2280"(deamidation reaction)                               | p('uniprot', 'Q86YW7') decreases p('uniprot', 'P21163')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0204"(deubiquitination reaction)                          | p('uniprot', 'Q93009') decreases p('uniprot', 'P04637')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0569"(deneddylation reaction)                             | p('uniprot', 'Q96LD8') decreases p('uniprot', 'P62913')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0985"(deamination reaction)                               | p('uniprot', 'Q8VSD5') decreases p('uniprot', 'P61088')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0871"(demethylation reaction)                             | p('uniprot', 'P68432') decreases p('uniprot', 'P41229')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0570"(protein cleavage)                                   | p('uniprot', 'P04275') decreases p('uniprot', 'Q76LX8')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Gene        | psi-mi:"MI:0572"(dna cleavage)                                       | p('uniprot', 'A4GXA9') decreases g('uniprot', 'Q96NY9')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0197"(deacetylation reaction)                             | p('uniprot', 'Q71U36') decreases p('uniprot', 'Q9UBN7')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0199"(deformylation reaction)                             | p('uniprot', 'Q62962') decreases p('uniprot', 'Q9EP80')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:1140"(decarboxylation reaction)                           | p('chebi', '16810') decreases p('uniprot', 'P9WJA9')        |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Rna         | psi-mi:"MI:0902"(rna cleavage)                                       | p('uniprot', 'Q99714') decreases r('uniprot', 'O15091')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0194"(cleavage reaction)                                  | p('uniprot', 'O14727') decreases p('uniprot', 'P42574')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0203"(dephosphorylation reaction)                         | p('uniprot', 'Q78DX7') decreases p('uniprot', 'P29351')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:1127"(putative self interaction)                          | p('uniprot', 'O64517') association p('uniprot', 'O64517')   |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0915"(physical association)                               | p('uniprot', 'P34708-1') association p('uniprot', 'P34709') |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0914"(association)                                        | p('uniprot', 'P50570') association p('uniprot', 'Q99961')   |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:1126"(self interaction)                                   | p('uniprot', 'P28481') association p('uniprot', 'P28481')   |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0414"(enzymatic reaction)                                 | p('uniprot', 'P15646') association p('uniprot', 'Q02555')   |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0403"(colocalization)                                     | p('uniprot', 'P00519') association p('uniprot', 'Q92558')   |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0407"(direct interaction)                                 | p('uniprot', 'P49418') regulates p('uniprot', 'O43426')     |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0195"(covalent binding)                                   | p('uniprot', 'P0CG48') hasComponent p('uniprot', 'P63146')  |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+
| Protein     | Protein     | psi-mi:"MI:0408"(disulfide bond)                                     | p('uniprot', 'P73728') hasComponent p('uniprot', 'P73728')  |
+-------------+-------------+----------------------------------------------------------------------+-------------------------------------------------------------+

For negative protein modifications in which a group is split from the protein like `decarboxylation reaction
<https://www.ebi.ac.uk/ols/ontologies/mi/terms?iri=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FMI_1140>`_,
the positive term `protein carboxylation <https://www.ebi.ac.uk/QuickGO/term/GO:0018214>`_ is taken and a interaction
describing the decrease of the target is taken.


In the case of `gtpase reaction <https://www.ebi.ac.uk/ols/ontologies/mi/terms?iri=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FMI_0883>`_ and
`atpase reaction <https://www.ebi.ac.uk/ols/ontologies/mi/terms?iri=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FMI_0882>`_,
the notion of the source protein taking on the ability to catalyze a GTP or ATP hydrolysis had to  be mentioned.
Therefore, :func:`pybel.dsl.activity` was added as the subject_modifier of the source protein.
A very special case was that of the `dna strand elongation
<https://www.ebi.ac.uk/ols/ontologies/mi/terms?iri=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FMI_0701>`_.

Here, the target was a gene and to capture the notion of the DNA strand elogation process, the corresponding GO term
was added as a :class:`pybel.dsl.GeneModification`. In the case of DNA or RNA cleavage, the target was set as the entity
of :class:`pybel.dsl.Gene` or :class:`pybel.dsl.Rna`.


For the relation `isomerase reaction
<https://www.ebi.ac.uk/ols/ontologies/mi/terms?iri=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FMI_1250>`_
there was no corresponding term in BEL denoting this process. Therefore, the molecular process `isomerization
<https://www.ebi.ac.uk/ols/ontologies/mop/terms?iri=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FMOP_0000789>`_ from the
`MOP <https://www.ebi.ac.uk/ols/ontologies/mop>`_ was used and annotated.

As IntAct and BioGRID are both interaction databases, the general code from biogrid.py could be taken as an initial
approach. Due to the higher granularity of IntAct concerning the interaction types, many modifications and special
cases as mentioned above had to be further investigated and were applied case-sensitive.

Moreover, a very interesting type of information in IntAct is the negative interaction data which means that a target
would not be activated by the source. A future improvement would be to map this type of relations to negative BEL.
In machine learning tasks like link prediction in graphs these negative edges could be used as negative samples to
enhance the prediction quality of the model.

IntAct also gives internal accession numbers to some complexes, but there are no mappings from IntAct to other
preferred resources like ComplexPortal yet. Therefore, these complexes are not taken into account in this module here.
For further information on this matter please follow the ongoing dicussion on
`Twitter <https://twitter.com/cthoyt/status/1252345260740456453>_`.

Next to IntAct and BioGRID, there are also other data resources that make use of the
`PSI-MI 2.5 format <https://psicquic.github.io/MITAB25Format.html>`_:

- Biomolecular Interaction Network Database (BIND) [bind]_
- `Human Protein Reference Database (HPRD) <http://www.hprd.org>`_ [hprd]_
- `Database of Interacting Proteins (DIP) <http://dip.doe-mbi.ucla.edu>`_ [dip]_

Summary statistics of the BEL graph generated in the IntAct module:

+------------+------------+
| Key        | Value      |
+============+============+
| Version    | v2020-03-31|
+------------+------------+
| Nodes      | 100115     |
+------------+------------+
| Edges      | 1294252    |
+------------+------------+
| Citations  | 20568      |
+------------+------------+
| Components | 3119       |
+------------+------------+
| Density:   | 1.29E-04   |
+------------+------------+

.. [bind] https://academic.oup.com/database/article/doi/10.1093/database/baq037/461120
.. [hprd] https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1347503/
.. [dip] https://www.ncbi.nlm.nih.gov/pmc/articles/PMC102387/
"""

import logging
from collections import Counter
from functools import lru_cache
from typing import Mapping, Optional, Tuple
from zipfile import ZipFile

import pandas as pd
import pyobo
import pyobo.xrefdb.sources.intact
from protmapper.uniprot_client import get_entrez_id, get_mnemonic
from tqdm import tqdm

import pybel.dsl
from pybel import BELGraph
from pybel.dsl import GeneModification, ProteinModification
from ..utils import ensure_path

__all__ = [
    'get_bel',
]

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
    'psi-mi:"MI:1146"(phospholipase reaction)',
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
        namespace='go',
        identifier='0003924',
    ),
    'psi-mi:"MI:0882"(atpase reaction)': pybel.dsl.activity(
        name='ATPase activity',
        namespace='go',
        identifier='0016887',
    ),
    'psi-mi:"MI:1146"(phospholipase reaction)': pybel.dsl.activity(
        name='phospholipase activity',
        namespace='go',
        identifier='0004620',
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
    'psi-mi:"MI:0556"(transglutamination reaction)': ProteinModification(
        namespace='mi', identifier='0556', name='transglutamination reaction',
    ),
    'psi-mi:"MI:0220"(ubiquitination reaction)': ProteinModification('Ub'),
    'psi-mi:"MI:0192"(acetylation reaction)': ProteinModification('Ac'),
    'psi-mi:"MI:0557"(adp ribosylation reaction)': ProteinModification('ADPRib'),
    'psi-mi:"MI:0567"(neddylation reaction)': ProteinModification('Nedd'),
    'psi-mi:"MI:0210"(hydroxylation reaction)': ProteinModification('Hy'),
    'psi-mi:"MI:0945"(oxidoreductase activity electron transfer reaction)': ProteinModification(
        namespace='mi', identifier='0945', name='oxidoreductase activity electron transfer reaction',
    ),
    'psi-mi:"MI:1250"(isomerase reaction)': ProteinModification(
        name='isomerization',
        namespace='mop',
        identifier='0000789',
    ),
    'psi-mi:"MI:1237"(proline isomerization reaction)': ProteinModification(
        name='protein peptidyl-prolyl isomerization',
        namespace='go',
        identifier='0000413',
    ),
    'psi-mi:"MI:0193"(amidation reaction)': ProteinModification(
        name='protein amidation',
        namespace='go',
        identifier='0018032',
    ),
    'psi-mi:"MI:1148"(ampylation reaction)': ProteinModification(
        name='protein adenylylation',
        namespace='go',
        identifier='0018117',
    ),
    'psi-mi:"MI:0214"(myristoylation reaction)': ProteinModification(
        name='protein myristoylation',
        namespace='go',
        identifier='0018377',
    ),
    'psi-mi:"MI:0211"(lipid addition)': ProteinModification(
        name='protein lipidation',
        namespace='go',
        identifier='0006497',
    ),
    'psi-mi:"MI:1143"(aminoacylation reaction)': ProteinModification(
        name='tRNA aminoacylation',
        namespace='go',
        identifier='0043039',
    ),
    'psi-mi:"MI:0883"(gtpase reaction)': ProteinModification(
        name='GTPase activity',
        namespace='go',
        identifier='0003924',
    ),
    'psi-mi:"MI:0882"(atpase reaction)': ProteinModification(
        name='ATPase activity',
        namespace='go',
        identifier='0016887',
    ),
    'psi-mi:"MI:1146"(phospholipase reaction)': ProteinModification(
        name='phospholipase activity',
        namespace='go',
        identifier='0004620',
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
VERSION = '2020-04-30'
URL = f'ftp://ftp.ebi.ac.uk/pub/databases/intact/{VERSION}/psimitab/intact.zip'


def _process_pmid(s: str, sep: str = '|', prefix: str = 'pubmed:') -> str:
    """Filter for PubMed ids.

    :param s: string of PubMed ids
    :param sep: separator between PubMed ids
    :return: PubMed id
    """
    for identifier in s.split(sep):
        identifier = identifier.strip()
        if identifier.startswith(prefix):
            return identifier


def _process_score(s: str, sep: str = '|', prefix: str = 'intact-miscore:') -> str or None:
    """Filter for confidence scores ids.

    :param s: string to split
    :param s: string to be filtered for scores ids
    :return: score
    """
    if not s:
        return None
    for identifier in s.split(sep):
        identifier = identifier.strip()
        if identifier.startswith(prefix):
            return identifier


@lru_cache()
def _get_complexportal_mapping():
    return pyobo.xrefdb.sources.intact.get_complexportal_mapping()


def _map_complexportal(identifier):
    return _get_complexportal_mapping().get(identifier)


@lru_cache()
def _get_reactome_mapping():
    return pyobo.xrefdb.sources.intact.get_reactome_mapping()


def _map_reactome(identifier):
    return _get_reactome_mapping().get(identifier)


_unhandled = Counter()
_logged_unhandled = set()


def _process_interactor(s: str) -> Optional[Tuple[str, str, Optional[str]]]:
    if s.startswith('uniprotkb:'):
        uniprot_id = s[len('uniprotkb:'):]
        try:
            ncbigene_id = get_entrez_id(uniprot_id)
        except Exception:
            ncbigene_id = None
        if ncbigene_id:
            return 'ncbigene', ncbigene_id, pyobo.get_name('ncbigene', ncbigene_id)
        return 'uniprot', uniprot_id, get_mnemonic(uniprot_id)
    if s.startswith('chebi:"CHEBI:'):
        chebi_id = s[len('chebi:"CHEBI:'):-1]
        return 'chebi', chebi_id, pyobo.get_name('chebi', chebi_id)
    if s.startswith('chembl target:'):
        return 'chembl.target', s[len('chembl target:'):-1], None
    if s.startswith('intact:'):
        prefix, identifier = 'intact', s[len('intact:'):]

        complexportal_identifier = _map_complexportal(identifier)
        if complexportal_identifier is not None:
            return 'complexportal', complexportal_identifier, None

        reactome_identifier = _map_reactome(identifier)
        if reactome_identifier is not None:
            return 'reactome', reactome_identifier, None

        _unhandled[prefix] += 1
        logger.debug('could not find complexportal/reactome mapping for %s:%s', prefix, identifier)
        return prefix, identifier, None
    if s.startswith('intenz:'):
        return 'eccode', s[len('intenz:'):], None

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
    if s not in _logged_unhandled:
        logger.warning('unhandled identifier: %s', s)
        _logged_unhandled.add(s)


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

    logger.info('Unmapped terms: %s', _unhandled)

    # remove any rows that weren't mapped by _process_interactor
    df = df[df['#ID(s) interactor A'].notna() & df['ID(s) interactor B'].notna()]

    # filter for PubMed
    logger.info('mapping provenance')
    df['Publication Identifier(s)'] = df['Publication Identifier(s)'].map(_process_pmid)

    # filter for intact-miscore
    df['Confidence value(s)'] = df['Confidence value(s)'].map(_process_score)

    # drop entries from intact with 'EBI-' identifier
    df = df[~df['#ID(s) interactor A'].astype(str).str.contains('EBI-')]
    df = df[~df['ID(s) interactor B'].astype(str).str.contains('EBI-')]

    return df


def get_bel() -> BELGraph:
    """Get BEL graph."""
    df = get_processed_intact_df()
    graph = BELGraph(name='IntAct', version=VERSION)
    it = tqdm(df[COLUMNS].values, total=len(df.index), desc=f'mapping {MODULE_NAME}', unit_scale=True)
    for (
        (source_prefix, source_id, source_name),
        (target_prefix, target_id, target_name),
        relation,
        pubmed_id,
        detection_method,
        source_db,
        confidence,
    ) in it:
        try:
            _add_row(
                graph,
                relation=relation,
                source_prefix=source_prefix,
                source_id=source_id,
                source_name=source_name,
                target_prefix=target_prefix,
                target_id=target_id,
                target_name=target_name,
                pubmed_id=pubmed_id,
                int_detection_method=detection_method,
                source_database=source_db,
                confidence=confidence,
            )
        except (AttributeError, ValueError, TypeError):
            logger.exception(
                '%s:%s ! %s (%s) %s:%s ! %s',
                source_prefix, source_id, source_name,
                relation,
                target_prefix, target_id, target_name,
            )
            continue

    return graph


NAMESPACE_TO_DSL = {
    'chebi': pybel.dsl.Abundance,
    'complexportal': pybel.dsl.NamedComplexAbundance,
}


def _add_row(
    graph: BELGraph,
    relation: str,
    source_prefix: str,
    source_id: str,
    source_name: Optional[str],
    target_prefix: str,
    target_id: str,
    target_name: Optional[str],
    pubmed_id: str,
    int_detection_method: str,
    source_database: str,
    confidence: str,
) -> None:  # noqa:C901
    """Add for every PubMed ID an edge with information about relationship type, source and target.

    :param source_database: row value of column source_database
    :param graph: graph to add edges to
    :param relation: row value of column relation
    :param source_prefix: row value of source prefix
    :param source_id: row value of source id
    :param target_prefix: row value of target prefix
    :param target_id: row value of target id
    :param pubmed_id: row value of column PubMed_id
    :param int_detection_method: row value of column interaction detection method
    :param confidence: row value of confidence score column
    :return: None
    """
    if pubmed_id is None:
        pubmed_id = 'database', 'intact'

    annotations = {
        'psi-mi': relation,
        'intact-detection': int_detection_method,
        'intact-source': source_database,
        'intact-confidence': confidence,
    }

    # map double spaces to single spaces in relation string
    relation = ' '.join(relation.split())

    source_dsl = NAMESPACE_TO_DSL.get(source_prefix, pybel.dsl.Protein)
    source = source_dsl(
        namespace=source_prefix,
        identifier=source_id,
        name=source_name,
    )
    target_dsl = NAMESPACE_TO_DSL.get(target_prefix, pybel.dsl.Protein)
    target = target_dsl(
        namespace=target_prefix,
        identifier=target_id,
        name=target_name,
    )

    if relation in PROTEIN_INCREASES_MOD_DICT:
        graph.add_increases(
            source,
            target.with_variants(PROTEIN_INCREASES_MOD_DICT[relation]),
            citation=pubmed_id,
            evidence=EVIDENCE,
            annotations=annotations,
            subject_modifier=SUBJECT_ACTIVITIES.get(relation),
        )

    # dna strand elongation
    elif relation == 'psi-mi:"MI:0701"(dna strand elongation)':
        target_mod = pybel.dsl.Gene(
            namespace=target_prefix,
            identifier=target_id,
            name=target_name,
            variants=[
                GeneModification(
                    name='DNA strand elongation',
                    namespace='go',
                    identifier='0022616',
                ),
            ],
        )
        graph.add_increases(
            source,
            target_mod,
            citation=pubmed_id,
            evidence=EVIDENCE,
            annotations=annotations,
        )

    # DECREASES
    elif relation in INTACT_DECREASES_ACTIONS:
        #: dna cleavage: Covalent bond breakage of a DNA molecule leading to the formation of smaller fragments
        if relation == 'psi-mi:"MI:0572"(dna cleavage)':
            target_mod = pybel.dsl.Gene(
                namespace=target_prefix,
                identifier=source_id,
                name=target_name,
            )
            graph.add_decreases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence=EVIDENCE,
                annotations=annotations,
            )
        #: rna cleavage: Any process by which an RNA molecule is cleaved at specific sites or in a regulated manner
        elif relation == 'psi-mi:"MI:0902"(rna cleavage)':
            target_mod = pybel.dsl.Rna(
                namespace=target_prefix,
                identifier=source_id,
                name=target_name,
            )
            graph.add_decreases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence=EVIDENCE,
                annotations=annotations,
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
                annotations=annotations,
            )

        #: Reaction monitoring the cleavage (hydrolysis) or a lipid molecule
        elif relation == 'psi-mi:"MI:1355"(lipid cleavage)':
            target_mod = target.with_variants(
                pybel.dsl.ProteinModification(
                    name='lipid catabolic process',
                    namespace='go',
                    identifier='0016042',
                ),
            )

            graph.add_decreases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence=EVIDENCE,
                annotations=annotations,
                object_modifier=pybel.dsl.activity(),
            )

        #: 'lipoprotein cleavage reaction': Cleavage of a lipid group covalently bound to a protein residue
        elif relation == 'psi-mi:"MI:0212"(lipoprotein cleavage reaction)':
            target_mod = target.with_variants(
                pybel.dsl.ProteinModification(
                    name='lipoprotein modification',
                    namespace='go',
                    identifier='0042160',
                ),
            )
            graph.add_decreases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence=EVIDENCE,
                annotations=annotations,
                object_modifier=pybel.dsl.activity(),
            )

        # deformylation reaction
        elif relation == 'psi-mi:"MI:0199"(deformylation reaction)':
            target_mod = target.with_variants(
                pybel.dsl.ProteinModification(
                    name='protein formylation',
                    namespace='go',
                    identifier='0018256',
                ),
            )
            graph.add_decreases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence=EVIDENCE,
                annotations=annotations,
            )
        # protein deamidation
        elif relation == 'psi-mi:"MI:2280"(deamidation reaction)':
            target_mod = target.with_variants(
                pybel.dsl.ProteinModification(
                    name='protein amidation',
                    namespace='go',
                    identifier='0018032',
                ),
            )
            graph.add_decreases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence=EVIDENCE,
                annotations=annotations,
                object_modifier=pybel.dsl.activity(),
            )

        # protein decarboxylation
        elif relation == 'psi-mi:"MI:1140"(decarboxylation reaction)':
            target_mod = target.with_variants(
                pybel.dsl.ProteinModification(
                    name='protein carboxylation',
                    namespace='go',
                    identifier='0018214',
                ),
            )
            graph.add_decreases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence=EVIDENCE,
                annotations=annotations,
            )
        # protein deamination:
        elif relation == 'psi-mi:"MI:0985"(deamination reaction)':
            target_mod = target.with_variants(
                pybel.dsl.ProteinModification(
                    name='amine binding',
                    namespace='go',
                    identifier='0043176',
                ),
            )
            graph.add_decreases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence=EVIDENCE,
                annotations=annotations,
            )
        # protein modification
        elif relation in PROTEIN_DECREASES_MOD_DICT:
            target_mod = target.with_variants(PROTEIN_DECREASES_MOD_DICT[relation])
            graph.add_decreases(
                source,
                target_mod,
                citation=pubmed_id,
                evidence=EVIDENCE,
                annotations=annotations,
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
            annotations=annotations,
        )

    # REGULATES:
    elif relation in INTACT_REGULATES_ACTIONS:
        graph.add_regulates(
            source,
            target,
            citation=pubmed_id,
            evidence=EVIDENCE,
            annotations=annotations,
        )

    # BINDS
    elif relation in INTACT_BINDS_ACTIONS:
        graph.add_binds(
            source,
            target,
            citation=pubmed_id,
            evidence=EVIDENCE,
            annotations=annotations,
        )

    # no specified relation
    else:
        raise ValueError(f"Unspecified relation {relation} between {source} and {target}")


def _create_table():
    df = get_processed_intact_df()

    d = []
    for interaction_set, bel_relation in zip(
        [INTACT_INCREASES_ACTIONS, INTACT_DECREASES_ACTIONS, INTACT_ASSOCIATION_ACTIONS, INTACT_REGULATES_ACTIONS,
         INTACT_BINDS_ACTIONS],
        ['increases', 'decreases', 'association', 'regulates', 'hasComponent'],
    ):

        for interaction in interaction_set:
            tmp_df = df[df['Interaction type(s)'] == interaction]

            if tmp_df.empty:
                continue

            # add protein modification abbreviation
            if interaction in PROTEIN_INCREASES_MOD_DICT:
                prot_mod = PROTEIN_INCREASES_MOD_DICT[interaction]

            elif interaction in PROTEIN_DECREASES_MOD_DICT:
                prot_mod = PROTEIN_DECREASES_MOD_DICT[interaction]

            else:
                prot_mod = '-'

            # add activities
            if interaction in SUBJECT_ACTIVITIES:
                activity = SUBJECT_ACTIVITIES[interaction]
            else:
                activity = '-'

            source = 'Protein'
            target = 'Protein'

            source_type = 'p'
            target_type = 'p'

            if interaction in [
                'psi-mi:"MI:0701"(dna strand elongation)',
                'psi-mi:"MI:0572"(dna cleavage)',
            ]:
                target = 'Gene'
                target_type = 'g'

            if interaction == 'psi-mi:"MI:0902"(rna cleavage)':
                target = 'Rna'
                target_type = 'r'

            source_identifier = tmp_df['#ID(s) interactor A'].iloc[0]
            logger.debug('INTERACTOR A: %s %s', type(source_identifier), source_identifier)
            target_identifier = tmp_df['ID(s) interactor B'].iloc[0]
            logger.debug('INTERACTOR B: %s %s', type(target_identifier), target_identifier)

            bel_example = f'{source_type}{source_identifier} {bel_relation} {target_type}{target_identifier}'

            d.append({
                'Source Type': source,
                'Target Type': target,
                'Interaction Type': interaction,
                'BEL Example': bel_example,
                'ProteinModification': prot_mod,
                'Activity': activity,
            })

    # intact_df = pd.DataFrame(d)


if __name__ == '__main__':
    get_bel().summarize()
