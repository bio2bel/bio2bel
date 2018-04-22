# -*- coding: utf-8 -*-

"""Aggregate CLI for all Bio2BEL projects."""

import importlib
import logging
import sys
import time

import click
from pkg_resources import VersionConflict, iter_entry_points

from .constants import DEFAULT_CACHE_CONNECTION
from .models import Action

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

cli_modules = {}
main_commands = {}
deploy_commands = {}
populate_commands = {}
drop_commands = {}
web_commands = {}

for entry_point in iter_entry_points(group='bio2bel', name=None):
    entry = entry_point.name

    try:
        bio2bel_module = entry_point.load()
    except VersionConflict:
        log.warning('Version conflict in %s', entry)
        continue
    except Exception:
        log.warning('Issue with importing module %s', entry)
        continue

    try:
        cli_modules[entry] = bio2bel_module.cli
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

main = click.Group(commands=main_commands)
main.help = "Bio2BEL Command Line Utilities on {}".format(sys.executable)


@main.command(help='Populate: {}'.format(', '.join(sorted(populate_commands))))
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
@click.pass_context
def populate(ctx, skip):
    """Run all populate commands."""
    skip = set(ctx.params.pop('skip')) if 'skip' in ctx.params else set()

    for idx, (name, command) in enumerate(sorted(populate_commands.items()), start=1):
        if name in skip:
            click.echo('skipping {}'.format(name))
            continue

        click.echo('{} [{}/{}] populating {}'.format(time.strftime('%H:%M'), idx, len(populate_commands), name))

        try:
            command.invoke(ctx)
        except Exception:
            log.exception('error during population of %s', name)
            continue

        click.echo('{} finished populating {}'.format(time.strftime('%H:%M'), name))


@main.command(help='Drop: {}'.format(', '.join(sorted(drop_commands))))
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
@click.pass_context
def drop(ctx, skip):
    """Run all drop commands."""
    skip = set(ctx.params.pop('skip')) if 'skip' in ctx.params else set()

    for name, command in sorted(drop_commands.items()):
        if name in skip:
            click.echo('skipping {}'.format(name))
            continue

        click.echo('dropping {}'.format(name))
        command.invoke(ctx)


@main.command(help='Deploy: {}'.format(', '.join(sorted(deploy_commands))))
@click.option('-s', '--skip', multiple=True, help='Modules to skip. Can specify multiple.')
@click.pass_context
def deploy(ctx, skip):
    """Run all deploy commands."""
    skip = set(ctx.params.pop('skip')) if 'skip' in ctx.params else set()

    for name, command in sorted(deploy_commands.items()):
        if name in skip:
            click.echo('skipping {}'.format(name))
            continue

        click.echo('deploying {}'.format(name))
        command.invoke(ctx)


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
