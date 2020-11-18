Bio2BEL |build| |coverage| |docs| |zenodo|
==========================================
Bio2BEL is a project aimed at bringing biological databases and other structured knowledge sources in a wide variety
of schemata into the unified framework of the
`Biological Expression Language <https://biological-expression-language.github.io/>`_ [1]_.

Two important places to look:

- `How to make a Bio2BEL Repository <http://bio2bel.readthedocs.io/en/latest/tutorial.html>`_
- `How to use the CLI <http://bio2bel.readthedocs.io/en/latest/cli.html>`_

Installation |pypi_version| |python_versions| |pypi_license|
------------------------------------------------------------
Download the latest stable code from `PyPI <https://pypi.org/project/bio2bel>`_ with:

.. code-block:: sh

   $ python -m pip install bio2bel

or get the latest from GitHub with:

.. code-block:: sh

   $ git clone https://github.com/bio2bel/bio2bel.git
   $ cd bio2bel
   $ python -m pip install -e .

or check the `installation instructions <http://bio2bel.readthedocs.io/en/latest/#installation>`_.

Citation
--------
If you find Bio2BEL useful for your work, please consider citing:

.. [1] Hoyt, C. T., *et al.* (2019). `Integration of Structured Biological Data Sources using Biological Expression Language
       <https://doi.org/10.1101/631812>`_. *bioRxiv*, 631812.

.. |build| image:: https://travis-ci.com/bio2bel/bio2bel.svg?branch=master
    :target: https://travis-ci.com/bio2bel/bio2bel
    :alt: Build Status

.. |coverage| image:: https://codecov.io/gh/bio2bel/bio2bel/coverage.svg?branch=master
    :target: https://codecov.io/gh/bio2bel/bio2bel?branch=master
    :alt: Coverage Status

.. |docs| image:: http://readthedocs.org/projects/bio2bel/badge/?version=latest
    :target: http://bio2bel.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. |python_versions| image:: https://img.shields.io/pypi/pyversions/bio2bel.svg
    :alt: Stable Supported Python Versions

.. |pypi_version| image:: https://img.shields.io/pypi/v/bio2bel.svg
    :alt: Current version on PyPI

.. |pypi_license| image:: https://img.shields.io/pypi/l/bio2bel.svg
    :alt: MIT License

.. |zenodo| image:: https://zenodo.org/badge/99800349.svg
    :target: https://zenodo.org/badge/latestdoi/99800349
