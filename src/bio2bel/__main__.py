# -*- coding: utf-8 -*-

"""This module runs the command line interface for Bio2BEL."""

import logging

from .cli import main

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
