# NMS Network Utilities

A collection of Python utilities that can be used to monitor and trouble
network issues.  These functions can be run stand-alone, but the end goal is to
have their output ingested into Check_MK / Nagios.

# Ping Script

The ping script can be used to ping a destination on the internet and report
back latency, packet loss, jitter and MOS score.  There is also an option to
output text in Nagios / Check_MK readable format.  Along with this, there's
options to set warning and critical threshold for each metric that will cause
these states in Nagios / Check_MK.

## Usage

```
usage: ping.py [-h] [-c COUNT] [-t TIMEOUT] [-l LENGTH] [-a A] [-z Z]
               [-s SOURCE] [-d DESTINATION] [-u] [-U UDP_PORT]
               [-o {normal,nagios,check_mk}] [-p LOSS_WARN] [-P LOSS_CRIT]
               [-r RTT_WARN] [-R RTT_CRIT] [-j JITTER_WARN] [-J JITTER_CRIT]
               [-m MOS_WARN] [-M MOS_CRIT] [-v]

Python Ping Implementation

options:
  -h, --help            show this help message and exit
  -c COUNT, --count COUNT
                        number of packets to send
  -t TIMEOUT, --timeout TIMEOUT
                        timeout in ms
  -l LENGTH, --length LENGTH
                        Total packet length
  -a A                  A side name
  -z Z                  Z side name
  -s SOURCE, --source SOURCE
                        source IP
  -d DESTINATION, --destination DESTINATION
                        destination host
  -u, --udp             use UDP instead of ICMP
  -U UDP_PORT, --udp-port UDP_PORT
                        use UDP port, required if UDP is being used (-u)
  -o {normal,nagios,check_mk}, --output {normal,nagios,check_mk}
                        output type
  -p LOSS_WARN, --loss-warn LOSS_WARN
                        packet loss warning threshold
  -P LOSS_CRIT, --loss-crit LOSS_CRIT
                        packet loss critical threshold
  -r RTT_WARN, --rtt-warn RTT_WARN
                        latency RTT warning threshold
  -R RTT_CRIT, --rtt-crit RTT_CRIT
                        latency RTT critical threshold
  -j JITTER_WARN, --jitter-warn JITTER_WARN
                        latency RTT warning threshold
  -J JITTER_CRIT, --jitter-crit JITTER_CRIT
                        latency RTT critical threshold
  -m MOS_WARN, --mos-warn MOS_WARN
                        MOS score warning threshold
  -M MOS_CRIT, --mos-crit MOS_CRIT
                        MOS score critical threshold
  -v, --verbose         verbose output
```

## ICMP Ping

```
$ sudo ping.py -d 4.2.2.2 -c 10 -l 1500 -v
Password:
1500 bytes from 4.2.2.2: icmp_seq=0 ttl=52 time=47.61 ms
1500 bytes from 4.2.2.2: icmp_seq=1 ttl=52 time=44.77 ms
1500 bytes from 4.2.2.2: icmp_seq=2 ttl=52 time=45.17 ms
1500 bytes from 4.2.2.2: icmp_seq=3 ttl=52 time=45.07 ms
1500 bytes from 4.2.2.2: icmp_seq=4 ttl=52 time=45.16 ms
1500 bytes from 4.2.2.2: icmp_seq=5 ttl=52 time=45.09 ms
1500 bytes from 4.2.2.2: icmp_seq=6 ttl=52 time=44.75 ms
1500 bytes from 4.2.2.2: icmp_seq=7 ttl=52 time=44.94 ms
1500 bytes from 4.2.2.2: icmp_seq=8 ttl=52 time=44.88 ms
1500 bytes from 4.2.2.2: icmp_seq=9 ttl=52 time=45.33 ms
Statistics for A to Z:
 - packet loss: 0/10 (0.00%)
 - latency (MIN/MAX/AVG): 44.75/47.61/45.28 ms
 - jitter (MIN/MAX/AVG): 0.06/2.84/0.51 ms
 - MOS: 4.38
```

## UDP Ping

Optionally, you can UDP packets to ping instead of ICMP.  To do this first,
you must first have another host on the far end running the `udpserver.py`
script.  By default this listens on port `5001` and will just reply with the
same data it receives from the client.


### Server Side

```
$ udpserver.py
```

### Client Side
```
$ ping.py -u -d 127.0.0.1 -c 10 -l 1500 -v
1500 bytes from 127.0.0.1: seq=0 time=0.21 ms
1500 bytes from 127.0.0.1: seq=1 time=0.17 ms
1500 bytes from 127.0.0.1: seq=2 time=0.15 ms
1500 bytes from 127.0.0.1: seq=3 time=0.11 ms
1500 bytes from 127.0.0.1: seq=4 time=0.16 ms
1500 bytes from 127.0.0.1: seq=5 time=0.12 ms
1500 bytes from 127.0.0.1: seq=6 time=0.10 ms
1500 bytes from 127.0.0.1: seq=7 time=0.13 ms
1500 bytes from 127.0.0.1: seq=8 time=0.12 ms
1500 bytes from 127.0.0.1: seq=9 time=0.11 ms
Statistics for A to Z:
 - packet loss: 0/10 (0.00%)
 - latency (MIN/MAX/AVG): 0.10/0.21/0.14 ms
 - jitter (MIN/MAX/AVG): 0.01/0.05/0.03 ms
 - MOS: 4.40
```

## Simulate Packet Loss

There is an optional parameter you can pass to `udpserver.py`, `-l <number>`.
When used, there will be a `<number>`% chance that a packet that is received
will be ignore.  This can be used to simulate packet loss on the network.

```
$ udpserver.py -l 20
```

## MOS Score

Mean Opinion Score or MOS score is measurable, industry standard for rating
voice and video calls.  The higher the score, the better the quality and less
likely your users are to complain.  The score ranges from 1 to 5, in general
though, for VoIP calls using g.711 codec, the highest score possible is 4.4.

Below is a table showing the MOS Score vs the preceived quality.

| MOS Score | Call Quality    | User Satisfaction             |
| --------- | --------------- | ----------------------------- |
| 4.3 - 5.0 | Best            | Very satisfied                |
| 4.0 - 4.3 | Good            | Satisfied                     |
| 3.6 - 4.0 | Just OK         | Some users dissatisfied       |
| 3.1 - 3.6 | Bad             | Many users dissatisfied       |
| 2.6 - 3.1 | Very Bad        | Nearly all users dissatisfied |
| 1.0 - 2.6 | Not Recommended | All users dissatisfied        |

The algorithm used for MOS score calculation was found online on
[PingPlotter's KB](https://www.pingman.com/kb/article/how-is-mos-calculated-in-pingplotter-pro-50.html).

