"""NMEA-OneNet/IEC 61162-450 transport envelope helpers."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OneNetDatagram:
    transport_header: str
    payload: bytes


def parse_datagram(data: bytes | str) -> OneNetDatagram:
    raw = data.encode("ascii") if isinstance(data, str) else data
    separator = raw.find(b" ")
    if separator <= 0 or separator > 128:
        raise ValueError("OneNet transport header is missing")
    header = raw[:separator].decode("ascii", "strict")
    if not (header.startswith("UdP") or header.startswith("TcP")):
        raise ValueError("unsupported OneNet transport header")
    return OneNetDatagram(header, raw[separator + 1 :])
