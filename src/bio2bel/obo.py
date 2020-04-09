# -*- coding: utf-8 -*-

"""Downloading utilities for OBO."""

import json
import logging
import os
from typing import Callable, Optional, TextIO

import click
import obonet
from networkx import MultiDiGraph, read_gpickle, write_gpickle
from pyobo import get_obo_graph

from bel_resources.obo import convert_obo_graph_to_belanno, convert_obo_graph_to_belns
from pybel.constants import BELNS_ENCODING_STR
from .downloading import make_downloader
from .utils import get_data_dir, get_namespace_hash

__all__ = [
    'make_obo_getter',
]

logger = logging.getLogger(__name__)


def make_obo_getter(
    data_url: str,
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

        logger.info(f'Reading OBO from {url}')
        result = obonet.read_obo(url)

        if preparsed_path is not None:
            write_gpickle(result, preparsed_path)

        return result

    return get_obo


@click.group()
def main():
    """OBO Utilities."""


keyword_option = click.argument('keyword')
directory_option = click.option(
    '-d', '--directory',
    default=os.getcwd(),
    type=click.Path(file_okay=False, dir_okay=True, exists=True),
    help='Defaults to current working directory',
)


@main.command()
@click.argument('keyword')
@directory_option
@click.option('-e', '--encoding', default=BELNS_ENCODING_STR, show_default=True)
def belns(keyword: str, directory: str, encoding: Optional[str]):
    """Write as a BEL namespace."""
    graph = get_obo_graph(keyword)

    items = {}
    mapping = {}
    for node, data in graph.nodes(data=True):
        items[data['name']] = encoding
        mapping[node] = data['name']

    namespace_hash = get_namespace_hash(items.items())
    with open(os.path.join(directory, f'{keyword}.belns.md5'), 'w') as file:
        print(namespace_hash, file=file)  # noqa:T001

    with open(os.path.join(directory, f'{keyword}.belns.mapping'), 'w') as file:
        json.dump(mapping, file, indent=2)

    outputs = [
        (os.path.join(directory, f'{keyword}.belns'), False),
        (os.path.join(directory, f'{keyword}-names.belns'), True),
    ]
    for path, use_names in outputs:
        with open(path, 'w') as file:
            convert_obo_graph_to_belns(
                graph,
                file=file,
                encoding=encoding,
                use_names=use_names,
            )


@main.command()
@keyword_option
@click.option('-f', '--file', type=click.File('w'))
def belanno(keyword: str, file: TextIO):
    """Write as a BEL annotation."""
    directory = get_data_dir(keyword)
    obo_url = f'http://purl.obolibrary.org/obo/{keyword}.obo'
    obo_path = os.path.join(directory, f'{keyword}.obo')
    obo_cache_path = os.path.join(directory, f'{keyword}.obo.pickle')

    obo_getter = make_obo_getter(obo_url, obo_path, preparsed_path=obo_cache_path)
    graph = obo_getter()
    convert_obo_graph_to_belanno(
        graph,
        file=file,
    )


if __name__ == '__main__':
    main()
