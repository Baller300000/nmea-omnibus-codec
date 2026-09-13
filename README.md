# maritime-frame

`maritime-frame` is a zero-runtime-dependency Python library for incremental NMEA and marine telemetry decoding. It is designed for applications that receive arbitrary serial, TCP, UDP, or CAN fragments and cannot assume that one read equals one frame.

## Install and test

```bash
python -m pip install .
python -m unittest discover -s tests -v
```

## Streaming NMEA-0183 and AIS

```python
from maritime_frame import StreamParser, Status

parser = StreamParser(max_sentence=1024)
for chunk in serial_port:
    for event in parser.feed(chunk):
        if event.status is Status.VALID_FRAME:
            print(event.protocol, event.message)
        elif event.status is Status.CORRUPTED_FRAME:
            logger.warning("discarded frame: %s", event.error)
```

`feed()` accepts `str` or ASCII `bytes`, retains incomplete lines, rejects overlong input, validates the optional two-digit XOR checksum, and recognizes `$` and `!` prefixes. `ddm_to_decimal("4807.038", "N")` returns `48.1173`. AIS `!AIVDM` and `!AIVDO` payloads are 6-bit unarmored into a bit string; message types 1, 2, 3, and 5 expose MMSI, position, speed, course, heading, identity, and ship dimensions. Multi-sentence AIS messages are reassembled by sequence ID.

## NMEA-2000 CAN and Fast Packet

A 29-bit CAN identifier is mapped as follows:

```text
28       26 25 24 23       16 15        8 7       0
+----------+--+--+-----------+------------+---------+
| priority |R |DP| PDU format|PDU specific| source  |
+----------+--+--+-----------+------------+---------+
```

```python
from maritime_frame import StreamParser

parser = StreamParser(n2k_timeout=1.0)
first = parser.feed_can(0x0CF00501, bytes([0, 10, 1, 2, 3, 4, 5, 6]), 100.0)
second = parser.feed_can(0x0CF00501, bytes([1, 7, 8, 9, 10, 0, 0, 0]), 100.1)
assert second.message.payload == bytes(range(1, 11))
```

The assembler enforces frame number order, a maximum payload of 223 bytes, exact eight-byte CAN data frames, and timeout purging before each frame. Dropped or late follow-up frames never remain in memory indefinitely.

## OneNet, legacy, and proprietary layers

```python
from maritime_frame.onenet import parse_datagram
from maritime_frame.proprietary import ProprietaryRegistry

network = parse_datagram(b"UdPBc $GPRMC,...")
registry = ProprietaryRegistry()
registry.register("PGR", lambda sentence: {"vendor": "Garmin", "fields": sentence.fields})
```

`parse_datagram` validates the `UdP*`/`TcP*` transport token and preserves the payload for the normal stream parser. `legacy.parse_0180` and `legacy.parse_0182` decode steering and bearing flags. The proprietary registry is intentionally open-ended so vendor payload schemas remain application-owned.

## Status contract

Every chunk or CAN frame yields one deterministic status: `VALID_FRAME`, `PARTIAL_STREAM`, or `CORRUPTED_FRAME`. A partial NMEA line produces a partial event while its bytes remain buffered. Invalid checksums, invalid AIS armor, overflows, malformed transport headers, and N2K sequencing errors produce corrupted events without exposing unsafe indexes or unbounded allocations.

## Scope and transport boundary

The package parses frames; it does not open sockets, configure serial ports, or control a CAN adapter. That keeps it portable and lets downstream systems choose their I/O, scheduling, timestamp, and multicast policy. All runtime code uses only the Python standard library.
