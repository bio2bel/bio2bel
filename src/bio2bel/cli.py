# -*- coding: utf-8 -*-

"""Aggregate CLI for all Bio2BEL projects."""

import importlib
import logging
import os
import sys

import click
from pkg_resources import VersionConflict, iter_entry_points

from .constants import get_global_connection
from .models import Action, _make_session
from .utils import get_version

log = logging.getLogger(__name__)

modules = {}
cli_modules = {}
main_commands = {}

for entry_point in iter_entry_points(group='bio2bel', name=None):
    entry = entry_point.name

    try:
        modules[entry] = entry_point.load()
    except VersionConflict:
        log.exception('Version conflict in %s', entry)
        continue
    except ImportError:
        log.exception('Issue with importing module %s', entry)
        continue

for entry, module in modules.items():
    try:
        cli_modules[entry] = modules[entry].cli
    except AttributeError:
        try:
            cli_modules[entry] = importlib.import_module('bio2bel_{}.cli'.format(entry))
        except ImportError:
            log.warning('no submodule bio2bel_%s.cli', entry)
            continue

    try:
        main_commands[entry] = cli_modules[entry].main
    except NameError:
        log.warning('no command group bio2bel_%s.cli:main', entry)
        continue

connection_option = click.option(
    '-c',
    '--connection',
    default=get_global_connection(),
    show_default=True,
    help='Database connection string.',
)

main = click.Group(commands=main_commands)
main.help = "Bio2BEL Command Line Utilities on {}\nBio2BEL v{}".format(sys.executable, get_version())


def _iterate_managers(connection, skip):
    _modules = sorted(
        (name, module)
        for name, module in modules.items()
        if name not in skip
    )
    return len(_modules), (
        (idx, name, module.Manager(connection=connection))
        for idx, (name, module) in enumerate(_modules, start=1)
    )


@main.command()
@connection_option
@click.option('--reset', is_flag=True, help='Nuke database first')
@click.option('--force', is_flag=True, help='Force overwrite if already populated')
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
def populate(connection, reset, force, skip):
    """Populate all."""
    lm, manager_list = _iterate_managers(connection, skip)

    for idx, name, manager in manager_list:
        click.echo(
            click.style('[{}/{}] '.format(idx, lm, name), fg='blue', bold=True) +
            click.style('populating {}'.format(name), fg='cyan', bold=True)
        )

        if reset:
            click.echo('deleting the previous instance of the database')
            manager.drop_all()
            click.echo('creating new models')
            manager.create_all()

        elif manager.is_populated() and not force:
            click.echo('👍 {} is already populated. use --force to overwrite'.format(name), color='red')
            continue

        try:
            manager.populate()
        except Exception:
            log.exception('%s population failed', name)
            click.echo(click.style('👎 {} population failed'.format(name), fg='red', bold=True))


@main.command(help='Drop all')
@connection_option
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
def drop(connection, skip):
    """Drop all."""
    lm, manager_list = _iterate_managers(connection, skip)
    for idx, name, manager in manager_list:
        click.echo(click.style('dropping {}'.format(name), fg='cyan', bold=True))
        manager.drop_all()


@main.command()
@connection_option
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
def summarize(connection, skip):
    """Summarize all."""
    lm, manager_list = _iterate_managers(connection, skip)
    for idx, name, manager in manager_list:
        click.echo(click.style(name, fg='cyan', bold=True))
        if not manager.is_populated():
            click.echo('👎 unpopulated')
        elif not hasattr(manager, 'summarize'):
            click.echo('👎 summarize function not implemented')
        else:
            for field_name, count in sorted(manager.summarize().items()):
                click.echo(
                    click.style('=> ', fg='white', bold=True) +
                    '{}: {}'.format(field_name.replace('_', ' ').capitalize(), count)
                )


@main.command()
@connection_option
@click.option('-d', '--directory', type=click.Path(), default=os.getcwd(), help='output directory')
@click.option('--force', is_flag=True, help='Force overwrite if already exported')
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
def to_bel(connection, directory, force, skip):
    """Write all as BEL."""
    os.makedirs(directory, exist_ok=True)
    lm, manager_list = _iterate_managers(connection, skip)
    import pybel
    for idx, name, manager in manager_list:
        click.echo(click.style(name, fg='cyan', bold=True))
        path = os.path.join(directory, '{}.bel.gpickle'.format(name))
        if os.path.exists(path) and not force:
            click.echo('👍 already exported')
            continue

        if not manager.is_populated():
            click.echo('👎 unpopulated')
        elif not hasattr(manager, 'to_bel'):
            click.echo('👎 to_bel function not implemented')
        else:
            graph = manager.to_bel()
            pybel.to_pickle(graph, path)


@main.command()
@connection_option
@click.option('--host', default='0.0.0.0')
@click.option('--port', type=int, default=5000)
def web(connection, host, port):
    """Run a combine web interface."""
    from bio2bel.web.application import create_application
    app = create_application(connection=connection)
    app.run(host=host, port=port)


@main.command()
@connection_option
def actions(connection):
    """List all actions."""
    session = _make_session(connection=connection)
    for action in Action.ls(session=session):
        click.echo('{} {} {}'.format(action.created, action.action, action.resource))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
