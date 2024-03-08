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

from signal import signal, SIGABRT, SIGINT, SIGTERM
from net import icmp, udp, utils


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


def ping(source, destination, length, count, timeout,
         udp_ping=False, udp_port=5001, verbose=False):
    lost = 0
    latency = []
    jitter = []

    # Do pings, and collect latencies all other stats will be derived.
    for i in range(0, count):
        try:
            if udp_ping and udp_port:
                delay = udp.single_ping(
                    destination, udp_port, timeout, i,
                    length, src_ip=source, verbose=verbose)
            else:
                delay = icmp.single_ping(
                    destination, timeout, i, length,
                    src_ip=source, verbose=verbose)
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
    lost_perc = lost / float(count)

    # Calculate min, max and average latency.
    if len(latency) > 0:
        min_latency = min(latency)
        max_latency = max(latency)
        avg_latency = sum(latency) / len(latency)
    else:
        min_latency = float('nan')
        max_latency = float('nan')
        avg_latency = float('nan')

    # Calculate min, max and average jitter
    if len(jitter) > 0:
        min_jitter = min(jitter)
        max_jitter = max(jitter)
        avg_jitter = sum(jitter) / len(jitter)
    else:
        min_jitter = float('nan')
        max_jitter = float('nan')
        avg_jitter = float('nan')

    if len(latency) > 0:
        mos = utils.mos_score(avg_latency, avg_jitter, (lost_perc * 100))
    else:
        mos = float('nan')

    return (
        lost, lost_perc, min_latency, max_latency, avg_latency,
        min_jitter, max_jitter, avg_jitter, mos)


def print_output(args, lost, lost_perc, min_latency, max_latency,
                 avg_latency, min_jitter, max_jitter, avg_jitter, mos):
    """Print output.
    """
    if args.output == 'normal':
        print(f'{args.destination} ping statistics ({args.length} bytes):\n'
              f' - packet loss: {lost_perc:.2%} ({lost}/{args.count})')
        if len(lost_perc) < 1:
            print(f' - latency (MIN/MAX/AVG): {min_latency:.2f}/'
                  f'{max_latency:.2f}/{avg_latency:.2f}')
            print(f' - jitter (MIN/MAX/AVG): {min_jitter:.2f}/{max_jitter:.2f}'
                  f'/{avg_jitter:.2f} ms')
            print(f' - MOS score: {mos:.2f}')
    elif args.output == 'check_mk':
        print('<<<nms_net_utils_ping>>>>')
        ping_type = 'udp' if args.udp else 'icmp'
        if lost_perc == 1:
            print(f'{args.a}_to_{args.z} {args.destination} {ping_type} '
                  f'{lost_perc:.4f} NaN NaN NaN NaN NaN NaN NaN')
        else:
            print(f'{args.a}_to_{args.z} {args.destination} {ping_type} '
                  f'{lost_perc:.4f} {min_latency:.2f} {max_latency:.2f} '
                  f'{avg_latency:.2f} {min_jitter:.2f} {max_jitter:.2f} '
                  f'{avg_jitter:.2f} {mos:.2f}')
    elif args.output == 'nagios':
        # If all packets were lost, just return critical.
        if lost_perc == 1:
            print(f'2 {args.a}_to_{args.z}_loss lost={lost_perc:.2f} '
                  f'{args.destination} - no reply')
            print(f'2 {args.a}_to_{args.z}_delay - no reply')
            print(f'2 {args.a}_to_{args.z}_jitter - no reply')
            print(f'2 {args.a}_to_{args.z}_mos - no reply')
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

            print(f'{loss_status} {args.a}_to_{args.z}_loss '
                  f'loss={(lost_perc * 100):.2f};{args.loss_warn:.2f};'
                  f'{args.loss_crit:.2f};0;100 {args.destination} - '
                  f'{lost_perc:.2%} packets lost')
            print(f'{latency_status} {args.a}_to_{args.z}_delay '
                  f'delay={avg_latency:.2f};{args.rtt_warn};{args.rtt_crit};0;'
                  f'{args.timeout} {args.destination} - {avg_latency:.2f} ms '
                  f'delay')
            print(f'{jitter_status} {args.a}_to_{args.z}_jitter '
                  f'jitter={(avg_jitter / 1000):.5f};'
                  f'{(args.jitter_warn / 1000):.5f};'
                  f'{(args.jitter_crit / 1000):.5f};0;{(args.timeout / 1000)} '
                  f'{args.destination} - {avg_jitter:.2f} ms jitter')
            print(f'{mos_status} {args.a}_to_{args.z}_mos mos={mos:.2f};'
                  f'{args.mos_warn:.2f};{args.mos_crit:.2f};0.0;5.0 '
                  f'{args.destination} - {mos:.2f} mos score')

            sys.exit(loss_status)


def main(args):
    """Main method.
    """
    args = parse_args(args)

    # Run a single ping.
    (
        lost, lost_perc, min_latency, max_latency, avg_latency,
        min_jitter, max_jitter, avg_jitter, mos
    ) = ping(
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

