# -*- coding: utf-8 -*-

"""Provide abstractions over BEL generation procedures."""

import logging
from abc import abstractmethod

from .abstract_manager import AbstractManager
from .cli_utils import add_cli_to_bel, add_cli_upload_bel

log = logging.getLogger(__name__)

__all__ = [
    'BELManagerMixin',
]


class BELManagerMixin(AbstractManager):
    """This mixin adds functions for making a BEL from a repository.

    *How to Use This Mixin*

    1. Either include it as a second inheriting class after :class:`AbstractManager` (this is how mixins are usually
    used):

    ..code-block:: python


        from bio2bel import AbstractManager
        from bio2bel.bel_manager import BELManagerMixin

        class MyManager(AbstractManager, BELManagerMixin):
            ...


    1. Or subclass it directly, since it also inherits from :class:`AbstractManager`, like:

    ..code-block:: python

        from bio2bel.bel_manager import BELManagerMixin

        class MyManager(BELManagerMixin):
            ...
    """

    @abstractmethod
    def to_bel(self, *args, **kwargs):
        """Convert the database to BEL.

        :rtype: pybel.BELGraph
        """

    @staticmethod
    def _cli_add_to_bel(main):
        return add_cli_to_bel(main)

    @staticmethod
    def _cli_add_upload_bel(main):
        return add_cli_upload_bel(main)

    @classmethod
    def get_cli(cls):
        """Gets a :mod:`click` main function to use as a command line interface."""
        main = super().get_cli()
        cls._cli_add_to_bel(main)
        cls._cli_add_upload_bel(main)
        return main
