# -*- coding: utf-8 -*-

"""This module has tools for making packages that can reproducibly download and parse data."""

import logging
import os
from urllib.request import urlretrieve

import pandas as pd

log = logging.getLogger(__name__)

__all__ = [
    'make_downloader',
    'make_df_getter',
]


def make_downloader(url, path):
    """Make a function that downloads the data for you, or uses a cached version at the given path.

    :param str url: The URL of some data
    :param str path: The path of the cached data, or where data is cached if it does not already exist
    :return: A function that downloads the data and returns the path of the data
    :rtype: (bool -> str)
    """
    def download_data(force_download=False):
        """Download the data.

        :param bool force_download: If true, overwrites a previously cached file
        :rtype: str
        """
        if os.path.exists(path) and not force_download:
            log.info('using cached data at %s', path)
        else:
            log.info('downloading %s to %s', url, path)
            urlretrieve(url, path)

        return path

    return download_data


def make_df_getter(data_url, data_path, **kwargs):
    """Build a function that handles downloading tabular data and parsing it into a pandas DataFrame.

    :param str data_url: The URL of the data
    :param str data_path: The path where the data should get stored
    :param kwargs: Any other arguments to pass to :func:`pandas.read_csv`
    :rtype: (Optional[str], bool, bool) -> pandas.DataFrame
    """
    download_function = make_downloader(data_url, data_path)

    def get_df(url=None, cache=True, force_download=False):
        """Get the data as a pandas DataFrame.

        :param Optional[str] url: The URL (or file path) to download.
        :param bool cache: If true, the data is downloaded to the file system, else it is loaded from the internet
        :param bool force_download: If true, overwrites a previously cached file
        :rtype: pandas.DataFrame
        """
        if url is None and cache:
            url = download_function(force_download=force_download)

        return pd.read_csv(
            url or data_url,
            **kwargs
        )

    return get_df
