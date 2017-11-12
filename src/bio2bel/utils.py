# -*- coding: utf-8 -*-


import logging
import os
from configparser import ConfigParser

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .constants import BIO2BEL_DIR, DEFAULT_CACHE_CONNECTION, DEFAULT_CONFIG_PATH

log = logging.getLogger(__name__)


def get_connection(module_name, connection=None):
    """Return the SQLAlchemy connection string if it is set

    Order of operations:

    1. Return the connection if given as a parameter
    2. Check the environment for BIO2BEL_{module_name}_CONNECTION
    3. Look in the bio2bel config file for module-specific connection. Create if doesn't exist. Check the module-
       specific section for ``connection``
    3. Look in the bio2bel module folder for a config file. Don't create if doesn't exist. Check the default section for
       ``connection``
    4. Check the environment for BIO2BEL_CONNECTION
    5. Check the bio2bel config file for default
    6. Fall back to standard default cache connection

    :param str module_name: The name of the module to get the configuration for
    :param Optional[str] connection: get the SQLAlchemy connection string
    :rtype: str
    """
    if connection is not None:
        return connection

    bio2bel_module_env = 'BIO2BEL_{}_CONNECTION'.format(module_name)
    bio2bel_module_env_value = os.environ.get(bio2bel_module_env)
    if bio2bel_module_env_value is not None:
        log.info('loaded connection from environment (%s): %s', bio2bel_module_env, bio2bel_module_env_value)
        return bio2bel_module_env_value

    global_config = ConfigParser()
    local_config = ConfigParser()

    if os.path.exists(DEFAULT_CONFIG_PATH):
        global_config.read(DEFAULT_CONFIG_PATH)
        if global_config.has_option(module_name, 'connection'):
            global_module_connection = global_config.get(module_name, 'connection')
            log.info('loading connection string from global configuration (%s): %s', DEFAULT_CONFIG_PATH,
                     global_module_connection)
            return global_module_connection

    module_config_path = os.path.join(BIO2BEL_DIR, module_name, 'config.ini')
    if os.path.exists(module_config_path):
        local_config.read(module_config_path)
        if local_config.has_option(local_config.default_section, 'connection'):
            local_module_connection = local_config.get(local_config.default_section, 'connection')
            log.info('loading connection string from local configuration (%s)', module_config_path,
                     local_module_connection)
            return local_module_connection

    if 'BIO2BEL_CONNECTION' in os.environ:
        global_environ_connection = os.environ['BIO2BEL_CONNECTION']
        log.info('loading global bio2bel connection from environ: %s', global_environ_connection)
        return global_environ_connection

    if not os.path.exists(DEFAULT_CONFIG_PATH):
        log.info('creating config file: %s', DEFAULT_CONFIG_PATH)
        config_writer = ConfigParser()
        with open(DEFAULT_CONFIG_PATH, 'w') as f:
            config_writer.set(config_writer.default_section, 'connection', DEFAULT_CACHE_CONNECTION)
            config_writer.write(f)

    log.info('fetching global bio2bel config from %s', DEFAULT_CONFIG_PATH)
    config = ConfigParser()
    config.read(DEFAULT_CONFIG_PATH)

    if not config.has_option(config.default_section, 'connection'):
        log.info('creating default connection string %s', DEFAULT_CACHE_CONNECTION)
        return DEFAULT_CACHE_CONNECTION

    default_connection = config.get(config.default_section, 'connection')
    log.info('load default connection string from %s'.format(default_connection))

    return default_connection


class Manager(object):
    """Managers handle the database construction, population and querying."""

    # This needs to be replaced with a declarative base
    Base = None
    # This needs to be replaced with the module name for the current package
    module_name = None

    def __init__(self, connection=None):
        self.connection = get_connection(self.module, connection=connection)
        self.engine = create_engine(self.connection)
        self.session_maker = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)
        self.session = self.session_maker()
        self.create_all()

    @property
    def module(self):
        """Gets the module name for this manager. Example: ``interpro``

        :rtype: str
        """
        if self.module_name is None:
            raise ValueError('Class variable, module_name, was not set in definition of {}'.format(self.__class__))

        return self.module_name

    @property
    def base(self):
        """Gets the SQLAlchemy Base for this manager"""
        if self.Base is None:
            raise ValueError('Class variable, Base, was not set in definition of {}'.format(self.__class__))

        return self.Base

    def create_all(self, check_first=True):
        """Create the empty database (tables)"""
        self.base.metadata.create_all(self.engine, checkfirst=check_first)

    def drop_all(self, check_first=True):
        """Create the empty database (tables)"""
        self.base.metadata.drop_all(self.engine, checkfirst=check_first)
