# -*- coding: utf-8 -*-

"""Aggregate CLI for all Bio2BEL projects."""

import logging
import os
import sys
from typing import TextIO

import click
from tqdm import tqdm

from .constants import config
from .manager import AbstractManager, get_bio2bel_manager_classes
from .manager.bel_manager import BELManagerMixin
from .manager.namespace_manager import BELNamespaceManagerMixin
from .models import Action, _make_session
from .utils import clear_cache
from .version import get_version

logger = logging.getLogger(__name__)

MANAGERS = get_bio2bel_manager_classes()

connection_option = click.option(
    '-c',
    '--connection',
    default=config.connection,
    show_default=True,
    help='Database connection string.',
)

commands = {}
for name, manager_cls in MANAGERS.items():
    commands[name] = manager_cls.get_cli()
    # can not use single asterick, causes documentation build failure
    commands[name].help = f'# Manage {name}'

main = click.Group(commands=commands)
main.help = f'Bio2BEL Command Line Utilities on {sys.executable}\nBio2BEL v{get_version()}'


def _iterate_managers(connection, skip):
    """Iterate over instantiated managers."""
    for idx, name, manager_cls in _iterate_manage_classes(skip):
        if name in skip:
            continue

        try:
            manager = manager_cls(connection=connection)
        except TypeError as e:
            click.secho(f'Could not instantiate {name}: {e}', fg='red')
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
            click.style(f'populating {name}', fg='cyan', bold=True),
        )

        if reset:
            try:
                click.echo(f'deleting the previous instance of {name}')
                manager.drop_all()
                click.echo(f'creating new models for {name}')
                manager.create_all()
            except AttributeError:
                click.echo(f'no models available for {name}')
                continue

        else:
            try:
                if manager.is_populated() and not force:
                    click.echo(f'👍 {name} is already populated. use --force to overwrite', color='red')
                    continue
            except AttributeError:
                click.echo(f'no population function available for {name}')
                continue

        try:
            manager.populate()
        except (AttributeError, NotImplementedError):
            click.echo(f'no population function available for {name}')
            continue
        except Exception:
            logger.exception('%s population failed', name)
            click.secho(f'👎 {name} population failed', fg='red', bold=True)


@main.command(help='Drop all')
@click.confirmation_option('Drop all?')
@connection_option
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
def drop(connection, skip):
    """Drop all."""
    for _, name, manager in _iterate_managers(connection, skip):
        click.secho(f'dropping {name}', fg='cyan', bold=True)
        manager.drop_all()


@main.group()
def cache():
    """Manage caches."""


@cache.command()
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
def clear(skip):
    """Clear all caches."""
    for name in sorted(MANAGERS):
        if name in skip:
            continue
        click.secho(f'clearing cache for {name}', fg='cyan', bold=True)
        clear_cache(name)


@main.command()
@connection_option
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
def summarize(connection, skip):
    """Summarize all."""
    for _, name, manager in _iterate_managers(connection, skip):
        click.secho(name, fg='cyan', bold=True)
        try:
            if not manager.is_populated():
                click.echo('👎 unpopulated')
                continue
        except (AttributeError, NotImplementedError):
            click.echo('👎 population not implemented')
            continue

        if isinstance(manager, BELNamespaceManagerMixin):
            click.secho(f'Terms: {manager._count_model(manager.namespace_model)}', fg='green')

        if isinstance(manager, BELManagerMixin):
            try:
                click.secho(f'Relations: {manager.count_relations()}', fg='green')
            except TypeError as e:
                click.secho(str(e), fg='red')

        try:
            summary = manager.summarize()
        except (AttributeError, NotImplementedError):
            click.echo('👎 summarize() not implemented')
            continue

        for field_name, count in sorted(summary.items()):
            click.echo(
                click.style('=> ', fg='white', bold=True) + f"{field_name.replace('_', ' ').capitalize()}: {count}",
            )


