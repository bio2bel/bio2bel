# -*- coding: utf-8 -*-

"""Entry points for PyKEEN.

PyKEEN is a machine learning library for knowledge graph embeddings that supports node clustering,
link prediction, entity disambiguation, question/answering, and other tasks with knowledge graphs.
It provides an interface for registering plugins using Python's entrypoints under the
``pykeen.triples.extension_importer`` and ``pykeen.triples.prefix_importer`` groups. More specific
information about how the Bio2BEL plugin is loaded into PyKEEN can be found in Bio2BEL's
`setup.cfg <https://github.com/bio2bel/bio2bel/blob/master/setup.cfg>`_ under the ``[options.entry_points]``
header.

The following example shows how you can parse/load the triples from a Bio2BEL
repository using the ``bio2bel`` prefix:

.. code-block:: python

    # Example 1A: Make triples factory
    from pykeen.triples import TriplesFactory
    tf = TriplesFactory(path='bio2bel:mirtarbase')

    # Example 1B: Use directly in the pipeline, which automatically invokes training/testing set stratification
    from pykeen.pipeline import pipeline
    results = pipeline(
        dataset='bio2bel:mirtarbase',
        model='TransE',
    )
"""

import numpy as np

from .automate import ensure_tsv

__all__ = [
    'ensure_triples',
]


def ensure_triples(module_name: str) -> np.ndarray:
    """Load a Bio2BEL repository.

    :param module_name: The name of the bio2bel repository (with no prefix)
    :return: A three column array with head, relation, and tail in each row
    """
    path = ensure_tsv(module_name)
    return np.loadtxt(
        fname=path,
        dtype=str,
        delimiter='\t',
    )
