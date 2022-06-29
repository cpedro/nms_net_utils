# -*- encoding: utf-8; py-indent-offset: 4 -*-
"""
File: net/icmp.py
Description: Performs various ICMP related tasks.

Author: Chris Pedro
Copyright: (c) Chris Pedro 2022'
Licence: MIT

Combines code from the below places:
    https://gist.github.com/pklaus/856268 - Only works with Python2
    https://github.com/l4m3rx/python-ping - Has a bit more than needed
"""


import os
import select
import socket
import struct
import sys
import time

from . import utils


try:
    from _thread import get_ident
except ImportError:
    def get_ident():
        return 0


if sys.platform == 'win32':
    # On Windows, the best timer is time.clock()
    default_timer = time.clock
else:
    # On most other platforms the best timer is time.time()
    default_timer = time.time


# ICMP parameters
ICMP_ECHOREPLY = 0  # Echo reply (per RFC792)
ICMP_ECHO = 8  # Echo request (per RFC792)
ICMP_ECHO_IPV6 = 128  # Echo request (per RFC4443)
ICMP_ECHO_IPV6_REPLY = 129  # Echo request (per RFC4443)
ICMP_MAX_RECV = 2048  # Max size of incoming buffer
ICMP_ECHO_IPV4_HEADER_SIZE = 8  # ICMP + IP header size for IPv4
ICMP_ECHO_IPV6_HEADER_SIZE = 32  # ICMP + IP header size for IPv6


def _send(my_socket, dest_ip, my_id, seq, packet_size, ipv6=False):
    """Send one ping to the given >dest_ip<.
    """
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)
    # (packet_size - 8) - Remove header size from packet size
    my_checksum = 0

    # Make a dummy heder with a 0 checksum.
    if ipv6:
        header = struct.pack(
            '!BbHHh', ICMP_ECHO_IPV6, 0, my_checksum, my_id, seq)
        header_len = ICMP_ECHO_IPV6_HEADER_SIZE
    else:
        header = struct.pack(
            '!BBHHH', ICMP_ECHO, 0, my_checksum, my_id, seq)
        header_len = ICMP_ECHO_IPV4_HEADER_SIZE

    data = utils.generate_packet_data((packet_size - header_len))

    # Calculate the checksum on the data and the dummy header.
    my_checksum = utils.checksum(header + data)  # Checksum is in network order

    # Now that we have the right checksum, we put that in. It's just easier
    # to make up a new header than to stuff it into the dummy.
    if ipv6:
        header = struct.pack(
            '!BbHHh', ICMP_ECHO_IPV6, 0, my_checksum, my_id, seq)
    else:
        header = struct.pack(
            '!BBHHH', ICMP_ECHO, 0, my_checksum, my_id, seq)

    packet = header + data

    send_time = default_timer()

    try:
        my_socket.sendto(packet, (dest_ip, 1))  # Port number is irrelevant
    except OSError:
        return
    except socket.error:
        return

    return send_time


def _receive(my_socket, my_id, timeout, ipv6=False):
    """Receive the ping from the socket. Timeout = in ms
    """
    time_left = timeout / 1000

    while True:  # Loop while waiting for packet or timeout
        started_select = default_timer()
        what_ready = select.select([my_socket], [], [], time_left)
        how_long_in_select = (default_timer() - started_select)
        if what_ready[0] == []:  # Timeout
            return None, 0, 0, 0, 0

        time_received = default_timer()

        data, addr = my_socket.recvfrom(ICMP_MAX_RECV)

        ip_header = data[:20]

        (head_version, head_tos, head_len, head_id, head_flags, head_ttl,
            head_protocol, head_checksum, head_src, head_dest) = (
                struct.unpack('!BBHHHBBHII', ip_header))

        if ipv6:
            icmp_header = data[0:8]
            header_len = ICMP_ECHO_IPV6_HEADER_SIZE
        else:
            icmp_header = data[20:28]
            header_len = ICMP_ECHO_IPV4_HEADER_SIZE

        icmp_type, icmp_code, icmp_checksum, icmp_packet_id, icmp_seq = (
            struct.unpack('!BBHHH', icmp_header))

        # Match only the packets we care about
        if (icmp_type != ICMP_ECHO) and (icmp_packet_id == my_id):
            data_size = len(data) - 28
            return (time_received, (data_size + header_len), head_src,
                    icmp_seq, head_ttl)

        time_left = time_left - how_long_in_select
        if time_left <= 0:
            return None, 0, 0, 0, 0


def single_ping(dest_ip, timeout, seq, packet_size, ipv6=False,
                src_ip=None, verbose=False):
    """Returns either the delay (in ms) or None on timeout.
    """
    delay = None

    if ipv6:
        try:
            my_socket = socket.socket(socket.AF_INET6, socket.SOCK_RAW,
                                      socket.getprotobyname('ipv6-icmp'))
            if src_ip is not None:
                my_socket.bind((src_ip, 0))
            my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except OSError as e:
            print(format(str(e)))
            print('NOTE: This script requires root permissions to run.')
            raise
    else:
        try:
            my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                                      socket.getprotobyname('icmp'))
            if src_ip is not None:
                my_socket.bind((src_ip, 0))
            my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except OSError as e:
            print(format(str(e)))
            print('NOTE: This script requires root permissions to run.')
            raise

    my_ID = (os.getpid() ^ get_ident()) & 0xFFFF

    sent_time = _send(my_socket, dest_ip, my_ID, seq, packet_size, ipv6)
    if sent_time is None:
        my_socket.close()
        return delay

    recv_time, data_size, src, seq, ttl = _receive(
        my_socket, my_ID, timeout, ipv6)

    my_socket.close()

    if recv_time:
        delay = (recv_time - sent_time) * 1000
        if verbose:
            print("{} bytes from {}: icmp_seq={} ttl={} time={:.2f} ms".format(
                  data_size, dest_ip, seq, ttl, delay))
    else:
        delay = None

    return delay

