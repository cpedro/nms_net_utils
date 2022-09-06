# -*- encoding: utf-8; py-indent-offset: 4 -*-
"""
File: net/udp.py
Description: Performs various UDP related tasks.

Author: Chris Pedro
Copyright: (c) Chris Pedro 2022'
Licence: MIT
"""


import random
import socket

from . import utils


# UDP parameters
UDP_SRC_PORT = 0  # Default UDP source port
UDP_MAX_RECV = 2048  # Max size of incoming buffer
UDP_IPV6_HEADER_SIZE = 44  # UDP + IP header size for IPv4
UDP_IPV4_HEADER_SIZE = 16  # UDP + IP header size for IPv6


def listen_and_reply(address, port, ipv6=False, loss=0, verbose=False):
    """Sets up a simple UDP server to listen and reply back with the same
    messages that it receives.

    If >loss< is specified there will be a percent chance that the server will
    just ignore the packet.  This can be useful when testing to simulate
    packet loss.
    """
    if ipv6:
        try:
            my_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            my_socket.bind((address, port))
        except OSError as e:
            utils.eprint(format(str(e)))
            utils.eprint(
                'NOTE: Using port < 1024 requires root permissions to run.')
            raise
    else:
        try:
            my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            my_socket.bind((address, port))
        except OSError as e:
            utils.eprint(format(str(e)))
            utils.eprint(
                'NOTE: Using port < 1024 requires root permissions to run.')
            raise

    try:
        while True:
            data, address = my_socket.recvfrom(UDP_MAX_RECV)
            if verbose:
                utils.eprint('Received from {}: {}'.format(address, data))

            if loss > 0:
                rand = random.uniform(0, 99)
                if rand < loss:
                    if verbose:
                        utils.eprint('Packet being ignored.')
                    continue

            my_socket.sendto(data, address)
    except KeyboardInterrupt:
        return


def _send(my_socket, dest_ip, port, seq, packet_length, ipv6=False):
    """Sends data over the UDP socket.
    """
    if ipv6:
        header_len = UDP_IPV6_HEADER_SIZE
    else:
        header_len = UDP_IPV4_HEADER_SIZE

    data = utils.generate_packet_data((packet_length - header_len))
    address = (dest_ip, port)

    send_time = utils.default_timer()

    try:
        my_socket.sendto(data, address)
    except OSError:
        return None
    except socket.error:
        return None

    return send_time


def _receive(my_socket, ipv6=False):
    """Receives data on the UDP socket, after using _send().
    """
    if ipv6:
        header_len = UDP_IPV6_HEADER_SIZE
    else:
        header_len = UDP_IPV4_HEADER_SIZE

    try:
        data, address = my_socket.recvfrom(UDP_MAX_RECV)
        recv_time = utils.default_timer()
        return recv_time, (len(data) + header_len)
    except socket.timeout:
        return None, 0


def single_ping(dest_ip, port, timeout, seq, packet_length, ipv6=False,
                src_ip=None, verbose=False):
    """Sends a single 'ping' UDP packet to a destination.  It will just connect
    and record the time it takes to get a response from the server.
    """
    delay = None

    if ipv6:
        try:
            my_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            if src_ip is not None:
                my_socket.bind((src_ip, UDP_SRC_PORT))
            my_socket.settimeout(float(timeout) / 1000)
        except OSError as e:
            utils.eprint(format(str(e)))
            utils.eprint(
                'NOTE: Using port < 1024 requires root permissions to run.')
            raise
    else:
        try:
            my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            if src_ip is not None:
                my_socket.bind((src_ip, UDP_SRC_PORT))
            my_socket.settimeout(float(timeout) / 1000)
        except OSError as e:
            utils.eprint(format(str(e)))
            utils.eprint(
                'NOTE: Using port < 1024 requires root permissions to run.')
            raise

    sent_time = _send(my_socket, dest_ip, port, seq, packet_length, ipv6)

    if sent_time is None:
        return None

    recv_time, data_size = _receive(my_socket, ipv6)
    if recv_time:
        delay = (recv_time - sent_time) * 1000
        if verbose:
            utils.eprint('{} bytes from {}: seq={} time={:.2f} ms'.format(
                data_size, dest_ip, seq, delay))
    else:
        delay = None
        if verbose:
            utils.eprint('Request timeout for seq {}'.format(seq))

    return delay

