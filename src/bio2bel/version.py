# -*- coding: utf-8 -*-

"""Version information for Bio2BEL."""

import os
import subprocess  # noqa:S404

__all__ = [
    'VERSION',
    'get_git_hash',
    'get_version',
]

VERSION = '0.4.3-dev'


def get_git_hash() -> str:
    """Get the Bio2BEL git hash."""
    with open(os.devnull, 'w') as devnull:
        try:
            ret = subprocess.check_output(  # noqa: S603,S607
                ['git', 'rev-parse', 'HEAD'],
                cwd=os.path.dirname(__file__),
                stderr=devnull,
            )
        except subprocess.CalledProcessError:
            return 'UNHASHED'
        else:
            return ret.strip().decode('utf-8')[:8]


def get_version(with_git_hash: bool = False):
    """Get the Bio2BEL version string, including a git hash."""
    return f'{VERSION}-{get_git_hash()}' if with_git_hash else VERSION


if __name__ == '__main__':
    print(get_version(with_git_hash=True))  # noqa:T001
