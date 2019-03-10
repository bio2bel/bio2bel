# -*- coding: utf-8 -*-

"""Downloading utilities for OBO."""

import os
from typing import Callable, Optional

import obonet
from networkx import MultiDiGraph, read_gpickle, write_gpickle

from bio2bel.downloading import make_downloader

__all__ = [
    'make_obo_getter',
]


def make_obo_getter(data_url: str,
                    data_path: str,
                    *,
                    preparsed_path: Optional[str] = None,
                    ) -> Callable[[Optional[str], bool, bool], MultiDiGraph]:
    """Build a function that handles downloading OBO data and parsing it into a NetworkX object.

    :param data_url: The URL of the data
    :param data_path: The path where the data should get stored
    :param preparsed_path: The optional path to cache a pre-parsed json version
    """
    download_function = make_downloader(data_url, data_path)

    def get_obo(url: Optional[str] = None, cache: bool = True, force_download: bool = False) -> MultiDiGraph:
        """Download and parse a GO obo file with :mod:`obonet` into a MultiDiGraph.

        :param url: The URL (or file path) to download.
        :param cache: If true, the data is downloaded to the file system, else it is loaded from the internet
        :param force_download: If true, overwrites a previously cached file
        """
        if preparsed_path is not None and os.path.exists(preparsed_path):
            return read_gpickle(preparsed_path)

        if url is None and cache:
            url = download_function(force_download=force_download)

        result = obonet.read_obo(url)

        if preparsed_path is not None:
            write_gpickle(result, preparsed_path)

        return result

    return get_obo
