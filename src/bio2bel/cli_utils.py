# -*- coding: utf-8 -*-

import logging
import sys

import click

__all__ = ['build_cli']

log = logging.getLogger(__name__)


def add_management_to_cli(main):
    """Adds populate and drop functions to main click function

    :param main: A click-decorated main function
    """

    @main.command()
    @click.pass_obj
    def populate(manager):
        """Populates the database"""
        manager.populate()

    @main.command()
    @click.option('-y', '--yes', is_flag=True)
    @click.pass_obj
    def drop(manager, yes):
        """Drops database"""
        if yes or click.confirm('Drop everything?'):
            manager.drop_all()


def build_cli(manager_cls):
    """Builds a :mod:`click` CLI main function.

    :param Type[AbstractManager] manager_cls: A Manager class
    :return: The main function for click
    """

    @click.group(help='Default connection at {}'.format(manager_cls.module_name, manager_cls.get_connection()))
    @click.option('-c', '--connection', help='Defaults to {}'.format(manager_cls.get_connection()))
    @click.pass_context
    def main(ctx, connection):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        logging.getLogger('bio2bel.utils').setLevel(logging.WARNING)
        ctx.obj = manager_cls(connection=connection)

    add_management_to_cli(main)

    if hasattr(manager_cls, 'flask_admin_models') and manager_cls.flask_admin_models:
        @main.command()
        @click.option('-v', '--debug', is_flag=True)
        @click.option('-p', '--port')
        @click.option('-h', '--host')
        @click.pass_obj
        def web(manager, debug, port, host):
            """Run the web app"""
            app = manager.get_flask_admin_app(url='/')
            app.run(debug=debug, host=host, port=port)

    if hasattr(manager_cls, 'to_bel'):
        @main.command()
        @click.option('-o', '--output', type=click.File('w'), default=sys.stdout)
        @click.pass_obj
        def to_bel(manager, output):
            """Writes BEL Script"""
            from pybel import to_bel
            graph = manager.to_bel()
            to_bel(graph, output)

        @main.command()
        @click.option('-c', '--connection')
        @click.pass_obj
        def upload_bel(manager, connection):
            """Uploads BEL to network store"""
            from pybel import to_database
            graph = manager.to_bel()
            to_database(graph, connection=connection)

    if hasattr(manager_cls, 'summarize'):
        @main.command()
        @click.pass_obj
        def summarize(manager):
            """Summarizes the contents of the database"""
            for name, count in sorted(manager.summarize().items()):
                click.echo('{}: {}'.format(name.capitalize(), count))

    return main
