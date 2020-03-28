# -*- coding: utf-8 -*-

"""Utilities for ComPath."""

import logging
from typing import Collection, Mapping

import pandas as pd

__all__ = [
    'write_dict',
    'dict_to_df',
]

logger = logging.getLogger(__name__)


def write_dict(data: Mapping[str, Collection[str]], path: str) -> None:
    """Write a dictionary to a file as an Excel document."""
    gene_sets_df = dict_to_df(data)
    logger.info("Exporting gene sets to %s", path)
    gene_sets_df.to_excel(path, index=False)
    logger.info("Exported gene sets to %s", path)


def dict_to_df(data: Mapping[str, Collection[str]]) -> pd.DataFrame:
    """Convert a dictionary to a DataFrame."""
    return pd.DataFrame({
        key: pd.Series(list(values))
        for key, values in data.items()
    })
