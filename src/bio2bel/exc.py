# -*- coding: utf-8 -*-

"""Bio2BEL custom errors."""


class Bio2BELMissingNameError(TypeError):
    """Raised when an abstract manager is subclassed and instantiated without overriding the module name."""


class Bio2BELModuleCaseError(TypeError):
    """Raised when the module name in a subclassed and instantiated manager is not all lowercase."""


class Bio2BELMissingModelsError(TypeError):
    """Raises when trying to build a flask admin app with no models defined."""


class Bio2BELTestMissingManagerError(TypeError):
    """Raised when "Manager" was not set as a class-level variable.."""


class Bio2BELManagerTypeError(TypeError):
    """Raised when the class-level variable "Manager" is not a subclass of :class:`bio2bel.AbstractManager`."""
