# -*- coding: utf-8 -*-

"""ComPath is a project for using gene-centric (and later other types of entities) to compare pathway knowledge.

This package provides guidelines, tutorials, and tools for making standardized ``compath`` packages as well as a
unifying framework for integrating them.
"""

from .manager import CompathManager, get_compath_manager_classes, get_compath_modules  # noqa: F401
from .mixins import CompathPathwayMixin, CompathProteinMixin  # noqa: F401
