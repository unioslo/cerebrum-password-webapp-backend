#!/usr/bin/env python
# coding: utf-8
""" Setup file for pofh. """
from __future__ import print_function

import re
import sys
import os
from setuptools import setup
from setuptools import find_packages
from setuptools.command.test import test as TestCommand


HERE = os.path.dirname(__file__)

PACKAGE_NAME = 'pofh'
PACKAGE_DESC = 'A generic web app to change password'
PACKAGE_AUTHOR = 'UIO/LOS/USIT/UAV/INT'
PACKAGE_URL = ('https://bitbucket.usit.uio.no'
               '/projects/CRB/repos/cerebrum-password-webapp-backend')


def get_version_number():
    """ Get the current module version. """
    # TODO: What should be the authoritative source of version numbers?
    find_version = re.compile(
        r"""__version__\s*=\s*[ubr]*(?:"([.0-9]+)"|'([.0-9]+)')""",
        re.IGNORECASE)
    try:
        with open(os.path.join(HERE, 'pofh', '__init__.py')) as init:
            for line in init.readlines():
                result = find_version.search(line)
                if result:
                    return result.group(1) or result.group(2)
    except Exception:
        # TODO: Maybe don't catch this error?
        pass
    return '0.0.0'


def get_requirements(filename):
    """ Read requirements from file. """
    with open(filename, 'r') as reqfile:
        for req_line in reqfile.readlines():
            req_line = req_line.strip()
            if req_line:
                yield req_line


def get_packages():
    """ List of (sub)packages to install. """
    return find_packages('.', include=('pofh', 'pofh.*'))


class Tox(TestCommand, object):
    """ Run tests using Tox.

    From `https://tox.readthedocs.io/en/latest/example/basic.html`

    """

    user_options = [('tox-args=', 'a', "Arguments to pass to tox")]

    def initialize_options(self):
        """ parse args. """
        super(Tox, self).initialize_options()
        self.tox_args = None

    def finalize_options(self):
        """ setup tests. """
        super(Tox, self).finalize_options()
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        """ Run tests. """
        import tox
        import shlex
        args = self.tox_args
        if args:
            args = shlex.split(self.tox_args)
        tox.cmdline(args=args)


def setup_package():
    """ build and run setup. """

    setup(
        name=PACKAGE_NAME,
        description=PACKAGE_DESC,
        author=PACKAGE_AUTHOR,
        url=PACKAGE_URL,

        setup_requires=['sphinx', 'sphinxcontrib-httpdomain', ] + list(get_requirements('requirements.txt')),
        version=get_version_number(),
        packages=get_packages(),

        install_requires=list(
            get_requirements('requirements.txt')),
        tests_require=list(
            get_requirements('test-requirements.txt')),

        entry_points={
            'console_scripts': [
                'pofhd = pofh.__main__:main'
            ]
        },

        cmdclass={
            'test': Tox
        },
    )


if __name__ == "__main__":
    print("pofh version: {!s}".format(get_version_number()))
    print("packages: {!r}".format(get_packages()))
    print("")
    setup_package()
