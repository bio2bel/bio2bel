# -*- coding: utf-8 -*-

"""Constants for Bio2BEL."""

from configparser import ConfigParser
import logging
import os

log = logging.getLogger(__name__)

VERSION = '0.1.1'

BIO2BEL_DIR = os.environ.get('BIO2BEL_DIRECTORY', os.path.join(os.path.expanduser('~'), '.pybel', 'bio2bel'))
os.makedirs(BIO2BEL_DIR, exist_ok=True)

DEFAULT_CONFIG_PATH = os.path.join(BIO2BEL_DIR, 'config.ini')

UNCONFIGURED_CACHE_NAME = 'bio2bel.db'
UNCONFIGURED_CACHE_PATH = os.path.join(BIO2BEL_DIR, UNCONFIGURED_CACHE_NAME)
UNCONFIGURED_CACHE_CONNECTION = 'sqlite:///' + UNCONFIGURED_CACHE_PATH


def get_global_connection():
    """Return the global connection string.

    :rtype: str
    """
    # 6. Check if there is a global connection
    global_environ_connection = os.environ.get('BIO2BEL_CONNECTION')
    if global_environ_connection is not None:
        log.info('loading global bio2bel connection from environ: %s', global_environ_connection)
        return global_environ_connection

    # 7. Use the global configuration file's global default cache connection string
    if not os.path.exists(DEFAULT_CONFIG_PATH):
        log.info('creating config file: %s', DEFAULT_CONFIG_PATH)
        config_writer = ConfigParser()
        with open(DEFAULT_CONFIG_PATH, 'w') as file:
            config_writer.set(config_writer.default_section, 'connection', UNCONFIGURED_CACHE_CONNECTION)
            config_writer.write(file)

    log.info('fetching global bio2bel config from %s', DEFAULT_CONFIG_PATH)
    config = ConfigParser()
    config.read(DEFAULT_CONFIG_PATH)

    if not config.has_option(config.default_section, 'connection'):
        log.info('creating default connection string %s', UNCONFIGURED_CACHE_CONNECTION)
        return UNCONFIGURED_CACHE_CONNECTION

    default_connection = config.get(config.default_section, 'connection')
    log.info('load default connection string from %s', default_connection)

    return default_connection


DEFAULT_CACHE_CONNECTION = get_global_connection()
