# encoding: utf-8
""" pofh flask server. """
from __future__ import print_function

import argparse
from pofh import __VERSION__ as VERSION
from pofh import wsgi


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

    conf_parser = commands.add_parser("show-config")
    conf_parser.set_defaults(command=show_config)

    route_parser = commands.add_parser("show-routes")
    route_parser.set_defaults(command=show_routes)

    args = parser.parse_args(args)

    args.command(wsgi.app, args)
    raise SystemExit()


if __name__ == '__main__':
    main()
