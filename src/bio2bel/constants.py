# -*- coding: utf-8 -*-

"""Constants for Bio2BEL."""

import logging
import os

from easy_config import EasyConfig

log = logging.getLogger(__name__)

VERSION = '0.2.0'

DEFAULT_CONFIG_DIRECTORY = os.path.abspath(os.path.join(os.path.expanduser('~'), '.config', 'bio2bel'))
DEFAULT_CONFIG_PATHS = [
    'bio2bel.cfg',
    os.path.join(DEFAULT_CONFIG_DIRECTORY, 'config.ini'),
    os.path.join(DEFAULT_CONFIG_DIRECTORY, 'bio2bel.cfg'),
]


class Config(EasyConfig):
    """Configuration for Bio2BEL."""

    NAME = 'bio2bel'
    FILES = DEFAULT_CONFIG_PATHS

    #: The directory in which Bio2BEL data is stored
    directory: str = os.path.join(os.path.expanduser('~'), '.bio2bel')

    #: The default name of the Bio2BEL database with SQLite
    default_cache_name: str = 'bio2bel.db'

    #: The SQLAlchemy connection string to the database
    connection: str = f'sqlite:///{os.path.join(directory, default_cache_name)}'

    @classmethod
    def load(cls, *args, **kwargs):
        """Load the Bio2BEL configuration and ensure the directory."""
        rv = super().load(*args, **kwargs)
        os.makedirs(rv.directory, exist_ok=True)
        return rv


config = Config.load(_lookup_config_envvar='config')
BIO2BEL_DIR = config.directory
DEFAULT_CACHE_CONNECTION = config.connection


def get_global_connection() -> str:
    """Return the global connection string."""
    return config.connection
