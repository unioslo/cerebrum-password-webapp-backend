# encoding: utf-8
""" pofh flask server. """
from __future__ import print_function, unicode_literals

import argparse
from pofh import wsgi


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', default=5000, type=int)
    parser.add_argument('--show-config', default=False, action='store_true')
    args = parser.parse_args(args)

    if args.show_config:
        for setting in sorted(wsgi.app.config):
            print("{!s}: {!r}".format(setting, wsgi.app.config[setting]))
        raise SystemExit()

    wsgi.app.run(host=args.host, port=args.port)


if __name__ == '__main__':
    main()
