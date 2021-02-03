# -*- coding: utf-8 -*-

"""Convert Rhea to BEL."""

import gzip
import logging

from ..utils import ensure_path

import rdflib
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

CH_NAMESPACE = rdflib.Namespace("http://purl.obolibrary.org/obo/CHEBI_")

CHEBI = 'CHEBI'
POLYMER = 'POLYMER'


def _build_query(expression):
    return rdflib.plugins.sparql.prepareQuery(expression, initNs={RH_PREFIX: RH_NAMESPACE})


def id_and_swap(g, reaction_uri):
    """Given the URI of a reaction, return the base ID for that reaction (the nondirectional version) if it exists, as well as the initial direction."""
    q = _build_query('SELECT ?base_rxn WHERE {?base_rxn ?relation ?id . FILTER (?relation IN (rh:directionalReaction, rh:bidirectionalReaction))}')
    result = list(g.query(q, initBindings={'id': reaction_uri}))

    def uri_to_id(uri):
        """Convert a resource URI to an ID"""
        return uri.replace(RH_NAMESPACE, RH_PREFIX + ":")

    if result:
        base_uri = result[0][0]
        swap = _should_swap(g, base_uri, reaction_uri)
        return uri_to_id(base_uri), swap
    else:
        return uri_to_id(reaction_uri), False


def _should_swap(g, base_uri, reaction_uri):
    """Returns the direction of the specified reaction (whether the base reaction's order should be swapped for the current reaction)"""
    # First determine whether the specific reaction is a directional or bidirectional variant
    bidirectional_q = _build_query('SELECT ?type WHERE {?base ?type ?rxn}')
    result = list(g.query(bidirectional_q, initBindings={'base': base_uri, 'rxn': reaction_uri}))
    if 'bidirectional' in result[0][0]:
        return False
    # If not bidirectional, determine whether the directional order matches what's set
    equations = []
    for uri in (base_uri, reaction_uri):
        order_q = _build_query('SELECT ?equation WHERE {?uri rh:equation ?equation}')
        result = list(g.query(order_q, initBindings={'uri': uri}))
        eq = str(result[0][0])
        # Retrieve the first half of the equation (the part before the = or =>) for later comparison
        first_half = eq.split('=')[0]
        equations.append(first_half)
    # Rhea represents nondirectional reactions as A + B = C + D
    # and directional reactions as A + B => C + D OR C + D => A + B, depending on the reaction direction
    # If the first half of the base equation matches the first half of the directional reaction equation (A + B and A + B), no swap is necessary
    # But if the halves don't match (A + B and C + D), a swap IS necessary
    if equations[0] == equations[1]:
        return False
    else:
        return True


def participants(g, base_id):
    """Return a list of PyBEL dsl nodes in format [reactants, products] for a given reaction."""
    participants = []
    for suffix in ('_L', '_R'):
        # Get the ID for the given side of a reaction (rh:10348 ---> rh:10348_L)
        side_id = base_id + suffix
        q = _build_query(
            "SELECT ?compound ?name ?accession WHERE {" + side_id + """ rh:contains ?participant .
                ?participant rh:compound ?compound .
                ?compound rh:name ?name .
                ?compound rh:accession ?accession .
            }""")
        result = list(map(lambda x: _to_pybel(g, x), g.query(q)))
        participants.append(result)
    return participants


def _to_pybel(g, participant):
    """Convert a given participant to PyBEL."""
    uri, name, accession = participant
    name = str(name)
    node = None
    if CHEBI in accession:
        # Accessions are formatted like "CHEBI:85007"
        # To access the identifier, remove "CHEBI:"
        identifier = accession.replace(CHEBI + ':', '')
        node = dsl.Abundance(namespace=CHEBI, name=name, identifier=identifier)
    elif POLYMER in accession:
        # To access the CHEBI identifier, use the rh:underlyingChebi property
        q = _build_query('SELECT ?chebi WHERE { ?uri rh:underlyingChebi ?chebi }')
        result = list(g.query(q, initBindings={'uri': uri}))
        identifier = result[0][0]
        node = dsl.Abundance(namespace=CHEBI, name=name, identifier=identifier)
    else:
        # Otherwise, this node is a rh:GenericCompound (either a polypeptide, polynucleotide, or heteropolysaccharide)
        # GenericCompounds don't have a CHEBI identifier, but their rh:ReactivePart subcomponents do
        # So, we take the ReactivePart to be the main part of the node, and use xrefs to indicate the compound it's part of
        q = _build_query(
            """
            SELECT ?reactivepart ?chebi WHERE {
                ?uri rh:reactivePart ?part .
                ?part rh:name ?reactivepart .
                ?part rh:chebi ?chebi
            }
            """
        )
        result = list(g.query(q, initBindings={'uri': uri}))
        reactive_part = str(result[0][0])
        # remove namespace from identifier: 'http://purl.obolibrary.org/obo/CHEBI_58210' ----> '58210'
        identifier = result[0][1].replace(CH_NAMESPACE, '')
        extra_reference = {'compound': name, 'comment': 'The "name" property of this node represents the reactive part of the compound "' + name + '."'}
        node = dsl.Abundance(namespace=CHEBI, name=reactive_part, identifier=identifier, xrefs=[extra_reference])
    return node


def get_bel() -> pybel.BELGraph:
    """Get the Rhea data."""
    # Parse the RDF file
    gz_path = ensure_path(MODULE_NAME, URL)
    logger.info('reading Rhea from %s', gz_path)
    with gzip.open(gz_path) as f:
        g = rdflib.Graph()
        g.parse(file=f)

    # Get a list of all the reactions in the database
    rxns = g.query(_build_query(
        """
        SELECT ?reaction ?reactionEquation WHERE {
            ?reaction rh:equation ?reactionEquation .
        }
        """
    ))
    rv = pybel.BELGraph(name='Rhea', version=VERSION)
    # Get the reactants
    for i, (reaction_uri, _) in enumerate(rxns):
        # Get the base ID for the given reaction (meaning the nondirectional, generic version) if it exists
        # as well as a boolean indicating whether the reactants and products should be swapped to reflect the direction of the given reaction
        base_id, swap = id_and_swap(g, reaction_uri)
        reactants, products = participants(g, base_id)
        if swap:
            reactants, products = products, reactants
        rv.add_reaction(reactants, products)
    return rv


if __name__ == '__main__':
    get_bel().summarize()
