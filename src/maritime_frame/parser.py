"""Bounded, incremental dispatcher for ASCII NMEA and binary CAN inputs."""
from __future__ import annotations

from .ais import decode as decode_ais
from .models import N2kMessage, ParseEvent, Status
from .n2k import FastPacketAssembler
from .nmea0183 import parse_sentence


class _PartialFrame(Exception):
    pass


class StreamParser:
    def __init__(self, *, max_sentence: int = 1024, n2k_timeout: float = 1.0) -> None:
        if max_sentence < 16:
            raise ValueError("max_sentence is too small")
        self.max_sentence = max_sentence
        self._text = bytearray()
        self._ais_fragments: dict[str, list[str]] = {}
        self.n2k = FastPacketAssembler(timeout=n2k_timeout)

    def feed(self, chunk: str | bytes) -> list[ParseEvent]:
        raw = chunk.encode("ascii") if isinstance(chunk, str) else bytes(chunk)
        events: list[ParseEvent] = []
        for byte in raw:
            if byte in (10, 13):
                if self._text:
                    events.append(self._parse_line(bytes(self._text)))
                    self._text.clear()
                continue
            if not self._text and byte not in (36, 33):
                continue
            if len(self._text) >= self.max_sentence:
                self._text.clear()
                events.append(ParseEvent(Status.CORRUPTED_FRAME, error="sentence exceeds configured limit"))
                continue
            self._text.append(byte)
        if self._text:
            events.append(ParseEvent(Status.PARTIAL_STREAM))
        elif not events:
            events.append(ParseEvent(Status.PARTIAL_STREAM))
        return events

    def feed_can(self, can_id: int, data: bytes, timestamp: float) -> ParseEvent:
        try:
            message = self.n2k.feed(can_id, data, timestamp)
        except (ValueError, IndexError) as exc:
            return ParseEvent(Status.CORRUPTED_FRAME, protocol="NMEA-2000", error=str(exc))
        if message is None:
            return ParseEvent(Status.PARTIAL_STREAM, protocol="NMEA-2000")
        return ParseEvent(Status.VALID_FRAME, protocol="NMEA-2000", message=message)

    def _parse_line(self, raw: bytes) -> ParseEvent:
        try:
            sentence = parse_sentence(raw, require_checksum=False)
            if sentence.talker == "AI" and sentence.sentence_type in {"VDM", "VDO"}:
                message = self._parse_ais(sentence)
                return ParseEvent(Status.VALID_FRAME, protocol="AIS", message=message)
            return ParseEvent(Status.VALID_FRAME, protocol="NMEA-0183", message=sentence)
        except _PartialFrame:
            return ParseEvent(Status.PARTIAL_STREAM, protocol="AIS")
        except (ValueError, UnicodeError) as exc:
            return ParseEvent(Status.CORRUPTED_FRAME, protocol="NMEA-0183", error=str(exc))

    def _parse_ais(self, sentence):
        if len(sentence.fields) < 6:
            raise ValueError("AIS sentence requires fragment fields")
        total, number = int(sentence.fields[0]), int(sentence.fields[1])
        sequence = sentence.fields[2] or "_"
        payload, fill = sentence.fields[4], int(sentence.fields[5])
        key = f"{sentence.sentence_type}:{sequence}"
        parts = self._ais_fragments.setdefault(key, [])
        if number == 1:
            parts.clear()
        if number != len(parts) + 1 or total < number:
            self._ais_fragments.pop(key, None)
            raise ValueError("AIS fragments are out of order")
        parts.append(payload)
        if number != total:
            raise _PartialFrame()
        self._ais_fragments.pop(key, None)
        return decode_ais("".join(parts), fill)
