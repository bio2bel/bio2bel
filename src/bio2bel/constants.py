# -*- coding: utf-8 -*-

"""Constants for Bio2BEL."""

import logging
import os

import click
from easy_config import EasyConfig

log = logging.getLogger(__name__)

VERSION = '0.3.4'

_USER_CONFIG_DIRECTORY = os.path.abspath(os.path.join(os.path.expanduser('~'), '.config'))
DEFAULT_CONFIG_DIRECTORY = os.path.join(_USER_CONFIG_DIRECTORY, 'bio2bel')
DEFAULT_CONFIG_PATHS = [
    'bio2bel.cfg',
    os.path.join(DEFAULT_CONFIG_DIRECTORY, 'config.ini'),
    os.path.join(DEFAULT_CONFIG_DIRECTORY, 'bio2bel.cfg'),
    os.path.join(_USER_CONFIG_DIRECTORY, 'pybel', 'config.ini'),
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
    connection: str = None

    def __post_init__(self):
        os.makedirs(self.directory, exist_ok=True)
        if self.connection is None:
            self.connection = f'sqlite:///{os.path.join(self.directory, self.default_cache_name)}'


config = Config.load(_lookup_config_envvar='config')
BIO2BEL_DIR = config.directory
DEFAULT_CACHE_CONNECTION = config.connection


def get_global_connection() -> str:
    """Return the global connection string."""
    return config.connection


directory_option = click.option(
    '-d', '--directory',
    type=click.Path(file_okay=False, dir_okay=True),
    default=os.getcwd(),
    help='output directory, defaults to current.',
    show_default=True,
)
