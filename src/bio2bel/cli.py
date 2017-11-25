# -*- coding: utf-8 -*-

"""Aggregate CLI for all Bio2BEL projects"""

import importlib
import logging
import sys

import click
from pkg_resources import VersionConflict, iter_entry_points

from .constants import DEFAULT_CACHE_CONNECTION

log = logging.getLogger(__name__)

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


@main.group()
def util():
    """Run all commands"""


@util.command(help='Populate: {}'.format(', '.join(sorted(populate_commands))))
@click.pass_context
def populate(ctx):
    """Runs all populate commands"""
    for name, command in populate_commands.items():
        click.echo('populating {}'.format(name))
        command.invoke(ctx)


@util.command(help='Drop: {}'.format(', '.join(sorted(drop_commands))))
@click.pass_context
def drop(ctx):
    """Runs all drop commands"""
    for name, command in drop_commands.items():
        click.echo('dropping {}'.format(name))
        command.invoke(ctx)


@util.command(help='Deploy: {}'.format(', '.join(sorted(deploy_commands))))
@click.pass_context
def deploy(ctx, connection):
    """Runs all deploy commands"""
    for name, command in deploy_commands.items():
        click.echo('deploying {}'.format(name))
        command.invoke(ctx)


@util.command()
@click.option('-c', '--connection', help='Defaults to {}'.format(DEFAULT_CACHE_CONNECTION))
def web(connection):
    """Runs a combine web interface"""
    from bio2bel.web.application import create_application
    app = create_application(connection=connection)
    app.run(host='0.0.0.0', port=5000)


@util.command()
def web_registered():
    """Prints the registered web services"""
    from bio2bel.web.application import web_modules, add_admins
    click.echo('Web Modules:')
    for m in sorted(web_modules):
        click.echo(m)

    click.echo('Web Admin Interfaces:')
    for m, f in sorted(add_admins.items()):
        click.echo('{} - {}'.format(m, f))


if __name__ == '__main__':
    main()
