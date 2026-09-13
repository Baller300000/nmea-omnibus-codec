"""Registry hook for vendor-specific NMEA-0183 $P sentences."""
from __future__ import annotations

from collections.abc import Callable
from .models import NmeaSentence

Decoder = Callable[[NmeaSentence], object]


class ProprietaryRegistry:
    def __init__(self) -> None:
        self._decoders: dict[str, Decoder] = {}

    def register(self, manufacturer: str, decoder: Decoder) -> None:
        if not manufacturer or not manufacturer.isalnum():
            raise ValueError("manufacturer key must be alphanumeric")
        self._decoders[manufacturer.upper()] = decoder

    def decode(self, sentence: NmeaSentence) -> object:
        if not sentence.proprietary:
            raise ValueError("sentence is not proprietary")
        decoder = self._decoders.get(sentence.talker[1:].upper())
        return decoder(sentence) if decoder else sentence
