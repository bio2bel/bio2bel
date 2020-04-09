# -*- coding: utf-8 -*-

"""This module has tools for making packages that can reproducibly download and parse data."""

import json
import logging
import os
from typing import Callable, Optional
from urllib.request import urlretrieve
from zipfile import ZipFile

import pandas as pd

logger = logging.getLogger(__name__)

__all__ = [
    'make_downloader',
    'make_json_getter',
    'make_df_getter',
    'make_zipped_df_getter',
]


def make_downloader(url: str, path: str) -> Callable[[bool], str]:  # noqa: D202
    """Make a function that downloads the data for you, or uses a cached version at the given path.

    :param url: The URL of some data
    :param path: The path of the cached data, or where data is cached if it does not already exist
    :return: A function that downloads the data and returns the path of the data
    """

    def download_data(force_download: bool = False) -> str:
        """Download the data.

        :param force_download: If true, overwrites a previously cached file
        """
        if os.path.exists(path) and not force_download:
            logger.debug('using cached data at %s', path)
        else:
            logger.info('downloading %s to %s', url, path)
            urlretrieve(url, path)  # noqa: S310

        return path

    return download_data


def make_json_getter(data_url: str, data_path: str):
    """Build a function that handles downloading JSON data and parsing it.

    :param data_url: The URL of the data
    :param data_path: The path where the data should get stored
    """
    download_function = make_downloader(data_url, data_path)

    def get_json(force_download: bool = False):
        """Get the data as a JSON object.

        :param force_download: If true, overwrites a previously cached file
        """
        path = download_function(force_download=force_download)
        with open(path) as file:
            return json.load(file)

    return get_json


def make_df_getter(data_url: str, data_path: str, **kwargs) -> Callable[[Optional[str], bool, bool], pd.DataFrame]:
    """Build a function that handles downloading tabular data and parsing it into a pandas DataFrame.

    :param data_url: The URL of the data
    :param data_path: The path where the data should get stored
    :param kwargs: Any other arguments to pass to :func:`pandas.read_csv`
    """
    download_function = make_downloader(data_url, data_path)

    def get_df(url: Optional[str] = None, cache: bool = True, force_download: bool = False) -> pd.DataFrame:
        """Get the data as a pandas DataFrame.

        :param url: The URL (or file path) to download.
        :param cache: If true, the data is downloaded to the file system, else it is loaded from the internet
        :param force_download: If true, overwrites a previously cached file
        """
        if url is None and cache:
            url = download_function(force_download=force_download)

        return pd.read_csv(
            url or data_url,
            **kwargs,
        )

    return get_df


def make_zipped_df_getter(data_url: str, data_path: str, zip_path: str, **kwargs):
    """Build a function that handles downloading data inside a zip folder and parsing it into a pandas DataFrame.

    :param data_url: The URL of the data
    :param data_path: The path where the data should get stored
    :param zip_path: The path to the data inside the zip folder
    :param kwargs: Any other arguments to pass to :func:`pandas.read_csv`
    """
    download_function = make_downloader(data_url, data_path)

    def get_df(url: Optional[str] = None, cache: bool = True, force_download: bool = False) -> pd.DataFrame:
        """Get the data as a pandas DataFrame.

        :param url: The URL (or file path) to download.
        :param cache: If true, the data is downloaded to the file system, else it is loaded from the internet
        :param force_download: If true, overwrites a previously cached file
        """
        if url is not None:
            return pd.read_csv(url, **kwargs)

        if url is None and cache:
            url = download_function(force_download=force_download)

        with ZipFile(url) as zip_file:
            with zip_file.open(zip_path) as file:
                return pd.read_csv(file, **kwargs)

    return get_df
