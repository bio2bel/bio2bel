# -*- coding: utf-8 -*-

"""Aggregate CLI for all Bio2BEL projects"""

import importlib
import logging

import click
from pkg_resources import VersionConflict, iter_entry_points

log = logging.getLogger(__name__)

cli_modules = {}
main_commands = {}
deploy_commands = {}
populate_commands = {}
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
        web_commands[entry] = cli_modules[entry].web
    except AttributeError:
        log.debug('no command bio2bel_%s.cli:web', entry)

main = click.Group(commands=main_commands)


@main.group()
def util():
    """Run all commands"""


@util.command()
@click.pass_context
def populate(ctx):
    """Runs all populate commands"""
    for name, command in populate_commands.items():
        click.echo('populating {}'.format(name))
        command.invoke(ctx)


@util.command()
@click.pass_context
def deploy(ctx):
    """Runs all deploy commands"""
    for name, command in deploy_commands.items():
        click.echo('deploying {}'.format(name))
        command.invoke(ctx)


if __name__ == '__main__':
    main()
