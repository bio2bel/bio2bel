# -*- coding: utf-8 -*-

"""Aggregate CLI for all Bio2BEL projects"""

import importlib
import logging

import click

from . import entries

log = logging.getLogger(__name__)

modules = {}

for entry in entries:
    try:
        modules[entry] = importlib.import_module('bio2bel_{}'.format(entry)).cli
    except:
        log.warning('%s has no CLI', entry)

commands = {
    entry: mod.main
    for entry, mod in modules.items()
}

main = click.Group(commands=commands)


@main.group()
def util():
    """Run all commands"""


@util.command()
@click.pass_context
def deploy(ctx):
    """Runs all deploy commands"""
    for name, mod in modules.items():
        try:
            click.echo('Deploying {}'.format(name))
            mod.deploy.invoke(ctx)
        except:
            click.echo('No deploy function found for {}'.format(name))


if __name__ == '__main__':
    main()
