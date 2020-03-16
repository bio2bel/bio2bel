# -*- coding: utf-8 -*-

"""Utilities for BioKEEN."""

import importlib
import logging
import os
import sys
import types
from contextlib import redirect_stdout
from typing import Any, Mapping, Optional, Tuple

import numpy as np

from pybel import BELGraph, from_nodelink_gz, to_nodelink_gz, to_tsv
from .manager.bel_manager import BELManagerMixin
from .utils import get_data_dir

__all__ = [
    'ensure_triples',
    'ensure_tsv',
    'ensure_graph',
    'ensure_bio2bel_installation',
]

_SPECIAL_CASES = {
    'compath': 'compath_resources',
}

logger = logging.getLogger(__name__)


def ensure_triples(module_name: str) -> np.ndarray:
    """Load a Bio2BEL repository.

    :param module_name: The name of the bio2bel repository (with no prefix)
    """
    path = ensure_tsv(module_name)
    return np.loadtxt(
        fname=path,
        dtype=str,
        delimiter='\t',
    )


def ensure_tsv(name: str, *, manager_kwargs: Optional[Mapping[str, Any]] = None):
    """Ensure that the Bio2BEL repository has been cached as a TSV export."""
    directory = get_data_dir(name)
    path = os.path.join(directory, f'{name}.bel.tsv')
    if os.path.exists(path):
        return path
    graph = ensure_graph(name, manager_kwargs=manager_kwargs)
    to_tsv(graph, path)
    return path


def ensure_graph(name: str, *, manager_kwargs: Optional[Mapping[str, Any]] = None) -> BELGraph:
    """Get the BEL graph for a given Bio2BEL package."""
    directory = get_data_dir(name)
    path = os.path.join(directory, f'{name}.bel.nodelink.json.gz')
    if os.path.exists(path):
        return from_nodelink_gz(path)

    _, module = ensure_bio2bel_installation(name)
    manager = module.Manager(**(manager_kwargs or {}))
    if not isinstance(manager, BELManagerMixin):
        raise ValueError(f'{module} is not enabled for BEL export')

    graph = manager.to_bel()
    to_nodelink_gz(graph, path)
    return graph


def ensure_bio2bel_installation(name: str) -> Tuple[bool, types.ModuleType]:
    """Import a package, or install it."""
    package = _SPECIAL_CASES.get(name, f'bio2bel_{name}')

    try:
        return True, importlib.import_module(package)
    except ImportError:
        logger.info(f'pip install {package}')
        # Install this package using pip
        # https://stackoverflow.com/questions/12332975/installing-python-module-within-code

        with redirect_stdout(sys.stderr):
            pip_exit_code = os.system(f'python -m pip install -q {package}')

        if 0 != pip_exit_code:  # command failed
            logger.warning(f'could not find {package} on PyPI. Try installing from GitHub with:')
            name = package.split("_")[-1]
            logger.warning(f'\n   pip install git+https://github.com/bio2bel/{name}.git\n')
            sys.exit(1)

        try:
            return False, importlib.import_module(package)
        except ImportError:
            logger.exception(f'failed to import {package}')
            sys.exit(1)
