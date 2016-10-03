# encoding: utf-8
""" pofh flask server. """
from __future__ import print_function

import os
import argparse
from pofh import __VERSION__ as VERSION
from pofh import CONFIG_FILE_NAME
from pofh import wsgi


def readable_file_type(path):
    """ Validate and normalize path. """
    abspath = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(abspath):
        raise argparse.ArgumentTypeError("No file {!s}".format(path))
    if not os.path.isfile(abspath):
        raise argparse.ArgumentTypeError("{!s} is not a file".format(path))
    if not os.access(abspath, os.R_OK):
        raise argparse.ArgumentTypeError("Unable to read {!s}".format(path))
    return abspath


def install_config(app, args):
    """ Installs config to instance folder. """
    import time
    import shutil

    if not os.path.isdir(app.instance_path):
        raise IOError(
            "No instance folder ({!s})".format(app.instance_path))
    if not os.access(app.instance_path, os.W_OK | os.X_OK):
        raise IOError(
            "No access to instance folder ({!s})".format(app.instance_path))
    config_file = os.path.join(app.instance_path, CONFIG_FILE_NAME)
    if os.path.exists(config_file) and args.backup:
        backup_name = '{!s}.backup.{!s}'.format(CONFIG_FILE_NAME,
                                                time.strftime("%Y%m%d-%H%M%S"))
        backup_file = os.path.join(app.instance_path, backup_name)
        shutil.move(config_file, backup_file)
        print("Moved '{!s}'\n   to '{!s}'".format(config_file, backup_file))
    shutil.copyfile(args.config, config_file)
    print("Copied '{!s}'\n    to '{!s}'".format(args.config, config_file))


def show_config(app, args):
    """ Print config. """
    print("Settings:")
    for setting in sorted(app.config):
        print("  {!s}: {!r}".format(setting, wsgi.app.config[setting]))


def show_routes(app, args):
    """ Print routing rules. """
    print("Routes:")
    for rule in app.url_map.iter_rules():
        print("  {!r}".format(rule))


def run_app(app, args):
    """ Run Flask server. """
    app.run(host=args.host, port=args.port)


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s version {:s}'.format(VERSION),
        help="show version number and exit")
    parser.add_argument(
        '-c', '--config',
        metavar='FILE',
        default=None,
        type=readable_file_type,
        help="use config from %(metavar)s")

    commands = parser.add_subparsers(help='Valid commands')

    run_parser = commands.add_parser("run")
    run_parser.add_argument(
        '--host',
        metavar='HOST',
        type=str,
        default='127.0.0.1',
        help="bind server to host %(metavar)s (default: %(default)s)")
    run_parser.add_argument(
        '--port',
        metavar='PORT',
        type=int,
        default=5000,
        help="bind server to port %(metavar)s (default: %(default)d)")
    run_parser.set_defaults(command=run_app)

    show_conf_parser = commands.add_parser("show-config")
    show_conf_parser.set_defaults(command=show_config)

    inst_conf_parser = commands.add_parser("install-config")
    inst_conf_parser.add_argument(
        'config',
        metavar='FILE',
        type=readable_file_type,
        help="the config file to install")
    inst_conf_parser.add_argument(
        '--no-backup',
        dest='backup',
        default=True,
        action='store_false',
        help="do not backup any existing config")
    inst_conf_parser.set_defaults(command=install_config)

    route_parser = commands.add_parser("show-routes")
    route_parser.set_defaults(command=show_routes)

    args = parser.parse_args(args)

    args.command(wsgi.create(config=args.config), args)
    raise SystemExit()


if __name__ == '__main__':
    main()
