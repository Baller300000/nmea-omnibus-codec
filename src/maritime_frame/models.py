"""Public immutable data structures and parser status values."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Status(str, Enum):
    VALID_FRAME = "VALID_FRAME"
    PARTIAL_STREAM = "PARTIAL_STREAM"
    CORRUPTED_FRAME = "CORRUPTED_FRAME"


@dataclass(frozen=True, slots=True)
class ParseEvent:
    status: Status
    protocol: str | None = None
    message: Any = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class NmeaSentence:
    talker: str
    sentence_type: str
    fields: tuple[str, ...]
    raw: str
    checksum: int | None
    proprietary: bool = False


@dataclass(frozen=True, slots=True)
class AisMessage:
    message_type: int
    repeat: int
    mmsi: int
    fields: dict[str, int | float | str]
    payload: str


@dataclass(frozen=True, slots=True)
class CanFrame:
    can_id: int
    data: bytes
    timestamp: float


@dataclass(frozen=True, slots=True)
class N2kMessage:
    priority: int
    pgn: int
    source: int
    destination: int | None
    payload: bytes
    timestamp: float
    fields: dict[str, int | float | str] = field(default_factory=dict)
