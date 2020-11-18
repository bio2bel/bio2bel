# -*- coding: utf-8 -*-

"""Utilities for Bio2BEL."""

import hashlib
import logging
import os
import pathlib
import shutil
import types
from typing import Iterable, Mapping, Optional, Tuple
from urllib.parse import urlparse
from urllib.request import urlretrieve

import requests
from botocore.client import BaseClient
from pkg_resources import UnknownExtra, VersionConflict, iter_entry_points

from .constants import BIO2BEL_DIR, config

__all__ = [
    'get_data_dir',
    'prefix_directory_join',
    'get_url_filename',
    'ensure_path',
    'get_connection',
    'get_bio2bel_modules',
    'clear_cache',
]

logger = logging.getLogger(__name__)


def get_data_dir(module_name: str) -> str:
    """Ensure the appropriate Bio2BEL data directory exists for the given module, then returns the file path.

    :param module_name: The name of the module. Ex: 'chembl'
    :return: The module's data directory
    """
    module_name = module_name.lower()
    data_dir = os.path.join(BIO2BEL_DIR, module_name)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def prefix_directory_join(prefix: str, *parts: str) -> str:
    """Join the parts onto the prefix directory."""
    return os.path.join(get_data_dir(prefix), *parts)


def get_url_filename(url: str) -> str:
    """Get the URL's file name."""
    parse_result = urlparse(url)
    return os.path.basename(parse_result.path)


def ensure_path(
    prefix: str,
    url: str,
    *,
    path: Optional[str] = None,
    use_requests: bool = False,
    force: bool = False,
    bucket: Optional[str] = None,
    s3_client: Optional[BaseClient] = None,
) -> str:
    """Download a file if it doesn't exist.

    :param force: If set to true, will re-download from source and re-upload to S3
    """
    if path is None:
        path = get_url_filename(url)

    path = prefix_directory_join(prefix, path)

    if not os.path.exists(path) or force:
        if bucket is not None:  # try downloading from AWS if available
            s3_client = _ensure_s3_client(s3_client)
            s3_key = _get_s3_key(prefix, path)
            if not _has_file(s3_client, bucket=bucket, key=s3_key) and not force:
                logger.info('downloading from AWS (bucket=%s): %s to %s', bucket, s3_key, path)
                s3_client.download_file(bucket, s3_key, path)
                return path

        logger.info('downloading from source %s to %s', url, path)
        if use_requests:
            res = requests.get(url)
            with open(path, 'wb') as file:
                file.write(res.content)
        else:
            urlretrieve(url, path)  # noqa:S310

    if bucket is not None:
        s3_client = _ensure_s3_client(s3_client)
        s3_key = _get_s3_key(prefix, path)
        if _has_file(s3_client, bucket=bucket, key=s3_key) and not force:
            logger.debug('already available on S3. Not uploading again.')
            return path

        logger.info('uploading to AWS (bucket=%s): %s to %s', bucket, path, s3_key)
        s3_client.upload_file(path, bucket, s3_key)

    return path


def _get_s3_key(prefix: str, path: str) -> str:
    path = pathlib.Path(path)
    return os.path.join(prefix, path.name)


def _has_file(s3_client: BaseClient, *, bucket: str, key: str) -> bool:
    from botocore.errorfactory import ClientError

    try:
        s3_client.head_object(Bucket=bucket, Key=key)
    except ClientError:
        return False
    else:
        return True


def _ensure_s3_client(s3_client: Optional[BaseClient]) -> BaseClient:
    if s3_client is None:
        import boto3
        s3_client = boto3.client('s3')
    return s3_client


def get_connection(*, connection: Optional[str] = None) -> str:
    """Return the SQLAlchemy connection string if it is set.

    Order of operations:

    1. Return the connection if given as a parameter
    2. Check the environment for BIO2BEL_{module_name}_CONNECTION
    3. Look in the bio2bel config file for module-specific connection. Create if doesn't exist. Check the
       module-specific section for ``connection``
    4. Look in the bio2bel module folder for a config file. Don't create if doesn't exist. Check the default section
       for ``connection``
    5. Check the environment for BIO2BEL_CONNECTION
    6. Check the bio2bel config file for default
    7. Fall back to standard default cache connection

    :param module_name: The name of the module to get the configuration for
    :param connection: get the SQLAlchemy connection string
    :return: The SQLAlchemy connection string based on the configuration
    """
    return connection or config.connection


def get_bio2bel_modules() -> Mapping[str, types.ModuleType]:
    """Get all Bio2BEL modules."""
    return dict(_get_modules('bio2bel'))


def _get_managers(group):
    for name, module in _get_modules(group):
        if hasattr(module, 'Manager'):
            yield name, module.Manager


def _get_modules(group) -> Iterable[Tuple[str, types.ModuleType]]:
    """Get all modules."""
    for entry_point in iter_entry_points(group=group, name=None):
        entry = entry_point.name

        try:
            yield entry, entry_point.load()
        except VersionConflict as exc:
            logger.warning('Version conflict in %s: %s', entry, exc)
            continue
        except UnknownExtra as exc:
            logger.warning('Unknown extra in %s: %s', entry, exc)
            continue
        except ImportError as exc:
            logger.exception('Issue with importing module %s: %s', entry, exc)
            continue


def clear_cache(module_name: str, keep_database: bool = True) -> None:
    """Clear all downloaded files."""
    data_dir = get_data_dir(module_name)
    if not os.path.exists(data_dir):
        return
    for name in os.listdir(data_dir):
        if name in {'config.ini', 'cfg.ini'}:
            continue
        if name == 'cache.db' and keep_database:
            continue
        path = os.path.join(data_dir, name)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

    os.rmdir(data_dir)


def get_namespace_hash(items, hash_function=None) -> str:
    """Get the namespace hash.

    Defaults to MD5.
    """
    if hash_function is None:
        hash_function = hashlib.md5
    m = hash_function()
    for name, encoding in items:
        m.update(f'{name}:{encoding}'.encode('utf8'))
    return m.hexdigest()
