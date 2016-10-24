#!/usr/bin/env python
# coding: utf-8
""" Setup file for pofh. """
from __future__ import print_function

import re
import os
import sys
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


class PyTest(TestCommand, object):
    """ Run tests using pytest.

    From `http://doc.pytest.org/en/latest/goodpractices.html`.

    """

    user_options = [('pytest-args=', 'a', "Arguments to pass to pytest")]

    def initialize_options(self):
        super(PyTest, self).initialize_options()
        self.pytest_args = []

    def run_tests(self):
        import shlex
        import pytest
        args = self.pytest_args
        if args:
            args = shlex.split(args)
        errno = pytest.main(args)
        raise SystemExit(errno)


def setup_package():
    """ build and run setup. """

    setup_requires = []

    # TODO: Is this good enough? Will it catch aliases?
    #       Are there better methods to figure out which command we are about
    #       to run?
    if {'build_sphinx', 'upload_docs'}.intersection(sys.argv):
        # Sphinx modules:
        setup_requires.extend(['sphinx', 'sphinxcontrib-httpdomain'])
        # pofh-dependencies for generating autodoc:
        setup_requires.extend(get_requirements('requirements.txt'))

    setup(
        name=PACKAGE_NAME,
        description=PACKAGE_DESC,
        author=PACKAGE_AUTHOR,
        url=PACKAGE_URL,

        version=get_version_number(),
        packages=get_packages(),

        setup_requires=setup_requires,
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
            'test': PyTest,
            'pytest': PyTest,
            'tox': Tox,
        }
    )


if __name__ == "__main__":
    print("pofh version: {!s}".format(get_version_number()))
    print("packages: {!r}".format(get_packages()))
    print("")
    setup_package()