@main.command()
@connection_option
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
@click.option('-f', '--file', type=click.File('w'), default=sys.stdout)
@click.option('--tablefmt', default="simple", show_default=True)
@click.option('--index', is_flag=True)
def sheet(connection, skip, file: TextIO, tablefmt: str, index: bool):
    """Generate a summary sheet."""
    try:
        from tabulate import tabulate, tabulate_formats
    except ImportError:
        click.echo('Could not import tabulate. Try `pip install tabulate`.')
        return sys.exit(1)

    if tablefmt not in tabulate_formats:
        click.echo(tabulate_formats)

    if index:
        header = ['', 'Name', 'Description', 'Terms', 'Relations']
    else:
        header = ['Name', 'Description', 'Terms', 'Relations']

    rows = []

    for i, (_, name, manager) in enumerate(_iterate_managers(connection, skip), start=1):
        try:
            if not manager.is_populated():
                continue
        except AttributeError:
            click.secho(f'{name} does not implement is_populated', fg='red')
            continue

        terms, relations = None, None
        if isinstance(manager, BELNamespaceManagerMixin):
            terms = manager._count_model(manager.namespace_model)

        if isinstance(manager, BELManagerMixin):
            try:
                relations = manager.count_relations()
            except TypeError as e:
                relations = str(e)
            else:
                if 0 == relations:
                    relations = None

        if not terms and not relations:
            continue

        if index:
            rows.append((i, name, manager.__doc__.split('\n')[0].strip().strip('.'), terms, relations))
        else:
            rows.append((name, manager.__doc__.split('\n')[0].strip().strip('.'), terms, relations))

    click.echo(
        tabulate(
            rows,
            headers=header,
            tablefmt=tablefmt,
        ),
        file=file,
    )


@main.command()
@click.option('-d', '--directory', type=click.Path(dir_okay=True, file_okay=False), default=os.getcwd())
def er(directory):
    """Generate entity-relation diagrams for each package."""
    try:
        import eralchemy
    except ImportError:
        click.echo('Can not import eralchemy. Try `pip install eralchemy`.')
        return sys.exit(1)

    os.makedirs(directory, exist_ok=True)
    it = tqdm(sorted(MANAGERS.items()), leave=False)
    for name, manager_cls in it:
        base = getattr(manager_cls, '_base', None)
        if base is None:
            it.write(f'{name} does not have a SQLAlchemy base')
            continue
        it.write(f'generating for {name}')
        eralchemy.render_er(base, os.path.join(directory, f'{name}_erd.png'))


@main.group()
def belns():
    """Manage BEL namespaces."""


@belns.command(name='write')
@connection_option
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
@click.option('-d', '--directory', type=click.Path(file_okay=False, dir_okay=True), default=os.getcwd(),
              help='output directory')
@click.option('-f', '--force', is_flag=True, help='Force re-download and re-population of resources')
def write_belns(connection, skip, directory, force):
    """Write a BEL namespace names/identifiers to terminology store."""
    os.makedirs(directory, exist_ok=True)
    from .manager.namespace_manager import BELNamespaceManagerMixin
    for _, name, manager in _iterate_managers(connection, skip):
        if not (isinstance(manager, AbstractManager) and isinstance(manager, BELNamespaceManagerMixin)):
            continue
        click.secho(name, fg='cyan', bold=True)
        if force:
            try:
                click.echo('dropping')
                manager.drop_all()
                click.echo('clearing cache')
                clear_cache(name)
                click.echo('populating')
                manager.populate()
            except Exception:
                click.secho(f'{name} failed', fg='red')
                continue

        try:
            r = manager.write_directory(directory)
        except TypeError as e:
            click.secho(f'error with {name}: {e}'.rstrip(), fg='red')
        else:
            if not r:
                click.echo('no update')


@main.group()
def bel():
    """Manage BEL."""


@bel.command(name='write')
@connection_option
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
@click.option('-d', '--directory', type=click.Path(file_okay=False, dir_okay=True), default=os.getcwd(),
              help='output directory')
@click.option('--force', is_flag=True, help='Force overwrite if already exported')
def write_bel(connection, skip, directory, force):
    """Write all as BEL."""
    os.makedirs(directory, exist_ok=True)
    from .manager.bel_manager import BELManagerMixin
    import pybel
    for _, name, manager in _iterate_managers(connection, skip):
        if not isinstance(manager, BELManagerMixin):
            continue
        click.secho(name, fg='cyan', bold=True)
        path = os.path.join(directory, f'{name}.bel.pickle')
        if os.path.exists(path) and not force:
            click.echo('👍 already exported')
            continue

        if not manager.is_populated():
            click.echo('👎 unpopulated')
        else:
            graph = manager.to_bel()
            pybel.to_pickle(graph, path)
            pybel.to_nodelink_gz(graph, os.path.join(directory, f'{name}.bel.nodelink.json.gz'))
            pybel.to_bel_script_gz(graph, os.path.join(directory, f'{name}.bel.gz'))


@main.command()
@connection_option
@click.option('--host')
@click.option('--port', type=int)
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


@main.command()
@click.argument('name')
def install(name):
    """Install the Bio2BEL package."""
    from .io.automate import ensure_bio2bel_installation
    installed, m = ensure_bio2bel_installation(name)
    if installed:
        click.secho(f'{m.__name__} is already installed', fg='green')
    else:
        click.secho(f'{m.__name__} was successfully installed', fg='green')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
