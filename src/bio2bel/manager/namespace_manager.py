# -*- coding: utf-8 -*-

"""Provide abstractions over BEL namespace generation procedures."""

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Iterable, List, Mapping, Optional, Set, TextIO

import click
from sqlalchemy.ext.declarative import DeclarativeMeta
from tqdm import tqdm

from bel_resources import write_annotation, write_namespace
from pybel import BELGraph
from pybel.manager.models import Base, Namespace, NamespaceEntry
from .cli_manager import CliMixin
from .connection_manager import ConnectionManager
from ..constants import directory_option
from ..utils import get_namespace_hash

__all__ = [
    'Bio2BELMissingNamespaceModelError',
    'BELNamespaceManagerMixin',
]

logger = logging.getLogger(__name__)


class Bio2BELMissingNamespaceModelError(TypeError):
    """Raised when the namespace_model class variable is not defined."""


class BELNamespaceManagerMixin(ABC, ConnectionManager, CliMixin):
    """A mixin for generating a BEL namespace file and uploading it to the PyBEL database.

    First, you'll have to make sure that :mod:`pybel` is installed. This can be done with pip like:

    .. code-block:: bash

        $ pip install pybel

    To use this mixin, you need to properly implement the AbstractManager, and add additional class variables and
    functions.

    ``namespace_model``: The SQLAlchemy class that represents the entity to serialize into the namespace

    .. code-block:: python

        >>> from bio2bel import AbstractManager
        >>> from bio2bel.namespace_manager import NamespaceManagerMixin
        >>> from .models import HumanGene
        >>>
        >>> class MyManager(AbstractManager, NamespaceManagerMixin):
        ...     module_name = 'hgnc'
        ...     ...
        ...     namespace_model = HumanGene

    Several fields from Identifiers.org should be populated, including:

    1. ``identifiers_recommended``
    2. ``identifiers_pattern``
    3. ``identifiers_miriam``
    4. ``identifiers_namespace``
    5. ``identifiers_url``

    .. code-block:: python

        >>> from bio2bel import AbstractManager
        >>> from bio2bel.namespace_manager import NamespaceManagerMixin
        >>> from .models import HumanGene
        >>>
        >>> class MyManager(AbstractManager, NamespaceManagerMixin):
        ...     module_name = 'hgnc'
        ...     ...
        ...     namespace_model = HumanGene
        ...     identifiers_recommended = 'HGNC'
        ...     identifiers_pattern = '...'
        ...     identifiers_miriam = 'MIR:00000080'
        ...     identifiers_namespace = 'hgnc'
        ...     identifiers_url = 'http://identifiers.org/hgnc/'

    Two methods need to be implemented. First, the static method ``_get_identifier`` should take in the namespace model
    and give back the database identifier. for us, this is easy, since the HumanGene class has an attribute called
    ``hgnc_id``.

    Perhaps in the future, we will enfoce the convention that the namespace model should have a field
    called <module name>_id, but having this method gives lots of flexibility.

    This is also a good place to add more specific type annotations (not yet tested with MyPy).

    .. code-block:: python

        >>> from bio2bel import AbstractManager
        >>> from bio2bel.namespace_manager import NamespaceManagerMixin
        >>> from .models import HumanGene
        >>>
        >>> class MyManager(AbstractManager, NamespaceManagerMixin):
        ...     module_name = 'hgnc'
        ...     ...
        ...     namespace_model = HumanGene
        ...     identifiers_recommended = 'HGNC'
        ...     identifiers_pattern = '...'
        ...     identifiers_miriam = 'MIR:00000080'
        ...     identifiers_namespace = 'hgnc'
        ...     identifiers_url = 'http://identifiers.org/hgnc/'
        ...
        ...     @staticmethod
        ...     def _get_identifier(model: HumanGene) -> str:
        ...         return model.hgnc_id

    Last, we must implement the method ``_create_namespace_entry_from_model``, which encodes the logic of building a
    :class:`pybel.manager.models.NamespaceEntry` from the Bio2BEL repository's namespace model.

    For a repository like ChEBI, this is very simple, but for HGNC there is reason to add additional logic
    to get the proper encodings.

    .. code-block:: python

        >>> from bio2bel import AbstractManager
        >>> from bio2bel.namespace_manager import NamespaceManagerMixin
        >>> from pybel.manager.models import Namespace, NamespaceEntry
        >>> from .models import HumanGene
        >>>
        >>> class MyManager(AbstractManager, NamespaceManagerMixin):
        ...     module_name = 'hgnc'
        ...     ...
        ...     namespace_model = HumanGene
        ...     identifiers_recommended = 'HGNC'
        ...     identifiers_pattern = '...'
        ...     identifiers_miriam = 'MIR:00000080'
        ...     identifiers_namespace = 'hgnc'
        ...     identifiers_url = 'http://identifiers.org/hgnc/'
        ...
        ...     @staticmethod
        ...     def _get_identifier(model: HumanGene) -> str:
        ...         return model.hgnc_id
        ...
        ...     def _create_namespace_entry_from_model(self, model: HumanGene, namespace: Namespace) -> NamespaceEntry:
        ...         return NamespaceEntry(
        ...             encoding=encodings.get(model.locus_type, 'GRP'),
        ...             identifier=model.hgnc_id,
        ...             name=model.hgnc_symbol,
        ...             namespace=namespace,
        ...         )
    """

    namespace_model: DeclarativeMeta

    #: Can be set to False for namespaces that don't have labels
    has_names: bool = True

    is_namespace: bool = True
    is_annotation: bool = False

    identifiers_recommended = None
    identifiers_pattern = None
    identifiers_miriam = None
    identifiers_namespace = None
    identifiers_url = None

    def __init__(self, *args, **kwargs):  # noqa: D107
        if not hasattr(self, 'namespace_model'):
            raise Bio2BELMissingNamespaceModelError('Class variable `namespace_model` was not defined.')

        super().__init__(*args, **kwargs)

        # Ensure that the PyBEL database is ready to go
        Base.metadata.create_all(self.engine, checkfirst=True)

    @abstractmethod
    def _create_namespace_entry_from_model(self, model, namespace: Namespace) -> NamespaceEntry:
        """Create a PyBEL NamespaceEntry model from a Bio2BEL model.

        :param model: The model to convert
        :param namespace: The PyBEL namespace to add to
        """

    @classmethod
    def _get_identifier(cls, model) -> str:
        """Extract the identifier from an instance of namespace_model.

        :param model: The model to convert
        """
        return getattr(model, f'{cls.module_name}_id')

    @staticmethod
    def _get_encoding(model) -> str:
        """Extract the BEL encoding from an instance of a namespace_model.

        :param model: The model to convert
        """
        return model.bel_encoding

    @staticmethod
    def _get_name(model) -> str:
        """Extract the name from an instance of namespace_model.

        :param model: The model to convert
        """
        return model.name

    def _iterate_namespace_models(self, **kwargs) -> Iterable:
        """Return an iterator over the models to be converted to the namespace."""
        return tqdm(
            self._get_query(self.namespace_model),
            total=self._count_model(self.namespace_model),
            **kwargs,
        )

    @classmethod
    def _get_namespace_name(cls) -> str:
        """Get the nicely formatted name of this namespace."""
        return cls.identifiers_recommended or cls.module_name

    @classmethod
    def _get_namespace_keyword(cls) -> str:
        """Get the keyword to use as the reference BEL namespace."""
        return cls.identifiers_namespace or cls.module_name.upper()

    @classmethod
    def _get_namespace_url(cls) -> str:
        """Get the URL to use as the reference BEL namespace."""
        return cls.identifiers_url or f'_{cls.module_name.upper()}'

    def _get_default_namespace(self) -> Optional[Namespace]:
        """Get the reference BEL namespace if it exists."""
        return self._get_query(Namespace).filter(Namespace.url == self._get_namespace_url()).one_or_none()

    def _get_namespace_entries(self, namespace) -> List:
        return [
            namespace_entry
            for namespace_entry in (
                self._create_namespace_entry_from_model(model, namespace)
                for model in self._iterate_namespace_models()
            )
            if namespace_entry is not None
        ]

    def _make_namespace(self) -> Namespace:
        """Make a namespace."""
        namespace = Namespace(
            name=self._get_namespace_name(),
            keyword=self._get_namespace_keyword(),
            url=self._get_namespace_url(),
            version=str(time.asctime()),
        )
        self.session.add(namespace)

        entries = self._get_namespace_entries(namespace)
        self.session.add_all(entries)

        t = time.time()
        logger.info('committing models')
        self.session.commit()
        logger.info('committed models in %.2f seconds', time.time() - t)

        return namespace

    @staticmethod
    def _get_old_entry_identifiers(namespace: Namespace) -> Set[NamespaceEntry]:
        """Convert a PyBEL generalized namespace entries to a set.

        Default to using the identifier, but can be overridden to use the name instead.

        >>> {term.identifier for term in namespace.entries}
        """
        return {term.identifier for term in namespace.entries}

    def _update_namespace(self, namespace: Namespace) -> None:
        """Update an already-created namespace.

        Note: Only call this if namespace won't be none!
        """
        old_entry_identifiers = self._get_old_entry_identifiers(namespace)
        new_count = 0
        skip_count = 0

        for model in self._iterate_namespace_models():
            if self._get_identifier(model) in old_entry_identifiers:
                continue

            entry = self._create_namespace_entry_from_model(model, namespace=namespace)
            if entry is None or entry.name is None:
                skip_count += 1
                continue

            new_count += 1
            self.session.add(entry)

        t = time.time()
        logger.info('got %d new entries. skipped %d entries missing names. committing models', new_count, skip_count)
        self.session.commit()
        logger.info('committed models in %.2f seconds', time.time() - t)

    def add_namespace_to_graph(self, graph: BELGraph) -> Namespace:
        """Add this manager's namespace to the graph."""
        namespace = self.upload_bel_namespace()
        graph.namespace_url[namespace.keyword] = namespace.url

        # Add this manager as an annotation, too
        self._add_annotation_to_graph(graph)

        return namespace

    def _add_annotation_to_graph(self, graph: BELGraph) -> None:
        """Add this manager as an annotation to the graph."""
        if 'bio2bel' not in graph.annotation_list:
            graph.annotation_list['bio2bel'] = set()

        graph.annotation_list['bio2bel'].add(self.module_name)

    def upload_bel_namespace(self, update: bool = False) -> Namespace:
        """Upload the namespace to the PyBEL database.

        :param update: Should the namespace be updated first?
        """
        if not self.is_populated():
            self.populate()

        namespace = self._get_default_namespace()

        if namespace is None:
            logger.info('making namespace for %s', self._get_namespace_name())
            return self._make_namespace()

        if update:
            self._update_namespace(namespace)

        return namespace

    def drop_bel_namespace(self) -> Optional[Namespace]:
        """Remove the default namespace if it exists."""
        namespace = self._get_default_namespace()

        if namespace is not None:
            for entry in tqdm(namespace.entries, desc=f'deleting entries in {self._get_namespace_name()}'):
                self.session.delete(entry)
            self.session.delete(namespace)

            logger.info('committing deletions')
            self.session.commit()
            return namespace

    def write_bel_namespace(self, file: TextIO, use_names: bool = False) -> None:
        """Write as a BEL namespace file."""
        if not self.is_populated():
            self.populate()

        if use_names and not self.has_names:
            raise ValueError

        values = (
            self._get_namespace_name_to_encoding(desc='writing names')
            if use_names else
            self._get_namespace_identifier_to_encoding(desc='writing identifiers')
        )

        write_namespace(
            namespace_name=self._get_namespace_name(),
            namespace_keyword=self._get_namespace_keyword(),
            namespace_query_url=self.identifiers_url,
            values=values,
            file=file,
        )

    def write_bel_annotation(self, file: TextIO) -> None:
        """Write as a BEL annotation file."""
        if not self.is_populated():
            self.populate()

        values = self._get_namespace_name_to_encoding(desc='writing names')

        write_annotation(
            keyword=self._get_namespace_keyword(),
            citation_name=self._get_namespace_name(),
            description='',
            values=values,
            file=file,
        )

    def write_bel_namespace_mappings(self, file: TextIO, **kwargs) -> None:
        """Write a BEL namespace mapping file."""
        json.dump(self._get_namespace_identifier_to_name(**kwargs), file, indent=2, sort_keys=True)

    def write_directory(self, directory: str) -> bool:
        """Write a BEL namespace for identifiers, names, name hash, and mappings to the given directory."""
        current_md5_hash = self.get_namespace_hash()
        md5_hash_path = os.path.join(directory, f'{self.module_name}.belns.md5')

        if not os.path.exists(md5_hash_path):
            old_md5_hash = None
        else:
            with open(md5_hash_path) as file:
                old_md5_hash = file.read().strip()

        if old_md5_hash == current_md5_hash:
            return False

        with open(md5_hash_path, 'w') as file:
            print(current_md5_hash, file=file)  # noqa:T001

        with open(os.path.join(directory, f'{self.module_name}.belns'), 'w') as file:
            self.write_bel_namespace(file, use_names=False)

        if self.has_names:
            with open(os.path.join(directory, f'{self.module_name}-names.belns'), 'w') as file:
                self.write_bel_namespace(file, use_names=True)

            with open(os.path.join(directory, f'{self.module_name}.belns.mapping'), 'w') as file:
                self.write_bel_namespace_mappings(file, desc='writing mapping')

        return True

    def _get_namespace_name_to_encoding(self, **kwargs) -> Mapping[str, str]:
        return {
            self._get_name(model): self._get_encoding(model)
            for model in self._iterate_namespace_models(**kwargs)
        }

    def _get_namespace_identifier_to_encoding(self, **kwargs) -> Mapping[str, str]:
        return {
            self._get_identifier(model): self._get_encoding(model)
            for model in self._iterate_namespace_models(**kwargs)
        }

    def _get_namespace_identifier_to_name(self, **kwargs) -> Mapping[str, str]:
        return {
            self._get_identifier(model): self._get_name(model)
            for model in self._iterate_namespace_models(**kwargs)
        }

    def get_namespace_hash(self, hash_fn=None) -> str:
        """Get the namespace hash.

        Defaults to MD5.
        """
        if self.has_names:
            items = self._get_namespace_name_to_encoding(desc='getting hash').items()
        else:
            items = self._get_namespace_identifier_to_encoding(desc='getting hash').items()

        return get_namespace_hash(items, hash_function=hash_fn)

    @staticmethod
    def _cli_add_to_bel_namespace(main: click.Group) -> click.Group:
        """Add the export BEL namespace command."""
        return add_cli_to_bel_namespace(main)

    @staticmethod
    def _cli_add_clear_bel_namespace(main: click.Group) -> click.Group:
        """Add the clear BEL namespace command."""
        return add_cli_clear_bel_namespace(main)

    @staticmethod
    def _cli_add_write_bel_namespace(main: click.Group) -> click.Group:
        """Add the write BEL namespace command."""
        return add_cli_write_bel_namespace(main)

    @staticmethod
    def _cli_add_write_bel_annotation(main: click.Group) -> click.Group:
        """Add the write BEL namespace command."""
        return add_cli_write_bel_annotation(main)

    @classmethod
    def get_cli(cls) -> click.Group:
        """Get a :mod:`click` main function with added BEL namespace commands."""
        main = super().get_cli()

        if cls.is_namespace:
            @main.group()
            def belns():
                """Manage BEL namespace."""

            cls._cli_add_to_bel_namespace(belns)
            cls._cli_add_clear_bel_namespace(belns)
            cls._cli_add_write_bel_namespace(belns)

        if cls.is_annotation:
            @main.group()
            def belanno():
                """Manage BEL annotation."""

            cls._cli_add_write_bel_annotation(belanno)

        return main


