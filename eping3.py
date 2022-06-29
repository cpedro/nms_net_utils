#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
"""
File: eping3.py
Description: Pure python implementation of ping with some added output
    functionality, mainly for ingestion into Nagios / Check_MK.
Author: Chris Pedro
Date: 2022-06-23

Combines code from the below places:
    https://gist.github.com/pklaus/856268 - Only works with Python2
    https://github.com/l4m3rx/python-ping - Has a bit more than needed
"""


__author__ = 'Chris Pedro'
__copyright__ = '(c) Chris Pedro 2022'
__licence__ = 'MIT'
__version__ = '0.1.0'


import argparse
import sys

from signal import signal, SIGABRT, SIGINT, SIGTERM
from net import icmp, utils


def check_positive_int(value):
    """Check if the given value is an int and positive.
    """
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(
            '{} must be a positive int value'.format(value))
    return ivalue


def check_positive_float(value):
    """Check if the given value is a float and positive.
    """
    ivalue = float(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(
            '{} must be a positive float value'.format(value))
    return ivalue


def parse_args(args):
    """Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description='Python Ping Implementation')
    parser.add_argument(
        '-c', '--count', default=4, type=check_positive_int,
        help='number of packets to send')
    parser.add_argument(
        '-t', '--timeout', default=3000, type=check_positive_int,
        help='timeout in ms')
    parser.add_argument(
        '-l', '--length', default=192, type=check_positive_int,
        help='ICMP payload length')
    parser.add_argument('-a', default='A', help='A side name')
    parser.add_argument('-z', default='Z', help='Z side name')
    parser.add_argument('-s', '--source', help='source IP')
    parser.add_argument( 
        '-d', '--destination', default='8.8.8.8', help='destination host')
    parser.add_argument(
        '-o', '--output', choices=['normal', 'nagios'], default='normal',
        help='output type')
    parser.add_argument(
        '-p', '--loss-warn', default=10, type=check_positive_float,
        help='packet loss warning threshold')
    parser.add_argument(
        '-P', '--loss-crit', default=20, type=check_positive_float,
        help='packet loss critical threshold')
    parser.add_argument(
        '-r', '--rtt-warn', default=75, type=check_positive_int,
        help='latency RTT warning threshold')
    parser.add_argument(
        '-R', '--rtt-crit', default=100, type=check_positive_int,
        help='latency RTT critical threshold')
    parser.add_argument(
        '-j', '--jitter-warn', default=20, type=check_positive_int,
        help='latency RTT warning threshold')
    parser.add_argument(
        '-J', '--jitter-crit', default=30, type=check_positive_int,
        help='latency RTT critical threshold')
    parser.add_argument(
        '-m', '--mos-warn', default=4, type=check_positive_float,
        help='MOS score warning threshold')
    parser.add_argument(
        '-M', '--mos-crit', default=3, type=check_positive_float,
        help='MOS score critical threshold')
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='verbose output')
    return parser.parse_args(args)


def main(args):
    """Main method.
    """
    lost = 0
    latency = []
    jitter = []
    
    args = parse_args(args)

    # Do pings, and collect latencies all other stats will be derived.
    for i in range(0, args.count):
        try:
            delay = icmp.single_ping(
                args.destination, args.timeout, i, args.length,
                src_ip=args.source, verbose=args.verbose)
        except OSError:
            sys.exit(2)

        if delay is None:
            lost += 1
            continue
        latency.append(delay)

        # Skip jitter calculation until we have at least 2 packets returned.
        if len(latency) > 1:
            jitter.append(abs(latency[-1] - latency[-2]))

    # Packet loss percentage
    lost_perc = lost / float(args.count)

    # Calculate min, max and average latency.
    if len(latency) > 0:
        min_latency = min(latency)
        max_latency = max(latency)
        avg_latency = sum(latency) / len(latency)
    else:
        min_latency = 'NaN'
        max_latency = 'NaN'
        avg_latency = 'NaN'

    # Calculate min, max and average jitter
    if len(jitter) > 0:
        min_jitter = min(jitter)
        max_jitter = max(jitter)
        avg_jitter = sum(jitter) / len(jitter)
    else:
        min_jitter = 'NaN'
        max_jitter = 'NaN'
        avg_jitter = 'NaN'

    if len(latency) > 0:
        mos = utils.mos_score(avg_latency, max_jitter, lost_perc)
    else:
        mos = 0

    if args.output == 'normal':
        print('Statistics for {} to {}:'.format(args.a, args.z))
        print(' - packet loss: {}/{} ({:.2%})'.format(
            lost, args.count, lost_perc))
        if len(latency) > 0:
            print(' - latency (MIN/MAX/AVG): {:.2f}/{:.2f}/{:.2f} ms'.format(
                min_latency, max_latency, avg_latency))
            print(' - jitter (MIN/MAX/AVG): {:.2f}/{:.2f}/{:.2f} ms'.format(
                min_jitter, max_jitter, avg_jitter))
            print(' - MOS: {:.1f}'.format(mos))
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
                   '{:.2%} packets lost'.format(loss_status, args.a, args.z,
                                                lost_perc * 100,
                                                args.loss_warn, args.loss_crit,
                                                args.destination, lost_perc)))
            print(('{} {}_to_{}_delay delay={:2f};{};{};0;{} {} - {:.2f} ms '
                   'delay'.format(latency_status, args.a, args.z,
                                  avg_latency, args.rtt_warn, args.rtt_crit,
                                  args.timeout, args.destination,
                                  avg_latency)))
            print(('{} {}_to_{}_jitter jitter={:.6f};{:.6f};{:.6f};0;{} {} - '
                   '{:.2f} ms jitter'.format(jitter_status, args.a, args.z,
                                             (float(avg_jitter) / 1000),
                                             (float(args.jitter_warn) / 1000),
                                             (float(args.jitter_crit) / 1000),
                                             (float(args.timeout) / 1000),
                                             args.destination, avg_jitter)))
            print(('{} {}_to_{}_mos mos={:.1f};{:.1f};{:.1f};0.0;5.0 {} - '
                   '{:.1f} mos score'.format(mos_status, args.a, args.z, mos,
                                             args.mos_warn, args.mos_crit,
                                             args.destination, mos)))
            sys.exit(loss_status)


def cleanup(signal_received, frame):
    """Signal handler. Allows signals to interrupt cleanly.
    """
    sys.exit(0)


if __name__ == '__main__':
    for sig in (SIGABRT, SIGINT, SIGTERM):
        signal(sig, cleanup)
    sys.exit(main(sys.argv[1:]))

