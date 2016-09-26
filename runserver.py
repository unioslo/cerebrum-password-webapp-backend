# encoding: utf-8
""" TODO. """
from __future__ import print_function, unicode_literals

from pofh import create_app
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
