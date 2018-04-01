How to Make a Bio2BEL Package
=============================
In this tutorial, we're going to explain how to make your own Bio2BEL package using
`miRTarBase <https://github.com/bio2bel/mirtarbase>`_ as an example. This package already exists and is an excellent
example.


Naming the Package
------------------
The package should be named ``bio2bel_XXX`` with all lowercase letters for the name of the package, even if the source
uses stylized capitalization. This means our example package wil be called ``bio2bel_mirtarbase``.

Note that the repository can be named differently from the package. On the `Bio2BEL <https://github.com/bio2bel>`_
organization on GitHub, we have chosen to use simply a lowercase name of the source to eliminate redundancy in the URL.

Organizing Constants
--------------------
The package should have a top-level module named ``constants.py`` as an easily accesible location for constants. A
variable called ``MODULE_NAME`` should be defined with the lowercase name of the source. Additionally,
the functions :func:`bio2bel.get_data_dir` and :func:`bio2bel.get_connection` to locate the appropriate directory
for data and configuration loading.

.. code-block:: python

    # /src/bio2bel_mirtarbase/constants.py

    from bio2bel import get_data_dir, get_connection

    MODULE_NAME = 'mirtarbase'
    DATA_DIRECTORY_PATH = get_data_dir(MODULE_NAME)
    DEFAULT_CONNECTION = get_connection(MODULE_NAME)

Making a Manager
----------------
There should be a concrete implementation of :class:`bio2bel.AbstractManager`. For consistent style, we recommend
implementing this in a top-level module called ``manager.py`` and naming the class ``Manager``. Check the miRTarBase
repository for an example of the
`package structure <https://github.com/bio2bel/mirtarbase/tree/master/src/bio2bel_mirtarbase>`_ and an example of the
`implementation of a Manager <https://github.com/bio2bel/mirtarbase/blob/master/src/bio2bel_mirtarbase/manager.py>`_.

.. autoclass:: bio2bel.AbstractManager
    :inherited-members:
    :members:

Organizing the Manager
----------------------
This class should be importable from the top-level. In our example, this means that you can either import the manager
class with :code:`from bio2bel_mirtarbase import Manager` or  :code:`import bio2bel_mirtarbase.Manager`.

This can be accomplished by importing the ``Manager`` in the top-level ``__init__.py``.

.. code-block:: python

    # /src/bio2bel_mirtarbase/__init__.py

    from .manager import Manager

    __all__ = ['Manager]

    __title__ = 'bio2bel_mirtarbase
    ...

A full example of the ``__init__.py`` for mirTarBase can be found `here <https://github.com/bio2bel/mirtarbase/blob/master/src/bio2bel_mirtarbase/__init__.py>`_.

Making a Command Line Interface
-------------------------------
The package should include a top-level module called ``cli.py``. Normally, :mod:`click` can be used to build nice
Command Line Interfaces like:

.. code-block:: python

    import click

    @click.group()
    def main():
        pass

    @main.command()
    def command_1()
        pass

However, if you've properly implemented an AbstractManager, then :func:`bio2bel.build_cli` can be used to generate the
main function and automatically implement several commands.

.. code-block:: python

    # /src/bio2bel_mirtarbase/cli.py

    from .manager import Manager
    from bio2bel import build_cli

    main = build_cli(Manager)

    if __name__ == '__main__':
        main()

This command line application will automatically have commands for  ``populate``, ``drop``, and ``web``. It can be
extended like ``main`` from the first example as well.

Additionally, if the optional function ``to_bel`` is implemented in the manager, then several other commands
(e.g., ``to_bel_file``, ``upload_bel``, etc.) become available as well.

Setting up ``__main__.py``
--------------------------

Finally, the top-level ``__main__.py`` should import main and should have 3 lines, reading exactly as follows:

.. code-block:: python

    # /src/bio2bel_mirtarbase/__main__.py

    from .cli import main

    if __name__ == '__main__':
        main()

Entry Points in ``setup.py``
----------------------------
Bio2BEL uses the entry points loader to find packages in combination with setuptools's ``entry_points`` argument.

.. code-block:: python

    # /setup.py

    import setuptools

    setuptools.setup(
        ...
        entry_points={
            'bio2bel': [
                'mirtarbase = bio2bel_mirtarbase',
            ],
        }
        ...
    )

This directly enables the Bio2BEL CLI to operate using the package's cli so it's possible to call things like
``bio2bel mirtarbase populate`` or ``bio2bel mirtarbase drop``.

Additionally, a command-line interaface should be registered as well called ``bio2bel__mirtarbase`` that directly
points to the ``main`` function in ``cli.py``.

.. code-block:: python

    # /setup.py

    import setuptools

    setuptools.setup(
        ...
        entry_points={
            'bio2bel': [
                'mirtarbase = bio2bel_mirtarbase',
            ],
            'console_scripts': [
              'bio2bel_mirtarbase = bio2bel_mirtarbase.cli:main',
          ]
        }
        ...
    )

Check the miRTarBase repostiroy for a `full example <https://github.com/bio2bel/mirtarbase/blob/master/setup.py>`_ of
a `setup.py`.

Testing
-------
Though it's not a requirement, writing tests is a plus. There are several testing classes available in
:mod:`bio2bel.testing` to enable writing tests quickly.

.. code-block:: python

    # /tests/constants.py

    from bio2bel.testing import make_temporary_cache_class_mixin
    from bio2bel_mirtarbase import Manager

    TemporaryCacheClassMixin = make_temporary_cache_class_mixin(Manager)


Additionally, this class can also be generated as a subclass directly and used to override the class-level ``populate``
function

.. code-block:: python

    class PopulatedTemporaryCacheClassMixin(TemporaryCacheClassMixin):
        @classmethod
        def populate(cls)
            cls.manager.populate(url='... test data path ...')

Keep in mind that your populate function will probably have different argument names, especially if there are multiple
files necessary to populate. Using test data instead of full source data is preferred for faster testing!
