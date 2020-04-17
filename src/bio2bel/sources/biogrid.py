# -*- coding: utf-8 -*-

"""This script downloads and parses BioGRID data and maps the interaction types to BEL.

To run this script, install Bio2BEL and then do:

python -m bio2bel.sources.biogrid
"""

import logging
from typing import Iterable, List, Optional, Tuple

import pandas as pd
import pyobo.sources.biogrid
from pyobo.identifier_utils import normalize_curie
from tqdm import tqdm

import pybel.dsl
from pybel import BELGraph
from ..utils import ensure_path

__all__ = [
    'get_bel',
]

logger = logging.getLogger(__name__)

EVIDENCE = 'From BioGRID'
MODULE_NAME = 'biogrid'

VERSION = '3.5.183'
BASE_URL = 'https://downloads.thebiogrid.org/Download/BioGRID/Release-Archive'
URL = f'{BASE_URL}/BIOGRID-{VERSION}/BIOGRID-ALL-{VERSION}.mitab.zip'

"""All of these can be extracted from the original file with the following

cat BIOGRID-ALL-3.5.183.mitab.txt | cut -f 12 | sort | uniq -c

Note that column 12 is the interaction column. You could also do

gzcat BIOGRID-ALL-3.5.183.mitab.zip | cut -f 12 | sort | uniq -c

becuase the zip file only contains that one file
"""

#: Relationship types in BioGRID that map to BEL relation 'increases'
BIOGRID_GENE_ASSOCIATION = {
    'psi-mi:"MI:0794"(synthetic genetic interaction defined by inequality)',
    'psi-mi:"MI:0799"(additive genetic interaction defined by inequality)',
    'psi-mi:"MI:0796"(suppressive genetic interaction defined by inequality)',
}

#: Relationship types in BioGRID that map to BEL relation 'association'
BIOGRID_ASSOCIATION_ACTIONS = {
    'psi-mi:"MI:0403"(colocalization)',
    'psi-mi:"MI:0914"(association)',
    # Look on OLS: https://www.ebi.ac.uk/ols/ontologies/mi/terms?iri=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FMI_0915
    # They're in a complex together, but not necessarily touching. This is
    # really dumb to put in a binary association database. Check ComplexPortal
    # or other higher granularity sources for more information
    'psi-mi:"MI:0915"(physical association)',
}

BIOGRID_BINDS_ACTIONS = {
    # https://www.ebi.ac.uk/ols/ontologies/mi/terms?iri=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FMI_0407
    'psi-mi:"MI:0407"(direct interaction)',
}

biogrid_ncbigene_mapping = pyobo.sources.biogrid.get_ncbigene_mapping()

#: biogrid id to ncbigene id
BIOGRID_NCBIGENE_REMAPPING = {
    '4349295': None,  # https://www.yeastgenome.org/locus/S000006792
    '4349491': None,  # http://www.candidagenome.org/cgi-bin/locus.pl?locus=CAF0007452
    '4349337': None,  # https://www.yeastgenome.org/locus/S000006962
    '4349775': None,  # http://www.candidagenome.org/cgi-bin/locus.pl?locus=CAL0000184983
    '4349716': None,  # http://www.candidagenome.org/cgi-bin/locus.pl?locus=CAL0000193047
    '4349853': None,  # http://www.candidagenome.org/cgi-bin/locus.pl?locus=CAL0006683
    '4383869': None,  # SARS-CoV2 protein ORF3B, not on uniprot or entrez
    '4383875': None,  # SARS-CoV2 protein ORF9C, not on uniprot or entrez
}

#: uniprot id to ncbigene id
UNIPROT_NCBIGENE_REMAPPING = {
    # FIXME
    'P0DTC1': None,  # SARS-CoV2 protein https://swissmodel.expasy.org/repository/uniprot/P0DTC1
    # TODO checkme
    'P0DTD2': '1489679',  # SARS-CoV2 protein https://swissmodel.expasy.org/repository/uniprot/P0DTD2
}


def _process_interactor(s: str) -> Optional[str]:
    prefix, identifier = normalize_curie(s)
    if prefix is None:
        logger.warning('could not parse %s', s)
        return

    if prefix == 'ncbigene':
        return identifier
    elif prefix == 'biogrid':
        if identifier in biogrid_ncbigene_mapping:
            return biogrid_ncbigene_mapping[identifier]
        if identifier in BIOGRID_NCBIGENE_REMAPPING:
            remapped = BIOGRID_NCBIGENE_REMAPPING[identifier]
            if not remapped:
                logger.debug('tried but failed curation on %s', s)
            return remapped
        else:
            logger.warning('need to curate: %s', s)
            return
    elif prefix == 'uniprot':
        if identifier in UNIPROT_NCBIGENE_REMAPPING:
            remapped = UNIPROT_NCBIGENE_REMAPPING[identifier]
            if not remapped:
                logger.debug('tried but failed curation on %s', s)
            return remapped
        else:
            logger.warning('need to curate: %s', s)
            return
    else:
        logger.warning('unhandled interactor: %s (%s:%s)', s, prefix, identifier)


def _process_xrefs(s: str) -> List[Tuple[str, str]]:
    return list(_iter_process_xrefs(s))


