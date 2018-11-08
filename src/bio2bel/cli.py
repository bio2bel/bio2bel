# -*- coding: utf-8 -*-

"""Aggregate CLI for all Bio2BEL projects."""

import logging
import os
import sys

import click

from .constants import config
from .manager import AbstractManager
from .models import Action, _make_session
from .utils import clear_cache, get_modules, get_version

logger = logging.getLogger(__name__)

MODULES = get_modules()
MANAGERS = {
    name: module.Manager
    for name, module in MODULES.items()
    if hasattr(module, 'Manager')
}

connection_option = click.option(
    '-c',
    '--connection',
    default=config.connection,
    show_default=True,
    help='Database connection string.',
)

main = click.Group(commands={
    name: manager_cls.get_cli()
    for name, manager_cls in MANAGERS.items()
})
main.help = f'Bio2BEL Command Line Utilities on {sys.executable}\nBio2BEL v{get_version()}'


def _iterate_managers(connection, skip):
    """Iterate over instantiated managers."""
    for idx, name, manager_cls in _iterate_manage_classes(skip):
        if name in skip:
            continue

        try:
            manager = manager_cls(connection=connection)
        except TypeError:
            click.secho(f'Could not instantiate {name}', fg='cyan')
        else:
            yield idx, name, manager


def _iterate_manage_classes(skip):
    for idx, (name, manager_cls) in enumerate(sorted(MANAGERS.items()), start=1):
        if name in skip:
            continue
        yield idx, name, manager_cls


@main.command()
@connection_option
@click.option('--reset', is_flag=True, help='Nuke database first')
@click.option('--force', is_flag=True, help='Force overwrite if already populated')
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
def populate(connection, reset, force, skip):
    """Populate all."""
    for idx, name, manager in _iterate_managers(connection, skip):
        click.echo(
            click.style(f'[{idx}/{len(MANAGERS)}] ', fg='blue', bold=True) +
            click.style(f'populating {name}', fg='cyan', bold=True)
        )

        if reset:
            click.echo('deleting the previous instance of the database')
            manager.drop_all()
            click.echo('creating new models')
            manager.create_all()

        elif manager.is_populated() and not force:
            click.echo(f'👍 {name} is already populated. use --force to overwrite', color='red')
            continue

        try:
            manager.populate()
        except Exception:
            logger.exception('%s population failed', name)
            click.secho(f'👎 {name} population failed', fg='red', bold=True)


@main.command(help='Drop all')
@click.confirmation_option('Drop all?')
@connection_option
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
def drop(connection, skip):
    """Drop all."""
    for idx, name, manager in _iterate_managers(connection, skip):
        click.secho(f'dropping {name}', fg='cyan', bold=True)
        manager.drop_all()


@main.group()
def cache():
    """Manage caches."""


@cache.command()
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
def clear(skip):
    """Clear all caches."""
    for name in sorted(MODULES):
        if name in skip:
            continue
        click.secho(f'clearing cache for {name}', fg='cyan', bold=True)
        clear_cache(name)


@main.command()
@connection_option
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
def summarize(connection, skip):
    """Summarize all."""
    for idx, name, manager in _iterate_managers(connection, skip):
        click.secho(name, fg='cyan', bold=True)
        if not manager.is_populated():
            click.echo('👎 unpopulated')
            continue
        for field_name, count in sorted(manager.summarize().items()):
            click.echo(
                click.style('=> ', fg='white', bold=True) +
                '{}: {}'.format(field_name.replace('_', ' ').capitalize(), count)
            )


@main.group()
def belns():
    """Manage BEL namespaces."""


@belns.command()
@connection_option
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
@click.option('-d', '--directory', type=click.Path(file_okay=False, dir_okay=True), default=os.getcwd(),
              help='output directory')
@click.option('-f', '--force', is_flag=True, help='Force re-download and re-population of resources')
def write(connection, skip, directory, force):
    """Write a BEL namespace names/identifiers to terminology store."""
    os.makedirs(directory, exist_ok=True)
    from .manager.namespace_manager import BELNamespaceManagerMixin
    for idx, name, manager in _iterate_managers(connection, skip):
        if not (isinstance(manager, AbstractManager) and isinstance(manager, BELNamespaceManagerMixin)):
            continue
        click.secho(name, fg='cyan', bold=True)
        if force:
            click.echo(f'dropping')
            manager.drop_all()
            click.echo('clearing cache')
            clear_cache(name)
            click.echo('populating')
            manager.populate()

        try:
            _write_one(manager, directory, name)
        except TypeError as e:
            click.secho(f'error with {name}: {e}'.rstrip(), fg='red')


def _write_one(manager, directory, name):
    with open(os.path.join(directory, f'{name}.belns'), 'w') as file:
        manager.write_bel_namespace(file, use_names=False)

    if manager.has_names:
        with open(os.path.join(directory, f'{name}-names.belns'), 'w') as file:
            manager.write_bel_namespace(file, use_names=True)


@main.group()
def bel():
    """Manage BEL."""


@bel.command()  # noqa: F811
@connection_option
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
@click.option('-d', '--directory', type=click.Path(file_okay=False, dir_okay=True), default=os.getcwd(),
              help='output directory')
@click.option('--force', is_flag=True, help='Force overwrite if already exported')
def write(connection, skip, directory, force):
    """Write all as BEL."""
    os.makedirs(directory, exist_ok=True)
    from .manager.bel_manager import BELManagerMixin
    from pybel import to_pickle
    for idx, name, manager in _iterate_managers(connection, skip):
        if not isinstance(manager, BELManagerMixin):
            continue
        click.secho(name, fg='cyan', bold=True)
        path = os.path.join(directory, f'{name}.bel.gpickle')
        if os.path.exists(path) and not force:
            click.echo('👍 already exported')
            continue

        if not manager.is_populated():
            click.echo('👎 unpopulated')
        else:
            graph = manager.to_bel()
            to_pickle(graph, path)


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
        click.echo(f'{action.created} {action.action} {action.resource}')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
