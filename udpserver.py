#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
"""
File: udpserver.py
Description: Run UDP server for someone running udpping to 'ping'.

Author: Chris Pedro
Copyright: (c) Chris Pedro 2022'
Licence: MIT
Version: 0.2.0
"""


import argparse
import sys

from signal import signal, SIGABRT, SIGINT, SIGTERM
from net import udp, utils


def parse_args(args):
    """Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description='Python UDP Server')
    parser.add_argument(
        '-a', '--address', default='', help='listen on this address')
    parser.add_argument(
        '-p', '--port', default=5001, type=utils.check_positive_int,
        help='listen on this port')
    parser.add_argument(
        '-l', '--loss-rate', default=0, type=utils.check_positive_int,
        help='simulate packet loss at this rate')
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='verbose output')
    return parser.parse_args(args)


def main(args):
    """Main method.
    """
    args = parse_args(args)
    udp.listen_and_reply(
        args.address, args.port, loss=args.loss_rate, verbose=args.verbose)


def cleanup(signal_received, frame):
    """Signal handler. Allows signals to interrupt cleanly.
    """
    sys.exit(0)


if __name__ == '__main__':
    for sig in (SIGABRT, SIGINT, SIGTERM):
        signal(sig, cleanup)
    sys.exit(main(sys.argv[1:]))
