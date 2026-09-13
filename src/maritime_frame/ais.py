"""AIS 6-bit armoring and common Class A message decoding."""
from __future__ import annotations

from .models import AisMessage


def _bits(payload: str) -> str:
    values = []
    for char in payload:
        code = ord(char) - 48
        if code > 40:
            code -= 8
        if not 0 <= code < 64:
            raise ValueError("invalid AIS armored character")
        values.append(f"{code:06b}")
    return "".join(values)


def _u(bits: str, start: int, width: int) -> int:
    end = start + width
    if end > len(bits):
        raise ValueError("truncated AIS payload")
    return int(bits[start:end], 2)


def _signed(bits: str, start: int, width: int) -> int:
    value = _u(bits, start, width)
    return value - (1 << width) if value & (1 << (width - 1)) else value


def decode(payload: str, fill_bits: int = 0) -> AisMessage:
    if not 0 <= fill_bits <= 5:
        raise ValueError("fill bits out of range")
    bits = _bits(payload)
    if fill_bits:
        bits = bits[:-fill_bits]
    message_type, repeat, mmsi = _u(bits, 0, 6), _u(bits, 6, 2), _u(bits, 8, 30)
    fields: dict[str, int | float | str] = {}
    if message_type in {1, 2, 3}:
        fields.update(
            navigational_status=_u(bits, 38, 4),
            rate_of_turn=_signed(bits, 42, 8),
            speed_over_ground=_u(bits, 50, 10) / 10.0,
            longitude=_signed(bits, 61, 28) / 600000.0,
            latitude=_signed(bits, 89, 27) / 600000.0,
            course_over_ground=_u(bits, 116, 12) / 10.0,
            true_heading=_u(bits, 128, 9),
            timestamp=_u(bits, 137, 6),
        )
    elif message_type == 5:
        fields.update(
            imo_number=_u(bits, 40, 30),
            callsign=_text(bits, 70, 42),
            vessel_name=_text(bits, 112, 120),
            ship_type=_u(bits, 232, 8),
            to_bow=_u(bits, 240, 9), to_stern=_u(bits, 249, 9),
            to_port=_u(bits, 258, 6), to_starboard=_u(bits, 264, 6),
        )
    else:
        fields["raw_bits"] = bits
    return AisMessage(message_type, repeat, mmsi, fields, payload)


def _text(bits: str, start: int, width: int) -> str:
    alphabet = "@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_ !\"#$%&'()*+,-./0123456789:;<=>?"
    return "".join(alphabet[_u(bits, offset, 6)] for offset in range(start, start + width, 6)).rstrip(" @")
