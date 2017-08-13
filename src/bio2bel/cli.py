# -*- coding: utf-8 -*-

"""Aggregate CLI for all Bio2BEL projects"""

import importlib

import click

from . import entries

modules = {
    entry: importlib.import_module('bio2bel_{}'.format(entry)).cli
    for entry in entries
}

commands = {
    entry: module.main
    for entry, module in modules.items()
}

main = click.Group(commands=commands)


@main.group()
def util():
    """Run all commands"""


@util.command()
@click.pass_context
def deploy(ctx):
    """Runs all deploy commands"""
    for name, module in modules.items():
        click.echo('Deploying {}'.format(name))
        module.deploy.invoke(ctx)


if __name__ == '__main__':
    main()
