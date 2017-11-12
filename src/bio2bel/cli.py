# -*- coding: utf-8 -*-

"""Aggregate CLI for all Bio2BEL projects"""

import importlib
import logging

import click

from . import entries

log = logging.getLogger(__name__)

modules = {}
commands = {}
deploy_commands = {}
populate_commands = {}
web_commands = {}

for entry in entries:
    try:  # TODO can be replaced by entry_point.resolve()
        bio2bel_module = importlib.import_module('bio2bel_{}'.format(entry))
    except ImportError:
        log.exception("can't import bio2bel_%s", entry)
        continue

    try:
        modules[entry] = importlib.import_module('bio2bel_{}.cli'.format(entry))
    except ImportError:
        log.warning('no submodule bio2bel_%s.cli', entry)
        continue

    try:
        commands[entry] = modules[entry].main
    except NameError:
        log.warning('no command group bio2bel_%s.cli:main', entry)
        continue

    try:
        deploy_commands[entry] = modules[entry].deploy
    except AttributeError:
        log.debug('no command bio2bel_%s.cli:deploy', entry)

    try:
        populate_commands[entry] = modules[entry].populate
    except AttributeError:
        log.debug('no command bio2bel_%s.cli:populate', entry)

    try:
        web_commands[entry] = modules[entry].web
    except AttributeError:
        log.debug('no command bio2bel_%s.cli:web', entry)

main = click.Group(commands=commands)


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
