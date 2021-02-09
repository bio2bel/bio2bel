# -*- coding: utf-8 -*-

"""Convert Rhea to BEL."""

import logging
from typing import Any, Dict, List, Tuple

import rdflib

import pybel
import pybel.dsl as dsl
from bio2bel.constants import BIO2BEL_MODULE

__all__ = [
    'get_bel',
]

logger = logging.getLogger(__name__)

MODULE_NAME = 'rhea'
VERSION = '116'  # released on 2020-12-02
URL = 'ftp://ftp.expasy.org/databases/rhea/rdf/rhea.rdf.gz'

# Strings used in RDF parsing
RH_NAMESPACE = rdflib.Namespace("http://rdf.rhea-db.org/")
RH_PREFIX = 'rh'

CH_NAMESPACE = "http://purl.obolibrary.org/obo/CHEBI_"

CHEBI = 'CHEBI'


def _build_query(expression: str) -> rdflib.plugins.sparql.sparql.Query:
    # rdflib.plugins.sparql.prepareQuery(expression, initNs={RH_PREFIX: RH_NAMESPACE})
    # The above line is broken for some reason, with error:
    #   AttributeError: module 'rdflib.plugins' has no attribute 'sparql'
    # So instead, we'll just replace() the prefix with the namespace
    return expression.replace(RH_PREFIX, RH_NAMESPACE)


def participants(g: rdflib.Graph, reaction_uri: rdflib.term.URIRef) -> Tuple[List[dsl.BaseEntity], List[dsl.BaseEntity]]:
    """Return a list of PyBEL dsl nodes in format (reactants, products) for a given reaction."""
    participants: Tuple[List[Any], List[Any]] = ([], [])
    # Repeat for each side of the reaction, reactants and products
    for i, suffix in enumerate(('_L', '_R')):
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
        nodes_by_compound: Dict[str, List[dsl.BaseEntity]] = {c: [] for c in compounds}
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

        for compound, node_list in nodes_by_compound.items():
            node = None
            if len(node_list) == 1:
                node = node_list[0]
            else:
                # If there are multiple nodes, there must be multiple reactiveParts
                # We represent that as a complexAbundance with name 'compound'
                node = dsl.ComplexAbundance(node_list, name=compound)
            # Append the node to the corresponding list in participants
            participants[i].append(node)

    return participants


def get_bel() -> pybel.BELGraph:
    """Get the Rhea data."""
    # Parse the RDF file
    g = BIO2BEL_MODULE.ensure_rdf('rhea', url=URL)
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
