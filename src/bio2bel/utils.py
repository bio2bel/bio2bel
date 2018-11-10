# -*- coding: utf-8 -*-

"""Utilities for Bio2BEL."""

import logging
import os
import shutil
from typing import Mapping, Optional, Type

from easy_config import EasyConfig
from pkg_resources import VersionConflict, iter_entry_points

from .constants import BIO2BEL_DIR, DEFAULT_CONFIG_DIRECTORY, DEFAULT_CONFIG_PATHS, VERSION, config

log = logging.getLogger(__name__)

__all__ = [
    'get_data_dir',
    'get_connection',
    'get_version',
    'get_modules',
    'clear_cache',
]


def get_data_dir(module_name: str) -> str:
    """Ensure the appropriate Bio2BEL data directory exists for the given module, then returns the file path.

    :param module_name: The name of the module. Ex: 'chembl'
    :return: The module's data directory
    """
    module_name = module_name.lower()
    data_dir = os.path.join(BIO2BEL_DIR, module_name)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


class _AbstractModuleConfig(EasyConfig):
    connection: str = None


def get_module_config_cls(module_name: str) -> Type[_AbstractModuleConfig]:  # noqa: D202
    """Build a module configuration class."""

    class ModuleConfig(_AbstractModuleConfig):
        NAME = f'bio2bel:{module_name}'
        FILES = DEFAULT_CONFIG_PATHS + [
            os.path.join(DEFAULT_CONFIG_DIRECTORY, module_name, 'config.ini')
        ]

    return ModuleConfig


def get_connection(module_name: str, connection: Optional[str] = None) -> str:
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
    # 1. Use given connection
    if connection is not None:
        return connection

    module_name = module_name.lower()
    module_config_cls = get_module_config_cls(module_name)
    module_config = module_config_cls.load()

    return module_config.connection or config.connection


def get_version() -> str:
    """Get the software version of Bio2BEL."""
    return VERSION


def get_modules() -> Mapping:
    """Get all Bio2BEL modules."""
    modules = {}

    for entry_point in iter_entry_points(group='bio2bel', name=None):
        entry = entry_point.name

        try:
            modules[entry] = entry_point.load()
        except VersionConflict:
            log.exception('Version conflict in %s', entry)
            continue
        except ImportError:
            log.exception('Issue with importing module %s', entry)
            continue

    return modules


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
