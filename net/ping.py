# -*- encoding: utf-8; py-indent-offset: 4 -*-
"""
File: net/icmp.py
Description: Performs various ICMP related tasks.

Author: Chris Pedro
Copyright: (c) Chris Pedro 2024'
Licence: MIT
"""


import sys

from . import icmp, udp


def mos_score(latency, jitter, loss):
    """Caculate MOS score.
    Algorithm for MOS is PingPlotter method:
    https://www.pingman.com/kb/article/how-is-mos-calculated-in-pingplotter-pro-50.html
    """
    # Take the average latency, add jitter, but double the impact to
    # latency then add 10 for protocol latencies
    eff_latency = latency + jitter * 2 + 10
    # Implement a basic curve - deduct 4 for the R value at 160ms of
    # latency (round trip).  Anything over that gets a much more agressive
    # deduction
    if eff_latency < 160:
        r = 93.2 - (eff_latency / 40)
    else:
        r = 93.2 - (eff_latency - 120) / 10
    # Now, let's deduct 2.5 R values per percentage of packet loss
    # Bug fix: would cause large MOS score when R went below 0.
    r = max(0, (r - (loss * 2.5)))
    # Convert the R into an MOS value. (this is a known formula)
    return 1 + (0.035) * r + (0.000007) * r * (r - 60) * (100 - r)


def ping(source, destination, length, count, timeout,
         udp_ping=False, udp_port=5001, verbose=False):
    """Send a ping to a remote host, using ICMP or UDP, then returns:
        lost - the number of lost packets
        lost_perc - percentage of lost packets as a number between 0 and 1
        min_latency - minimum rtt number in ms
        max_latency - maximum rtt number in ms
        avg_latency - average rtt in ms
        min_jtter - minimum jitter number in ms
        max_jitter - maximum jitter number in ms
        avg_jitter - average jitter across all packets in ms
        mos - MOS score calculated for the ping
    """
    lost = 0
    latency = []
    jitter = []

    # Do pings, and collect latencies all other stats will be derived.
    for i in range(0, count):
        try:
            if udp_ping and udp_port:
                delay = udp.single_ping(
                    destination, udp_port, timeout, i, length, src_ip=source,
                    verbose=verbose)
            else:
                delay = icmp.single_ping(
                    destination, timeout, i, length, src_ip=source,
                    verbose=verbose)
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
        mos = mos_score(avg_latency, avg_jitter, (lost_perc * 100))
    else:
        mos = float('nan')

    return (
        lost, lost_perc, min_latency, max_latency, avg_latency,
        min_jitter, max_jitter, avg_jitter, mos)


