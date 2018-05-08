# -*- coding: utf-8 -*-

"""Testing constants and utilities for Bio2BEL."""

import logging

from click.testing import CliRunner

import pybel
from bio2bel.namespacemanagermixin import Bio2BELMissingNamespaceModelError, NamespaceManagerMixin
from bio2bel.testing import AbstractTemporaryCacheMethodMixin, MockConnectionMixin, TemporaryConnectionMethodMixin
from pybel.manager.models import Base as PyBELBase, Namespace, NamespaceEntry
from tests.constants import Manager, Model, NUMBER_TEST_MODELS, TEST_MODEL_ID_FORMAT, TEST_MODEL_NAME_FORMAT

log = logging.getLogger(__name__)


class NamespaceManager(Manager, NamespaceManagerMixin):
    """Use parts of the test manager and finish the abstract namespace manager"""

    namespace_model = Model

    # automate by defining identifier column?

    def _create_namespace_entry_from_model(self, model, namespace=None):
        return NamespaceEntry(name=model.name, identifier=model.model_id, namespace=namespace)

    def _get_identifier(self, model):
        return model.model_id


class TestFailure(TemporaryConnectionMethodMixin):

    def test_type_failure(self):
        class _TestManager(Manager, NamespaceManagerMixin):
            def _create_namespace_entry_from_model(self, model, namespace=None):
                return NamespaceEntry(name=model.name, identifier=model.model_id, namespace=namespace)

            def _get_identifier(self, model):
                return model.model_id

        with self.assertRaises(Bio2BELMissingNamespaceModelError):
            _TestManager(connection=self.connection)

    def test_instantiation_failure(self):
        class _TestManager(Manager, NamespaceManagerMixin):
            """Use parts of the test manager and finish the abstract namespace manager"""

            namespace_model = Model

        with self.assertRaises(TypeError):
            _TestManager(connection=self.connection)


class TestNamespaceManagerMixin(TemporaryConnectionMethodMixin):
    def test_instantiation_success(self):
        """Test instantiation is possible."""
        NamespaceManager(connection=self.connection)


class TestAwesome(AbstractTemporaryCacheMethodMixin):
    Manager = NamespaceManager

    def setUp(self):
        super().setUp()
        PyBELBase.metadata.create_all(self.manager.engine, checkfirst=True)

    def populate(self):
        self.manager.populate()

    def test_namespace_name(self):
        self.assertEqual('test', self.manager.module_name)  # this is defined in the tests
        self.assertEqual('_TEST', self.manager._get_namespace_keyword())

    def test_make_namespace(self):
        namespace = self.manager._make_namespace()
        self.assertIsNotNone(namespace)
        self.assertIsInstance(namespace, Namespace)
        self.assertEqual('_TEST', namespace.keyword)
        self.assertEqual('_TEST', namespace.url)

        self.assertEqual(NUMBER_TEST_MODELS, namespace.entries.count())

        em = {
            entry.identifier: entry
            for entry in namespace.entries
        }

        for i in range(NUMBER_TEST_MODELS):
            model_id = TEST_MODEL_ID_FORMAT.format(i)

            self.assertIn(model_id, em)
            model = em[model_id]

            self.assertEqual(model_id, model.identifier)
            self.assertEqual(TEST_MODEL_NAME_FORMAT.format(i), model.name)
            self.assertEqual(namespace, model.namespace)

    def test_update_namespace(self):
        self.manager._make_namespace()

        # mock some sort of changes to the database

        _number_to_add = 4

        models = [
            Model.from_id(model_id)
            for model_id in range(NUMBER_TEST_MODELS + 1, NUMBER_TEST_MODELS + 1 + _number_to_add)
        ]
        self.manager.session.add_all(models)
        self.manager.session.commit()

        namespace = self.manager._update_namespace()

        self.assertIsNotNone(namespace)
        self.assertIsInstance(namespace, Namespace)
        self.assertEqual(NUMBER_TEST_MODELS + _number_to_add, namespace.entries.count())


class TestCli(MockConnectionMixin):
    """Tests the CLI for uploading a BEL namespace."""

    def setUp(self):
        """Set up a CliRunner and an accompanying CLI for each test."""
        self.runner = CliRunner()
        self.main = NamespaceManager.get_cli()
        self.manager = Manager(connection=self.connection)
        self.manager.populate()

    def test_to_bel_namespace(self):
        """Test the population function can be run."""
        self.assertEqual(5, self.manager.count_model(), msg='manager should be populated')

        pybel_manager = pybel.Manager(connection=self.connection)
        self.assertEqual(0, pybel_manager.count_namespaces())

        args = [
            '--connection',
            self.connection,
            'upload_bel_namespace'
        ]
        self.runner.invoke(self.main, args)

        self.assertEqual(1, pybel_manager.count_namespaces())
