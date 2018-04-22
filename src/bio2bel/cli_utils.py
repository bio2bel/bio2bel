# -*- coding: utf-8 -*-

import logging
import sys

import click

__all__ = [
    'add_cli_populate',
    'add_cli_drop',
    'add_cli_flask',
    'add_cli_summarize',
    'add_cli_to_bel',
    'add_cli_to_bel_namespace',
]
log = logging.getLogger(__name__)


def add_cli_populate(main):
    """Add a ``populate`` command to main :mod:`click` function.

    :param main: A click-decorated main function
    """

    @main.command()
    @click.option('--reset', is_flag=True)
    @click.pass_obj
    def populate(manager, reset):
        """Populates the database"""

        if reset:
            log.info('Deleting the previous instance of the database')
            manager.drop_all()
            log.info('Creating new models')
            manager.create_all()

        manager.populate()

    return populate


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

    return drop


def add_cli_flask(main):
    """Add a ``web`` comand main :mod:`click` function.

    :param main: A click-decorated main function
    """

    @main.command()
    @click.option('-v', '--debug', is_flag=True)
    @click.option('-p', '--port')
    @click.option('-h', '--host')
    @click.pass_obj
    def web(manager, debug, port, host):
        """Run the web app."""
        app = manager.get_flask_admin_app(url='/')
        app.run(debug=debug, host=host, port=port)

    return web


def add_cli_to_bel(main):
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


def add_cli_to_bel_namespace(main):
    @main.command()
    @click.pass_obj
    def upload_bel_namespace(manager):
        """Upload names/identifiers to terminology store."""
        manager.upload_bel_namespace()


def add_cli_summarize(main):
    @main.command()
    @click.pass_obj
    def summarize(manager):
        """Summarize the contents of the database."""
        for name, count in sorted(manager.summarize().items()):
            click.echo('{}: {}'.format(name.capitalize(), count))
