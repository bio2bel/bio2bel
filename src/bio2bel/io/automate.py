# -*- coding: utf-8 -*-

"""Automation of installation and execution of Bio2BEL packages."""

import importlib
import logging
import os
import sys
import types
from contextlib import redirect_stdout
from typing import Any, Mapping, Optional, Tuple

from pybel import BELGraph, from_nodelink_gz, to_nodelink_gz, to_triples_file
from ..manager.bel_manager import BELManagerMixin
from ..utils import get_data_dir

__all__ = [
    'ensure_tsv',
    'ensure_graph',
    'ensure_bio2bel_installation',
]

_SPECIAL_CASES = {
    'compath': 'compath_resources',
}

logger = logging.getLogger(__name__)


def ensure_tsv(name: str, *, manager_kwargs: Optional[Mapping[str, Any]] = None) -> str:
    """Generate/save a TSV from the Bio2BEL package using :func:`pybel.to_tsv` and return its path.

    The resulting file is cached within the bio2bel package's data directory. If it already exists, the path
    is directly returned with no other code being run.

    :param name: The name of the Bio2BEL package
    :param manager_kwargs: Optional mapping to give as keyword arguments to the manager upon instantiation.
    :return: The path to the TSV file generated (inside the Bio2BEL directory) or
    """
    directory = get_data_dir(name)
    path = os.path.join(directory, f'{name}.bel.tsv')
    if os.path.exists(path):
        return path
    graph = ensure_graph(name, manager_kwargs=manager_kwargs)
    to_triples_file(graph, path)
    return path


def ensure_graph(name: str, *, manager_kwargs: Optional[Mapping[str, Any]] = None) -> BELGraph:
    """Generate, cache, and return the BEL graph for a given Bio2BEL package.

    If it has already been cached, it is loaded directly.

    :param name: The name of the Bio2BEL package
    :param manager_kwargs: Optional mapping to give as keyword arguments to the manager upon instantiation.
    """
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
    """Import a Bio2BEL package, or install it.

    :return: If the package was already installed
    :return: A module object representing the Bio2BEL package
    """
    package = _SPECIAL_CASES.get(name, f'bio2bel_{name}')

    try:
        return True, importlib.import_module(package)
    except ImportError:
        logger.info(f'pip install {package}')
        # Install this package using pip
        # https://stackoverflow.com/questions/12332975/installing-python-module-within-code

        with redirect_stdout(sys.stderr):
            pip_exit_code = os.system(f'python -m pip install -q {package}')  # noqa:S605

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
