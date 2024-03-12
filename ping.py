#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
"""
File: ping.py
Description: Pure python implementation of ping with some added output
    functionality, mainly for ingestion into Nagios / Check_MK.

Author: Chris Pedro
Copyright: (c) Chris Pedro 2022'
Licence: MIT

Combines code from the below places:
    https://gist.github.com/pklaus/856268 - Only works with Python2
    https://github.com/l4m3rx/python-ping - Has a bit more than needed
"""


import argparse
import sys

from net import ping, utils
from signal import signal, SIGABRT, SIGINT, SIGTERM


def parse_args(args):
    """Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description='Python Ping Implementation')
    parser.add_argument(
        '-c', '--count', default=4, type=utils.check_positive_int,
        help='number of packets to send')
    parser.add_argument(
        '-t', '--timeout', default=3000, type=utils.check_positive_int,
        help='timeout in ms')
    parser.add_argument(
        '-l', '--length', default=64, type=utils.check_positive_int,
        help='Total packet length')
    parser.add_argument('-a', default='A', help='A side name')
    parser.add_argument('-z', default='Z', help='Z side name')
    parser.add_argument('-s', '--source', help='source IP')
    parser.add_argument(
        '-d', '--destination', default='8.8.8.8', help='destination host')
    parser.add_argument(
        '-u', '--udp', action='store_true', help='use UDP instead of ICMP')
    parser.add_argument(
        '-U', '--udp-port', default=5001, type=utils.check_positive_int,
        help='use UDP port, required if UDP is being used (-u)')
    parser.add_argument(
        '-o', '--output', choices=['normal', 'nagios', 'check_mk'],
        default='normal', help='output type')
    parser.add_argument(
        '-p', '--loss-warn', default=10, type=utils.check_positive_float,
        help='packet loss warning threshold')
    parser.add_argument(
        '-P', '--loss-crit', default=20, type=utils.check_positive_float,
        help='packet loss critical threshold')
    parser.add_argument(
        '-r', '--rtt-warn', default=75, type=utils.check_positive_int,
        help='latency RTT warning threshold')
    parser.add_argument(
        '-R', '--rtt-crit', default=100, type=utils.check_positive_int,
        help='latency RTT critical threshold')
    parser.add_argument(
        '-j', '--jitter-warn', default=20, type=utils.check_positive_int,
        help='latency RTT warning threshold')
    parser.add_argument(
        '-J', '--jitter-crit', default=30, type=utils.check_positive_int,
        help='latency RTT critical threshold')
    parser.add_argument(
        '-m', '--mos-warn', default=4, type=utils.check_positive_float,
        help='MOS score warning threshold')
    parser.add_argument(
        '-M', '--mos-crit', default=3, type=utils.check_positive_float,
        help='MOS score critical threshold')
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='verbose output')
    return parser.parse_args(args)


def print_output(args, lost, lost_perc, min_latency, max_latency,
                 avg_latency, min_jitter, max_jitter, avg_jitter, mos):
    """Print output.
    """
    if args.output == 'normal':
        print('{} ping statistics ({} bytes):'.format(
            args.destination, args.length))
        print(' - packet loss: {:.2%} ({}/{})'.format(
            lost_perc, lost, args.count))
        if lost_perc != 1:
            print(' - latency (MIN/MAX/AVG): {:.2f}/{:.2f}/{:.2f}'.format(
                min_latency, max_latency, avg_latency))
            print(' - jitter (MIN/MAX/AVG): {:.2f}/{:.2f}/{:.2f} ms'.format(
                min_jitter, max_jitter, avg_jitter))
            print(' - MOS score: {:.2f}'.format(mos))
    elif args.output == 'check_mk':
        print('<<<nms_net_utils_ping>>>')
        ping_type = 'udp' if args.udp else 'icmp'
        if lost_perc == 1:
            print('{}_to_{} {} {} {:.4f} NaN NaN NaN NaN NaN NaN NaN'.format(
                args.a, args.z, args.destination, ping_type, lost_perc))
        else:
            print(('{}_to_{} {} {} {:.4f} {:.2f} {:.2f} {:.2f} {:.2f} {:.2f} '
                  '{:.2f} {:.2f}').format(
                args.a, args.z, args.destination, ping_type, lost_perc,
                min_latency, max_latency, avg_latency, min_latency, max_jitter,
                avg_jitter, mos))
    elif args.output == 'nagios':
        # If all packets were lost, just return critical.
        if lost_perc == 1:
            print('2 {}_to_{}_loss lost={:.2f} {} - no reply'.format(
                args.a, args.z, lost_perc, args.destination))
            print('2 {}_to_{}_delay - no reply'.format(args.a, args.z))
            print('2 {}_to_{}_jitter - no reply'.format(args.a, args.z))
            print('2 {}_to_{}_mos - no reply'.format(args.a, args.z))
            sys.exit(2)
        else:
            # Generate status responses.
            if lost_perc >= float(args.loss_crit) / 100:
                loss_status = 2
            elif lost_perc >= float(args.loss_warn) / 100:
                loss_status = 1
            else:
                loss_status = 0

            if avg_latency >= args.rtt_crit:
                latency_status = 2
            elif avg_latency >= args.rtt_warn:
                latency_status = 1
            else:
                latency_status = 0

            if avg_jitter >= args.jitter_crit:
                jitter_status = 2
            elif avg_jitter >= args.jitter_warn:
                jitter_status = 1
            else:
                jitter_status = 0

            if mos <= args.mos_crit:
                mos_status = 2
            elif mos <= args.mos_warn:
                mos_status = 1
            else:
                mos_status = 0

            print(('{} {}_to_{}_loss loss={:.2f};{:.2f};{:.2f};0;100 {} - '
                   '{:.2%} packets lost').format(
                loss_status, args.a, args.z, (lost_perc * 100),
                args.loss_warn, args.loss_crit, args.destination, lost_perc))
            print(('{} {}_to_{}_delay delay={:.2f};{};{};0;{} {} - {:.2f} ms '
                   'delay').format(
                latency_status, args.a, args.z, avg_latency, args.rtt_warn,
                args.rtt_crit, args.timeout, args.destination, avg_latency))
            print(('{} {}_to_{}_jitter jitter={:.5f};{:.5f};{:.5f};0;{} {} - '
                   '{:.2f} ms jitter').format(
                jitter_status, args.a, args.z, (avg_jitter / 1000),
                (args.jitter_warn / 1000), (args.jitter_crit / 1000),
                (args.timeout / 1000), args.destination, avg_jitter))
            print(('{} {}_to_{}_mos mos={:.2f};{:.2f};{:.2f};0.0;5.0 {} - '
                   '{:.2f} mos score').format(
                mos_status, args.a, args.z, mos, args.mos_warn,
                args.mos_crit, args.destination, mos))

            sys.exit(loss_status)


def main(args):
    """Main method.
    """
    args = parse_args(args)

    # Run a single ping.
    (
        lost, lost_perc, min_latency, max_latency, avg_latency,
        min_jitter, max_jitter, avg_jitter, mos
    ) = ping.ping(
        args.source, args.destination, args.length, args.count, args.timeout,
        args.udp, args.udp_port, args.verbose)

    # Print output.
    print_output(
        args, lost, lost_perc, min_latency, max_latency, avg_latency,
        min_jitter, max_jitter, avg_jitter, mos)


def cleanup(signal_received, frame):
    """Signal handler. Allows signals to interrupt cleanly.
    """
    sys.exit(0)


if __name__ == '__main__':
    for sig in (SIGABRT, SIGINT, SIGTERM):
        signal(sig, cleanup)
    sys.exit(main(sys.argv[1:]))

