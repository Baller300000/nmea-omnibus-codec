"""NMEA-0183 sentence parsing, checksum validation, and coordinate helpers."""
from __future__ import annotations

import re
from .models import NmeaSentence

_SENTENCE = re.compile(r"^([$!])([^,*\r\n]{1,80})(?:,([^*\r\n]{0,512}))?(?:\*([0-9A-Fa-f]{2}))?$", re.ASCII)


def checksum(body: str | bytes) -> int:
    raw = body.encode("ascii") if isinstance(body, str) else body
    value = 0
    for byte in raw:
        value ^= byte
    return value


def parse_sentence(line: str | bytes, *, require_checksum: bool = False) -> NmeaSentence:
    text = line.decode("ascii", "strict") if isinstance(line, bytes) else line
    text = text.strip("\r\n")
    if not text or text[0] not in "$!":
        raise ValueError("sentence must begin with '$' or '!'")
    match = _SENTENCE.fullmatch(text)
    if not match:
        raise ValueError("malformed NMEA sentence")
    prefix, head, fields_text, supplied_hex = match.groups()
    supplied = int(supplied_hex, 16) if supplied_hex else None
    body = head + (("," + fields_text) if fields_text is not None else "")
    if supplied is None and require_checksum:
        raise ValueError("checksum is required")
    if supplied is not None and checksum(body) != supplied:
        raise ValueError("checksum mismatch")
    if head.startswith("P"):
        talker, sentence_type = head[:3], head[3:]
        proprietary = True
    else:
        talker, sentence_type = head[:2], head[2:]
        proprietary = False
    fields = tuple(fields_text.split(",")) if fields_text is not None else ()
    return NmeaSentence(talker, sentence_type, fields, text, supplied, proprietary)


def ddm_to_decimal(value: str, hemisphere: str) -> float:
    """Convert NMEA ddmm.mmmm or dddmm.mmmm coordinates to signed degrees."""
    if not value or hemisphere.upper() not in {"N", "S", "E", "W"}:
        raise ValueError("invalid DDM coordinate")
    try:
        degrees = int(value[: value.index(".") - 2])
        minutes = float(value[value.index(".") - 2 :])
    except (ValueError, IndexError):
        raise ValueError("invalid DDM coordinate") from None
    if not 0 <= minutes < 60:
        raise ValueError("coordinate minutes out of range")
    decimal = degrees + minutes / 60.0
    return -decimal if hemisphere.upper() in {"S", "W"} else decimal
