# -*- coding: utf-8 -*-

"""Convert Rhea to BEL."""

import gzip
import logging

import rdflib

from ..utils import ensure_path

import pybel
import pybel.dsl as dsl

__all__ = [
    'get_bel',
]

logger = logging.getLogger(__name__)

MODULE_NAME = 'rhea'
VERSION = '116'  # released on 2020-12-02
URL = 'ftp://ftp.expasy.org/databases/rhea/rdf/rhea.rdf.gz'

# Prefix/namespace for SPARQL queries
PREFIX = "rh"
NAMESPACE = "http://rdf.rhea-db.org/"

# Strings used in RDF parsing
RH_NAMESPACE = rdflib.Namespace("http://rdf.rhea-db.org/")
RH_PREFIX = 'rh'

CH_NAMESPACE = "http://purl.obolibrary.org/obo/CHEBI_"

CHEBI = 'CHEBI'


def _build_query(expression: str):
    return rdflib.plugins.sparql.prepareQuery(expression, initNs={RH_PREFIX: RH_NAMESPACE})


def participants(g: rdflib.Graph, reaction_uri: rdflib.term.URIRef):
    """Return a list of PyBEL dsl nodes in format [reactants, products] for a given reaction."""
    participants = []
    # Repeat for each side of the reaction, reactants and products
    for suffix in ('_L', '_R'):
        # Get the URI for the given side of a reaction (http://...10348 ---> http://...10348_L)
        side_uri = reaction_uri + suffix
        # Prepare a query that finds for each reaction side, the following information for each participant:
        # the name of the compound, the CHEBI ID of the compound (if it's a small molecule or a polymer) or of each reactivePart of a genericCompound (polypeptide/polynucleotide)
        q = _build_query(
            """
            SELECT ?compound_name ?chebi ?reactivePart WHERE {
                ?side rh:contains ?participant .
                ?participant rh:compound ?compound .
                ?compound rh:name ?compound_name .
                OPTIONAL {
                    ?compound rh:reactivePart ?part_id .
                    ?part_id rh:chebi ?chebi .
                    ?part_id rh:name ?reactivePart .
                } .
                OPTIONAL {?compound rh:chebi ?chebi} .
                OPTIONAL {?compound rh:underlyingChebi ?chebi}
            }
            """,
        )
        result = g.query(q, initBindings={'side': side_uri})
        # Get an iterable of the compounds (no need to remove duplicates since dictionary keys must be unique)
        compounds = map(lambda x: x[0], result)
        # Create a dictionary that will contain the nodes associated with a compound (for GenericCompounds with multiple ReactiveParts)
        # Goal: for compounds with multiple ReactiveParts, link those reactiveParts together so they can easily be crafted into a ComplexAbundance later
        nodes_by_compound = {c: [] for c in compounds}
        for r in set(result):
            compound_name, chebi_uri, reactive_part_name = r
            # Based on the way the OPTIONAL modifier works, the SELECT query may return ?compound_name entries by themselves, without any ?chebi information
            if not chebi_uri:
                continue
            # Remove the namespace from the chebi_uri to access the identifier
            identifier = chebi_uri.replace(CH_NAMESPACE, '')
            # Use the compound name if no reactive part is available
            name = reactive_part_name if reactive_part_name else compound_name
            # Build an abundance node, and append it to the node list under the correct compound
            node = dsl.Abundance(namespace=CHEBI, name=name, identifier=identifier)
            nodes_by_compound[compound_name].append(node)

        # Now, create a list of nodes by itself that will be appended to in the next loop
        nodes = []
        for compound, node_list in nodes_by_compound.items():
            if len(node_list) == 1:
                nodes.append(node_list[0])
                continue
            else:
                # If there are multiple nodes, there must be multiple reactiveParts
                # We represent that as a complexAbundance with name 'compound'
                complex_abundance = dsl.ComplexAbundance(node_list, name=compound)
                nodes.append(complex_abundance)

        participants.append(nodes)
    return participants


def get_bel() -> pybel.BELGraph:
    """Get the Rhea data."""
    # Parse the RDF file
    gz_path = ensure_path(MODULE_NAME, URL)
    logger.info('reading Rhea from %s', gz_path)
    with gzip.open(gz_path) as f:
        g = rdflib.Graph()
        g.parse(file=f)

    # Get a list of all the reactions in the database
    # (the bidirectionalReaction criterion is added to ensure that we only recieve the nondirectional version of a given reaction)
    rxns = g.query(_build_query(
        """
        SELECT ?reaction ?reactionEquation WHERE {
            ?reaction rh:equation ?reactionEquation .
            ?reaction rh:bidirectionalReaction ?bdr
        }
        """,
    ))
    rv = pybel.BELGraph(name='Rhea', version=VERSION)
    # Loop over reactions, adding reaction nodes to rv as we go
    # Rather than converting to a set (time-consuming), just let the PyBEL graph handle the occasional duplicate
    for (reaction_uri, _) in rxns:
        # Retrieve the reactants and products of the reaction
        reactants, products = participants(g, reaction_uri)
        # Add a reaction node to the BELGraph
        rv.add_reaction(reactants, products)
    return rv


if __name__ == '__main__':
    get_bel().summarize()
