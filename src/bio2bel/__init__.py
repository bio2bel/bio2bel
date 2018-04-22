# -*- coding: utf-8 -*-

"""Bio2BEL is a project aimed at bringing biological databases and other structured knowledge sources in a wide variety
of schemata into the unified framework of `Biological Expression Language <http://http://openbel.org/>`_.

This package provides guidelines, tutorials, and tools for making standardized ``bio2bel`` packages as well as a
unifying framework for integrating them.

Installation
------------
Easiest
~~~~~~~
Download the latest stable code from `PyPI <https://pypi.org/bio2bel>`_ with:

.. code-block:: sh

   $ python3 -m pip install bio2bel

Get the Latest
~~~~~~~~~~~~~~~
Download the most recent code from `GitHub <https://github.com/bio2bel/bio2bel>`_ with:

.. code-block:: sh

   $ python3 -m pip install git+https://github.com/bio2bel/bio2bel.git

For Developers
~~~~~~~~~~~~~~
Clone the repository from `GitHub <https://github.com/bio2bel/bio2bel>`_ and install in editable mode with:

.. code-block:: sh

   $ git clone https://github.com/bio2bel/bio2bel.git
   $ cd bio2bel
   $ python3 -m pip install -e .


Testing
-------
Bio2BEL is tested with Python3 on Linux using `Travis CI <https://travis-ci.org/bio2bel/bio2bel>`_.
"""

from pkg_resources import iter_entry_points

from . import abstractmanager, cli_utils, utils
from .abstractmanager import *
from .cli_utils import *
from .downloading import *
from .utils import *

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

__version__ = '0.0.10-dev'

__title__ = 'bio2bel'
__description__ = "A package for converting biological stuff to BEL"
__url__ = 'https://github.com/bio2bel/bio2bel'

__author__ = 'Charles Tapley Hoyt'
__email__ = 'charles.hoyt@scai.fraunhofer.de'

__license__ = 'Apache 2.0 License'
__copyright__ = 'Copyright (c) 2017-2018 Charles Tapley Hoyt'

__all__ = entries + abstractmanager.__all__ + utils.__all__ + cli_utils.__all__
