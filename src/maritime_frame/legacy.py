"""Small, explicit decoders for NMEA-0180/0182 steering sentences."""
from __future__ import annotations


def parse_0180(fields: list[str] | tuple[str, ...]) -> dict[str, str | float]:
    if len(fields) < 2:
        raise ValueError("NMEA-0180 requires steering flag and error")
    flag = fields[0].upper()
    if flag not in {"L", "R", "A", "V"}:
        raise ValueError("invalid cross-track error flag")
    return {"cross_track_flag": flag, "cross_track_error": float(fields[1])}


def parse_0182(fields: list[str] | tuple[str, ...]) -> dict[str, str | float]:
    if len(fields) < 2:
        raise ValueError("NMEA-0182 requires bearing flag and bearing")
    flag = fields[0].upper()
    if flag not in {"A", "M", "T", "V"}:
        raise ValueError("invalid bearing flag")
    return {"bearing_flag": flag, "bearing": float(fields[1])}