def _iter_process_xrefs(s: str) -> Iterable[Tuple[str, str]]:
    """Take a string with pipe-delimited curies and split/normalize them.

    Compact Uniform Identfiers (CURIE) examples:
    - hgnc:12345
    - ncbigene:12345
    - uniprot:P12345
    - ec-code:1.2.3.15

    Goal:
    make hgnc:1234|ncbigene:1245|uniprot...:12345" into a list of tuples
    """
    for curie in s.split('|'):
        curie = curie.strip()
        prefix, identifier = normalize_curie(curie)
        if prefix is not None:
            yield prefix, identifier


def _process_pmid(s: str) -> str:
    """Process provenance column."""
    if not s.startswith('pubmed:'):
        raise ValueError(f'Non pubmed: {s}')
    return s[len('pubmed:')]


COLUMNS = [
    '#ID Interactor A',
    'ID Interactor B',
    'Interaction Types',
    'Publication Identifiers',
    'Interaction Detection Method',
    'Source Database',
    'Confidence Values',
]


def get_processed_biogrid() -> pd.DataFrame:
    """Load BioGRID file, filter, and rename columns and return a dataframe.

    :return: dataframe of preprocessed BioGRID data
    """
    path = ensure_path(prefix=MODULE_NAME, url=URL)
    logger.info('reading BioGRID from %s', path)
    df = pd.read_csv(path, sep='\t', dtype=str, usecols=COLUMNS)

    logger.info('mapping provenance')
    df['Publication Identifiers'] = df['Publication Identifiers'].map(_process_pmid)

    logger.info('mapping interactors')
    df['#ID Interactor A'] = df['#ID Interactor A'].map(_process_interactor)
    df['ID Interactor B'] = df['ID Interactor B'].map(_process_interactor)

    # logger.info('mapping alternate identifiers')
    # df['Alt IDs Interactor A'] = df['Alt IDs Interactor A'].map(_process_xrefs)
    # df['Alt IDs Interactor B'] = df['Alt IDs Interactor B'].map(_process_xrefs)

    return df


def get_bel() -> BELGraph:
    """Get a BEL graph for BioGRID."""
    df = get_processed_biogrid()
    graph = BELGraph(name=MODULE_NAME)
    it = tqdm(df[COLUMNS].values, total=len(df.index), desc=f'mapping {MODULE_NAME}', unit_scale=True)
    for source_ncbigene_id, target_ncbigene_id, relation, pubmed_id, detection_method, source_db, confidence in it:
        if pd.isna(source_ncbigene_id) or pd.isna(target_ncbigene_id):
            continue
        _add_my_row(
            graph,
            relation=relation,
            source_ncbigene_id=source_ncbigene_id,
            target_ncbigene_id=target_ncbigene_id,
            pubmed_id=pubmed_id,
            int_detection_method=detection_method,
            source_database=source_db,
            confidence=confidence,
        )
    return graph


def _add_my_row(
    graph: BELGraph,
    relation: str,
    source_ncbigene_id: str,
    target_ncbigene_id: str,
    pubmed_id: str,
    int_detection_method: str,
    source_database: str,
    confidence: str,
) -> None:  # noqa:C901
    """Add an edge with information about relationship type, source, and target for every PubMed ID.

    :param graph: graph to add edges to
    :param relation: row value of column relation
    :param source_ncbigene_id: row value of column source
    :param target_ncbigene_id: row value of column target
    :param pubmed_id: row value of column pubmed_id
    :param int_detection_method: row value of column interaction detection method
    """
    annotations = {
        'psi-mi': relation,
        'biogrid-detection': int_detection_method,
        'biogrid-source': source_database,
        'biogrid-confidence': confidence,
    }

    if relation in BIOGRID_GENE_ASSOCIATION:
        graph.add_association(
            pybel.dsl.Gene(namespace='ncbigene', identifier=source_ncbigene_id),
            pybel.dsl.Gene(namespace='ncbigene', identifier=target_ncbigene_id),
            citation=pubmed_id,
            evidence=EVIDENCE,
            annotations=annotations.copy(),
        )
    elif relation in BIOGRID_ASSOCIATION_ACTIONS:
        graph.add_association(
            pybel.dsl.Protein(namespace='ncbigene', identifier=source_ncbigene_id),
            pybel.dsl.Protein(namespace='ncbigene', identifier=target_ncbigene_id),
            citation=pubmed_id,
            evidence=EVIDENCE,
            annotations=annotations.copy(),
        )
    elif relation in BIOGRID_BINDS_ACTIONS:
        graph.add_binds(
            pybel.dsl.Protein(namespace='ncbigene', identifier=source_ncbigene_id),
            pybel.dsl.Protein(namespace='ncbigene', identifier=target_ncbigene_id),
            citation=pubmed_id,
            evidence=EVIDENCE,
            annotations=annotations.copy(),
        )
    else:
        raise ValueError(f'Unhandled BioGrid relation: {relation}')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    _graph = get_bel()
    _graph.summarize()
    import os

    pybel.dump(_graph, os.path.expanduser('~/Desktop/biogrid.bel.nodelink.json'))
