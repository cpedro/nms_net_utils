from __future__ import print_function
# -*- encoding: utf-8; py-indent-offset: 4 -*-
"""
File: net/utils.py
Description: Performs various utility tasks.

Author: Chris Pedro
Copyright: (c) Chris Pedro 2022'
Licence: MIT

Combines code from the below places:
    https://gist.github.com/pklaus/856268 - Only works with Python2
    https://github.com/l4m3rx/python-ping - Has a bit more than needed
"""


import argparse
import array
import struct
import sys
import socket
import time


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
    fvalue = float(value)
    if fvalue <= 0:
        raise argparse.ArgumentTypeError(
            '{} must be a positive float value'.format(value))
    return fvalue


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


def default_timer():
    """Returns best timer to use, based on the system running the script.
    """
    if sys.platform == 'win32':
        # On Windows, the best timer is time.clock()
        return time.clock()
    else:
        # On most other platforms the best timer is time.time()
        return time.time()


def eprint(*args, **kwargs):
    """Print error message to stderr.
    """
    print(*args, file=sys.stderr, **kwargs)


def generate_packet_data(payload_size):
    """Generates random data to be used in a packet payload.
    """
    pad_bytes = []
    start_val = 0x42

    # Because of the string/byte changes in Python 3 we have to build the
    # data differnely for different version or it will make packets with
    # unexpected size.
    if sys.version[:1] == '2':
        _bytes = struct.calcsize('d')
        data = (payload_size - _bytes) * 'Q'
        data = struct.pack('d', default_timer()) + data
    else:
        for i in range(start_val, start_val + payload_size):
            pad_bytes += [(i & 0xff)]
        data = bytearray(pad_bytes)
    return data


