# -*- coding: utf-8 -*-

"""Aggregate CLI for all Bio2BEL projects."""

import importlib
import logging
import sys

import click
from pkg_resources import VersionConflict, iter_entry_points

from .constants import DEFAULT_CACHE_CONNECTION
from .models import Action
from .utils import get_version

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

modules = {}
cli_modules = {}
main_commands = {}
deploy_commands = {}
populate_commands = {}
drop_commands = {}
web_commands = {}
summarize_commands = {}

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

    try:
        deploy_commands[entry] = cli_modules[entry].deploy
    except AttributeError:
        log.debug('no command bio2bel_%s.cli:deploy', entry)

    try:
        populate_commands[entry] = cli_modules[entry].populate
    except AttributeError:
        log.debug('no command bio2bel_%s.cli:populate', entry)

    try:
        drop_commands[entry] = cli_modules[entry].drop
    except AttributeError:
        log.debug('no command bio2bel_%s.cli:drop', entry)

    try:
        web_commands[entry] = cli_modules[entry].web
    except AttributeError:
        log.debug('no command bio2bel_%s.cli:web', entry)

    try:
        summarize_commands[entry] = cli_modules[entry].summarize
    except AttributeError:
        log.debug('no command bio2bel_%s.cli:summarize', entry)

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

@main.command(help='Populate: {}'.format(', '.join(sorted(populate_commands))))
@click.option('-c', '--connection', help='Defaults to {}'.format(DEFAULT_CACHE_CONNECTION))
@click.option('--reset', is_flag=True, help='Nuke database first')
@click.option('--force', is_flag=True, help='Force overwrite if already populated')
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
def populate(connection, reset, force, skip):
    """Run all populate commands."""
    lm, manager_list = _iterate_managers(connection, skip)

    for idx, name, manager in manager_list:
        click.echo(
            click.style('[{}/{}] '.format(idx, lm, name), fg='blue', bold=True) +
            click.style('populating {}'.format(name), fg='cyan', bold=True))

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
        except:
            log.exception('%s population failed', name)
            click.echo(click.style('👎 {} population failed'.format(name), fg='red', bold=True))



@main.command(help='Drop: {}'.format(', '.join(sorted(drop_commands))))
@click.option('-c', '--connection', help='Defaults to {}'.format(DEFAULT_CACHE_CONNECTION))
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
def drop(connection, skip):
    """Run all drop commands."""
    for idx, name, manager in _iterate_managers(connection, skip):
        click.echo(click.style('dropping {}'.format(name), fg='cyan', bold=True))
        manager.drop_all()


@main.command()
@click.option('-c', '--connection', help='Defaults to {}'.format(DEFAULT_CACHE_CONNECTION))
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
def summarize(connection, skip):
    """Run all summarize commands."""
    for idx, name, manager in _iterate_managers(connection, skip):
        click.echo(click.style(name, fg='cyan', bold=True))
        if not manager.is_populated():
            click.echo('unpopulated {}'.format(name))
        else:
            for field_name, count in sorted(manager.summarize().items()):
                click.echo('{}: {}'.format(field_name.capitalize(), count))


@main.command()
@click.option('-c', '--connection', help='Defaults to {}'.format(DEFAULT_CACHE_CONNECTION))
def web(connection):
    """Run a combine web interface."""
    from bio2bel.web.application import create_application
    app = create_application(connection=connection)
    app.run(host='0.0.0.0', port=5000)


@main.command()
def web_registered():
    """Print the registered web services."""
    from bio2bel.web.application import web_modules, add_admins
    click.echo('Web Modules:')
    for manager_name in sorted(web_modules):
        click.echo(manager_name)

    click.echo('Web Admin Interfaces:')
    for manager_name, add_admin in sorted(add_admins.items()):
        click.echo('{} - {}'.format(manager_name, add_admin))


@main.command()
def actions():
    """List actions."""
    for action in Action.ls():
        click.echo('{} {} {}'.format(action.created, action.action, action.resource))


if __name__ == '__main__':
    main()
