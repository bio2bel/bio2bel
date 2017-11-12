# -*- coding: utf-8 -*-

import os

BIO2BEL_DIR = os.environ.get('BIO2BEL_DIRECTORY', os.path.join(os.path.expanduser('~'), '.pybel', 'bio2bel'))
os.makedirs(BIO2BEL_DIR, exist_ok=True)

DEFAULT_CACHE_NAME = 'bio2bel.db'
DEFAULT_CACHE_PATH = os.path.join(BIO2BEL_DIR, DEFAULT_CACHE_NAME)
DEFAULT_CACHE_CONNECTION = os.environ.get('BIO2BEL_CONNECTION', 'sqlite:///' + DEFAULT_CACHE_PATH)

DEFAULT_CONFIG_PATH = os.path.join(BIO2BEL_DIR, 'config.ini')
