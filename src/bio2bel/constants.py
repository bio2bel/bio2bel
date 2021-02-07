# -*- coding: utf-8 -*-

"""Constants for Bio2BEL."""

import os

import click
import pystow

_USER_CONFIG_DIRECTORY = os.path.abspath(os.path.join(os.path.expanduser('~'), '.config'))
DEFAULT_CONFIG_PATHS = [
    'bio2bel.cfg',
    'bio2bel.ini',
    'pybel.cfg',
    'pybel.ini',
    os.path.join(_USER_CONFIG_DIRECTORY, 'bio2bel.ini'),
    os.path.join(_USER_CONFIG_DIRECTORY, 'bio2bel.cfg'),
    os.path.join(_USER_CONFIG_DIRECTORY, 'bio2bel', 'config.ini'),
    os.path.join(_USER_CONFIG_DIRECTORY, 'bio2bel', 'bio2bel.cfg'),
    os.path.join(_USER_CONFIG_DIRECTORY, 'bio2bel', 'bio2bel.ini'),
    os.path.join(_USER_CONFIG_DIRECTORY, 'pybel.ini'),
    os.path.join(_USER_CONFIG_DIRECTORY, 'pybel.cfg'),
    os.path.join(_USER_CONFIG_DIRECTORY, 'pybel', 'config.ini'),
    os.path.join(_USER_CONFIG_DIRECTORY, 'pybel', 'pybel.cfg'),
    os.path.join(_USER_CONFIG_DIRECTORY, 'pybel', 'pybel.ini'),
]

BIO2BEL_MODULE = pystow.module('bio2bel')
BIO2BEL_HOME = BIO2BEL_MODULE.base

directory_option = click.option(
    '-d', '--directory',
    type=click.Path(file_okay=False, dir_okay=True),
    default=os.getcwd(),
    help='output directory, defaults to current.',
    show_default=True,
)
