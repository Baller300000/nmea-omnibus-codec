"""NMEA-2000 CAN identifier decoding and bounded Fast-Packet reassembly."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import N2kMessage


def decode_can_id(can_id: int) -> tuple[int, int, int, int | None]:
    if not 0 <= can_id < (1 << 29):
        raise ValueError("CAN identifier must be an 11-bit or 29-bit value")
    priority = (can_id >> 26) & 7
    data_page = (can_id >> 24) & 1
    pdu_format = (can_id >> 16) & 0xFF
    pdu_specific = (can_id >> 8) & 0xFF
    source = can_id & 0xFF
    pgn = (data_page << 16) | (pdu_format << 8)
    destination = None if pdu_format >= 240 else pdu_specific
    if pdu_format >= 240:
        pgn |= pdu_specific
    return priority, pgn, source, destination


@dataclass(slots=True)
class _Assembly:
    total: int
    data: bytearray
    next_index: int
    last_seen: float


class FastPacketAssembler:
    def __init__(self, timeout: float = 1.0, max_payload: int = 223) -> None:
        if timeout <= 0 or max_payload < 1:
            raise ValueError("invalid reassembly limits")
        self.timeout, self.max_payload = timeout, max_payload
        self._assemblies: dict[tuple[int, int, int, int | None, int], _Assembly] = {}

    def purge(self, now: float) -> None:
        expired = [key for key, item in self._assemblies.items() if now - item.last_seen > self.timeout]
        for key in expired:
            del self._assemblies[key]

    def feed(self, can_id: int, data: bytes, timestamp: float) -> N2kMessage | None:
        if len(data) != 8:
            raise ValueError("N2K CAN data frames must contain exactly 8 bytes")
        self.purge(timestamp)
        priority, pgn, source, destination = decode_can_id(can_id)
        sequence = data[0] >> 5
        frame_number = data[0] & 0x1F
        key = (pgn, source, destination or 0, sequence, priority)
        if frame_number == 0:
            total = data[1]
            if not 1 <= total <= self.max_payload:
                raise ValueError("invalid Fast-Packet payload length")
            item = _Assembly(total, bytearray(data[2:]), 1, timestamp)
            self._assemblies[key] = item
            if total <= 6:
                del self._assemblies[key]
                return N2kMessage(priority, pgn, source, destination, bytes(item.data[:total]), timestamp)
            return None
        item = self._assemblies.get(key)
        if item is None or frame_number != item.next_index:
            self._assemblies.pop(key, None)
            raise ValueError("missing or out-of-order Fast-Packet frame")
        item.data.extend(data[1:])
        item.next_index += 1
        item.last_seen = timestamp
        if len(item.data) >= item.total:
            del self._assemblies[key]
            return N2kMessage(priority, pgn, source, destination, bytes(item.data[:item.total]), timestamp)
        return None
