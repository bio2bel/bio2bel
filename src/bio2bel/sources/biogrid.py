# -*- coding: utf-8 -*-

"""Download and convert `BioGRID <https://thebiogrid.org>`_ to BEL.

Run this script with ``python -m bio2bel.sources.biogrid``

The interaction information contained in  can be categorized into protein
interactions, genetic interactions, chemical associations, and post-translational modifications. BioGRID includes
information from major model organisms and humans.

The file downloaded from BioGRID is a zip archive containing a single file formatted in `PSI MITAB level 2.5
<https://wiki.thebiogrid.org/doku.php/psi_mitab_file>`_ compatible Tab Delimited Text file format, containing all
interaction and associated annotation data.

The interaction types in BioGRID were in the `PSI-MI <https://psicquic.github.io/MITAB25Format.html>`_
(Proteomics Standards Initiative - Molecular Interactions Controlled Vocabulary) format and were mapped to BEL
relations. The following table shows examples of how interaction types in BioGRID were mapped to BEL or other ontologies.

+------------------------------------------------------------------------+----------------------------------------+----------------------------+----------------------------+
| PSI-MI (BioGIRD)                                                       | Mapped BEL term                        | Source                     | Target                     |
+========================================================================+========================================+============================+============================+
| psi-mi:"MI:0794"(synthetic genetic interaction defined by inequality)  | :code:`pybel.BELGraph.add_association` | :class:`pybel.dsl.Gene`    | :class:`pybel.dsl.Gene`    |
+------------------------------------------------------------------------+----------------------------------------+----------------------------+----------------------------+
| psi-mi:"MI:0915"(physical association)                                 | :code:`pybel.BELGraph.add_association` | :class:`pybel.dsl.Protein` | :class:`pybel.dsl.Protein` |
+------------------------------------------------------------------------+----------------------------------------+----------------------------+----------------------------+
| psi-mi:"MI:0407"(direct interaction)                                   | :code:`pybel.BELGraph.add_binds`       | :class:`pybel.dsl.Protein` | :class:`pybel.dsl.Protein` |
+------------------------------------------------------------------------+----------------------------------------+----------------------------+----------------------------+

Summary statistics of the BEL graph generated in the BioGRID module:

+------------+----------+
| Key        | Value    |
+============+==========+
| Version    | v3.5.183 |
+------------+----------+
| Nodes      | 293030   |
+------------+----------+
| Edges      | 3127695  |
+------------+----------+
| Citations  | 9        |
+------------+----------+
| Components | 1225     |
+------------+----------+
| Density:   | 3.64E-05 |
+------------+----------+
"""

import logging
import os
from functools import lru_cache
from typing import Iterable, List, Optional, Tuple

import click
import pandas as pd
import pyobo.sources.biogrid
from pyobo.cli_utils import verbose_option
from pyobo.identifier_utils import normalize_curie
from tqdm import tqdm

import pybel.dsl
from pybel import BELGraph
from ..utils import ensure_path, get_data_dir

__all__ = [
    'get_bel',
]

logger = logging.getLogger(__name__)

EVIDENCE = 'From BioGRID'
MODULE_NAME = 'biogrid'

VERSION = '3.5.186'
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


@lru_cache()
def _get_ncbigene_mapping():
    return pyobo.sources.biogrid.get_ncbigene_mapping()


def _map_ncbigene(identifier):
    return _get_ncbigene_mapping().get(identifier)


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
    'Q7TLC7': None,  # SARS-CoV protein
}


def _process_interactor(s: str) -> Optional[str]:
    prefix, identifier = normalize_curie(s)
    if prefix is None:
        logger.warning('could not parse %s', s)
        return

    if prefix == 'ncbigene':
        return identifier
    elif prefix == 'biogrid':
        ncbigene_identifier = _map_ncbigene(identifier)
        if ncbigene_identifier is not None:
            return ncbigene_identifier
        elif identifier in BIOGRID_NCBIGENE_REMAPPING:
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
    graph = BELGraph(name='BioGRID', version=VERSION)
    it = tqdm(df[COLUMNS].values, total=len(df.index), desc=f'Convering {MODULE_NAME} to BEL', unit_scale=True)
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
            annotations=annotations,
        )
    elif relation in BIOGRID_ASSOCIATION_ACTIONS:
        graph.add_association(
            pybel.dsl.Protein(namespace='ncbigene', identifier=source_ncbigene_id),
            pybel.dsl.Protein(namespace='ncbigene', identifier=target_ncbigene_id),
            citation=pubmed_id,
            evidence=EVIDENCE,
            annotations=annotations,
        )
    elif relation in BIOGRID_BINDS_ACTIONS:
        graph.add_binds(
            pybel.dsl.Protein(namespace='ncbigene', identifier=source_ncbigene_id),
            pybel.dsl.Protein(namespace='ncbigene', identifier=target_ncbigene_id),
            citation=pubmed_id,
            evidence=EVIDENCE,
            annotations=annotations,
        )
    else:
        raise ValueError(f'Unhandled BioGrid relation: {relation}')


def _create_table_biogrid():
    df = get_processed_biogrid()

    d = []
    for interaction_set, bel_relation in zip(
            [BIOGRID_BINDS_ACTIONS, BIOGRID_ASSOCIATION_ACTIONS, BIOGRID_GENE_ASSOCIATION],
            ['hasComponent', 'association', 'association'],
    ):

        for interaction in interaction_set:
            tmp_df = df[df['#ID Interactor A'] == interaction]

            if tmp_df.empty:
                continue

            source = 'Protein'
            target = 'Protein'

            source_type = 'p'
            target_type = 'p'

            if interaction in BIOGRID_GENE_ASSOCIATION:
                source = 'Gene'
                source_type = 'g'
                target = 'Gene'
                target_type = 'g'

            source_identifier = tmp_df['#ID Interactor A'].iloc[0]

            target_identifier = tmp_df['ID Interactor B'].iloc[0]

            bel_example = f'{source_type}{source_identifier} {bel_relation} {target_type}{target_identifier}'

            d.append({
                'Source Type': source,
                'Target Type': target,
                'Interaction Type': interaction,
                'BEL Example': bel_example,
            })

    return pd.DataFrame(d)


@click.command()
@verbose_option
@click.option(
    '-o', '--output',
    default=os.path.join(get_data_dir(MODULE_NAME), 'biogrid.bel.nodelink.json.gz'),
    show_default=True,
)
def main(output: Optional[str]):
    """Convert and summarize BioGRID."""
    click.echo('Converting')
    graph = get_bel()
    click.echo('Summarizing')
    click.echo(graph.summary_str())
    click.echo('Outputting')
    pybel.dump(graph, output)


if __name__ == '__main__':
    main()
