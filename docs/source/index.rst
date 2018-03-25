Bio2BEL
=======
Bio2BEL is a project aimed at bringing biological databases in a wide variety of schemata into the unified framework
of Biological Expression Language.

This package provides a command line interface through which other bio2bel packages can be linked.

Project Structure
=================
All Bio2BEL projects should have a similar structure. In the top level, there should be certain modules:

- ``manager.py`` should include a class called ``Manager`` that has a function ``Manager.populate()``
- ``cli.py`` should have a main ``click`` group called ``main`` and optionally have commands for ``populate``, ``drop``,
  ``deploy``, and ``web``

How to Register
===============
Bio2BEL uses the entry points loader to find packages in combination with setuptools's ``entry_points`` argument.

.. code-block:: python

   import setuptools

   setuptools.setup(
      ...
      entry_points={
          'bio2bel': [
              'chembl = bio2bel_chembl',
          ],
          'console_scripts': [
              'bio2bel_chembl = bio2bel_chembl.cli:main',
          ]
      }
      ...
   )

Table of Contents
=================

.. toctree::
   :maxdepth: 2

   projects
   abstractmanager
   utils
   testing


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
