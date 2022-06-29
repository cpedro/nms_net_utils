# -*- encoding: utf-8; py-indent-offset: 4 -*-
"""
File: net/utils.py
Description: Performs various ICMP related tasks.

Combines code from the below places:
    https://gist.github.com/pklaus/856268 - Only works with Python2
    https://github.com/l4m3rx/python-ping - Has a bit more than needed
"""


__author__ = 'Chris Pedro'
__copyright__ = '(c) Chris Pedro 2022'
__licence__ = 'MIT'
__version__ = '0.1.0'


import array
import sys
import socket


def checksum(source_string):
    """A port of the functionality of in_cksum() from ping.c
    Ideally this would act on the string as a series of 16-bit ints (host
    packed), but this works.
    Network data is big-endian, hosts are typically little-endian
    """
    if (len(source_string) % 2):
        source_string += '\x00'
    converted = array.array('H', source_string)
    if sys.byteorder == 'big':
        converted.bytewap()
    val = sum(converted)

    val &= 0xffffffff  # Truncate val to 32 bits (a variance from ping.c, which
    # uses signed ints, but overflow is unlikely in ping)

    val = (val >> 16) + (val & 0xffff)  # Add high 16 bits to low 16 bits
    val += (val >> 16)  # Add carry from above (if any)
    answer = ~val & 0xffff  # Invert and truncate to 16 bits
    answer = socket.htons(answer)

    return answer


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
    r = r - ((loss * 100) * 2.5)
    # Convert the R into an MOS value. (this is a known formula)
    return 1 + (0.035) * r + (.000007) * r * (r - 60) * (100 - r)