def add_cli_to_bel_namespace(main: click.Group) -> click.Group:  # noqa: D202
    """Add a ``upload_bel_namespace`` command to main :mod:`click` function."""

    @main.command()
    @click.option('-u', '--update', is_flag=True)
    @click.pass_obj
    def upload(manager: BELNamespaceManagerMixin, update):
        """Upload names/identifiers to terminology store."""
        namespace = manager.upload_bel_namespace(update=update)
        click.echo(f'uploaded [{namespace.id}] {namespace.keyword}')

    return main


def add_cli_clear_bel_namespace(main: click.Group) -> click.Group:  # noqa: D202
    """Add a ``clear_bel_namespace`` command to main :mod:`click` function."""

    @main.command()
    @click.pass_obj
    def drop(manager: BELNamespaceManagerMixin):
        """Clear names/identifiers to terminology store."""
        namespace = manager.drop_bel_namespace()
        if namespace:
            click.echo(f'namespace {namespace} was cleared')

    return main


def add_cli_write_bel_namespace(main: click.Group) -> click.Group:  # noqa: D202
    """Add a ``write_bel_namespace`` command to main :mod:`click` function."""

    @main.command()
    @directory_option
    @click.pass_obj
    def write(manager: BELNamespaceManagerMixin, directory: str):
        """Write a BEL namespace names/identifiers to terminology store."""
        manager.write_directory(directory)

    return main


def add_cli_write_bel_annotation(main: click.Group) -> click.Group:  # noqa: D202
    """Add a ``write_bel_annotation`` command to main :mod:`click` function."""

    @main.command()
    @directory_option
    @click.pass_obj
    def write(manager: BELNamespaceManagerMixin, directory: str):
        """Write a BEL annotation."""
        with open(os.path.join(directory, manager.identifiers_namespace), 'w') as file:
            manager.write_bel_annotation(file)

    return main
