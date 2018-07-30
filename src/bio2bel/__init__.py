# -*- coding: utf-8 -*-

"""Bio2BEL is a project aimed at integrating biological databases and other structured knowledge sources.

Because they come from a wide variety of schemata, this package provides tools for converting them into the unified
framework of `Biological Expression Language <http://http://openbel.org/>`_.

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

from .downloading import make_df_getter, make_downloader  # noqa: F401
from .manager import abstract_manager  # noqa: F401
from .manager.abstract_manager import AbstractManager  # noqa: F401
from .utils import get_data_dir, get_version  # noqa: F401

__version__ = '0.1.1'

__title__ = 'bio2bel'
__description__ = "A package for converting biological stuff to BEL"
__url__ = 'https://github.com/bio2bel/bio2bel'

__author__ = 'Charles Tapley Hoyt'
__email__ = 'charles.hoyt@scai.fraunhofer.de'

__license__ = 'Apache 2.0 License'
__copyright__ = 'Copyright (c) 2017-2018 Charles Tapley Hoyt'
