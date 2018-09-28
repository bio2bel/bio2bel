# -*- coding: utf-8 -*-

"""Constants for Bio2BEL."""

import logging
import os

from easy_config import EasyConfig

log = logging.getLogger(__name__)

VERSION = '0.1.6-dev'


DEFAULT_CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.config', 'bio2bel.cfg')


class Config(EasyConfig):
    """Configuration for Bio2BEL."""
    NAME = 'bio2bel'
    FILES = ['bio2bel.cfg', DEFAULT_CONFIG_PATH]

    #: The directory in which Bio2BEL data is stored
    directory: str = os.path.join(os.path.expanduser('~'), '.bio2bel')

    #: The default name of the Bio2BEL database with SQLite
    default_cache_name: str = 'bio2bel.db'

    #: The SQLAlchemy connection string to the database
    connection: str = f'sqlite:///{os.path.join(directory, default_cache_name)}'


config = Config.load(_lookup_config_envvar='config')
os.makedirs(config.directory, exist_ok=True)

BIO2BEL_DIR = config.directory
DEFAULT_CACHE_CONNECTION = config.connection
