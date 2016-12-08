# encoding: utf-8
""" Script to rest the SMS settings by sending a message. """
from __future__ import print_function

import sys
import os.path
import logging
import argparse
import pofh

# Configure some simple logging to get all log messages
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('pofh.test_sms')
# DO NOT alter logging facilities:
os.environ[pofh.LOG_CONFIG_ENVIRON_NAME] = 'disabled'

# Attach SMS events to our own logger
def _log_sms_pre(sender, **args):
    logger.info(
        "SMS: Sending message to '{raw_number!s}'".format(**args))

def _log_sms_filtered(sender, **args):
    logger.info(
        ("SMS: Invalid or non-whitelisted number "
         "'{raw_number!s}'").format(**args))

def _log_sms_error(sender, **args):
    logger.info(
        ("SMS: Sending to '{raw_number!s}' "
         "failed: {error!s}").format(**args))

def _log_sms_sent(sender, **args):
    logger.info(
        "SMS: Sent message to '{raw_number!s}'".format(**args))


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Send SMS message with a given pofh configuration")
    parser.add_argument('-d', '--dryrun', action='store_true', default=False,
                        help="Show settings, but don't send SMS.")
    parser.add_argument('-c', '--config',
                        default=os.path.join(sys.prefix, 'etc', 'pofh.cfg'),
                        help="default: %(default)s")
    parser.add_argument('number')
    parser.add_argument('message')
    args = parser.parse_args()

    app = pofh.wsgi.create(config=args.config)

    with app.app_context():
        d = pofh.sms._dispatcher
        print("Dispatcher: {!s}".format(type(d)))

        d.signal_sms_pre.connect(_log_sms_pre)
        d.signal_sms_filtered.connect(_log_sms_filtered)
        d.signal_sms_error.connect(_log_sms_error)
        d.signal_sms_sent.connect(_log_sms_sent)

        print("SMS settings:")
        for k in app.config:
            if k.startswith('SMS_'):
                print("  {!s}: {!s}".format(k, app.config[k]))

        if args.dryrun:
            print("Dryrun, would send '{!s}' to '{!s}'".format(args.message,
                                                               d.parse(args.number)))
        else:
            res = pofh.sms.send_sms(args.number, args.message)
            print("Send result: {!r}".format(res))


if __name__ == '__main__':
    main()
