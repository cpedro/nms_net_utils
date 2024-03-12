#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
"""
File: cmk_ping_probe.py
Description: Check_MK probe that can be used to ping different destinations
    and output in a way that is ingestable with Check_MK plugin.  This is meant
    to be run on a probe server to monitor IP performance to different
    destinations, similar to Cisco's IP SLA.

Author: Chris Pedro
Copyright: (c) Chris Pedro 2024'
Licence: MIT

Requires on command-line parameter, which is a JSON config file.
File Format (Any can be excluded and 'default' values will be used):
{
  "probes": [
    {
      "a": "A",
      "z": "Z",
      "src": "",
      "dest": "9.9.9.9",
      "length": 64,
      "count": 4,
      "timeout": 3000,
      "use_udp": false,
      "udp_port": 5001
    },
    ...
  ]
}
"""

import argparse
import json
import sys

from net import ping
from signal import signal, SIGABRT, SIGINT, SIGTERM


def parse_args(args):
    """Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description='Check_MK Ping Probe Script')
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='verbose output')
    parser.add_argument('config', help='JSON config file to work off.')
    return parser.parse_args(args)


def parse_config(file):
    """Parse config file and load it in for use as a Python object.
    """
    with open(file, 'r') as config:
        config_data = json.load(config)
    return config_data


def set_probe_defaults(probe):
    """Function for setting default values for a probe.
    If any key in the dictionary is not set, it will be set to a 'default'.
    """
    probe.setdefault('a', 'A')
    probe.setdefault('z', 'Z')
    probe.setdefault('src', '')
    probe.setdefault('dest', '9.9.9.9')
    probe.setdefault('length', 64)
    probe.setdefault('count', 4)
    probe.setdefault('timeout', 3000)
    probe.setdefault('use_udp', False)
    probe.setdefault('udp_port', 5001)


def main(args):
    """Main method.
    """
    args = parse_args(args)
    config = parse_config(args.config)
    print('<<<ping_probe>>>>')
    for probe in config['probes']:
        # Avoid any missing probe variables by setting defaults.
        set_probe_defaults(probe)

        (
            _, lost_perc, min_latency, max_latency, avg_latency,
            min_jitter, max_jitter, avg_jitter, mos
        ) = ping.ping(
            probe['src'], probe['dest'], probe['length'], probe['count'],
            probe['timeout'], probe['use_udp'], probe['udp_port'],
            args.verbose)

        ping_type = 'udp' if probe['use_udp'] else 'icmp'
        if lost_perc == 1:
            print('{}_to_{} {} {} {:.4f} NaN NaN NaN NaN NaN NaN NaN'.format(
                probe['a'], probe['z'], probe['dest'], ping_type, lost_perc))
        else:
            print(('{}_to_{} {} {} {:.4f} {:.2f} {:.2f} {:.2f} {:.2f} {:.2f} '
                  '{:.2f} {:.2f}').format(
                probe['a'], probe['z'], probe['dest'], ping_type, lost_perc,
                min_latency, max_latency, avg_latency, min_latency, max_jitter,
                avg_jitter, mos))


def cleanup(signal_received, frame):
    """Signal handler. Allows signals to interrupt cleanly.
    """
    sys.exit(0)


if __name__ == '__main__':
    for sig in (SIGABRT, SIGINT, SIGTERM):
        signal(sig, cleanup)
    sys.exit(main(sys.argv[1:]))

