# -*- coding: utf-8 -*-

from pkg_resources import iter_entry_points

GROUP_NAME = 'bio2bel'

# Allow `from bio2bel.ext import *`
entries = [
    entry_point.name
    for entry_point in iter_entry_points(group=GROUP_NAME, name=None)
]


def setup():
    """Add the :code:`bio2bel.ext` importer/loader to the meta_path. Should probably only be called once."""
    from .exthook import ExtensionImporter
    importer = ExtensionImporter(GROUP_NAME)
    importer.install()


setup()
del setup  # Do a bit of cleanup. Not sure if it's necessary, but Flask did...

__version__ = '0.0.1'

__title__ = 'bio2bel'
__description__ = "A package for converting biological stuff to BEL"
__url__ = 'https://github.com/bio2bel/bio2bel'

__author__ = 'Charles Tapley Hoyt'
__email__ = 'charles.hoyt@scai.fraunhofer.de'

__license__ = 'Apache 2.0 License'
__copyright__ = 'Copyright (c) 2017 Charles Tapley Hoyt'

__all__ = entries
