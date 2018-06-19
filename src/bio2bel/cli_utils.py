# -*- coding: utf-8 -*-

import logging
import os
import sys

import click

from .utils import get_data_dir

__all__ = [
    'add_cli_populate',
    'add_cli_drop',
    'add_cli_flask',
    'add_cli_summarize',
    'add_cli_to_bel',
    'add_cli_to_bel_namespace',
    'add_cli_clear_bel_namespace',
    'add_cli_cache',
]
log = logging.getLogger(__name__)


def add_cli_populate(main):
    """Add a ``populate`` command to main :mod:`click` function.

    :param main: A click-decorated main function
    """

    @main.command()
    @click.option('--reset', is_flag=True, help='Nuke database first')
    @click.option('--force', is_flag=True, help='Force overwrite if already populated')
    @click.pass_obj
    def populate(manager, reset, force):
        """Populates the database"""

        if reset:
            click.echo('Deleting the previous instance of the database')
            manager.drop_all()
            click.echo('Creating new models')
            manager.create_all()

        if manager.is_populated() and not force:
            click.echo('Database already populated. Use --force to overwrite')
            sys.exit(0)

        manager.populate()

    return main


def add_cli_drop(main):
    """Add a ``drop`` command to main :mod:`click` function.

    :param main: A click-decorated main function
    """

    @main.command()
    @click.option('-y', '--yes', is_flag=True)
    @click.pass_obj
    def drop(manager, yes):
        """Drops database"""
        if yes or click.confirm('Drop everything?'):
            manager.drop_all()

    return main


def add_cli_flask(main):
    """Add a ``web`` comand main :mod:`click` function.

    :param main: A click-decorated main function
    """

    @main.command()
    @click.option('-v', '--debug', is_flag=True)
    @click.option('-p', '--port')
    @click.option('-h', '--host')
    @click.option('-k', '--secret-key')
    @click.pass_obj
    def web(manager, debug, port, host, secret_key):
        """Run the web app."""
        app = manager.get_flask_admin_app(url='/', secret_key=secret_key)
        app.run(debug=debug, host=host, port=port)

    return main


def add_cli_to_bel(main):
    """Add several command to main :mod:`click` function related to export to BEL.

    :param main: A click-decorated main function
    """

    @main.command()
    @click.option('-o', '--output', type=click.File('w'), default=sys.stdout)
    @click.pass_obj
    def to_bel(manager, output):
        """Write as BEL Script."""
        from pybel import to_bel
        graph = manager.to_bel()
        to_bel(graph, output)

    @main.command()
    @click.option('-c', '--connection')
    @click.pass_obj
    def upload_bel(manager, connection):
        """Upload BEL to network store."""
        from pybel import to_database
        graph = manager.to_bel()
        to_database(graph, connection=connection)

    return main


def add_cli_to_bel_namespace(main):
    """Add a ``upload_bel_namespace`` command to main :mod:`click` function.

    :param main: A click-decorated main function
    """

    @main.command()
    @click.option('-u', '--update', is_flag=True)
    @click.pass_obj
    def upload_bel_namespace(manager, update):
        """Upload names/identifiers to terminology store."""
        namespace = manager.upload_bel_namespace(update=update)
        click.echo('uploaded [{}] {}'.format(namespace.id, namespace.keyword))

    return main


def add_cli_clear_bel_namespace(main):
    """Add a ``clear_bel_namespace`` command to main :mod:`click` function.

    :param main: A click-decorated main function
    """

    @main.command()
    @click.pass_obj
    def clear_bel_namespace(manager):
        """Clear names/identifiers to terminology store."""
        namespace = manager.clear_bel_namespace()

        if namespace:
            click.echo('namespace {} was cleared'.format(namespace))

    return main


def add_cli_summarize(main):
    """Add a ``summarize`` command to main :mod:`click` function.

    :param main: A click-decorated main function
    """

    @main.command()
    @click.pass_obj
    def summarize(manager):
        """Summarize the contents of the database."""
        for name, count in sorted(manager.summarize().items()):
            click.echo('{}: {}'.format(name.capitalize(), count))

    return main


def add_cli_cache(main):
    """Add several commands to main :mod:`click` function for handling the cache.

    :param main: A click-decorated main function
    """

    @main.group()
    def cache():
        """Manage cached data"""

    @cache.command()
    @click.pass_obj
    def ls(manager):
        """Lists files in the cache."""
        data_dir = get_data_dir(manager.module_name)

        for path in os.listdir(data_dir):
            click.echo(path)

    @cache.command()
    @click.pass_obj
    def clear(manager):
        """Clears all files from the cache."""
        data_dir = get_data_dir(manager.module_name)

        for path in os.listdir(data_dir):
            if path in {'config.ini', 'cache.db'}:
                continue
            os.remove(os.path.join(data_dir, path))

    return main
