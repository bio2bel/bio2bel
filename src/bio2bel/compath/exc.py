# -*- coding: utf-8 -*-

"""Exceptions for ComPath."""


class CompathManagerTypeError(TypeError):
    """Raised when trying to instantiate an improperly implemented ComPath manager."""


class CompathManagerPathwayModelError(CompathManagerTypeError):
    """Raised when missing an appropriate pathway_model class variable."""


class CompathManagerPathwayIdentifierError(CompathManagerTypeError):
    """Raised when missing an appropriate pathway_model_standard_identifer class variable."""


class CompathManagerProteinModelError(CompathManagerTypeError):
    """Raised when missing an appropriate protein_model class variable."""
