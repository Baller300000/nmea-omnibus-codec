import unittest

from maritime_frame import FastPacketAssembler, Status, StreamParser, ddm_to_decimal, parse_sentence
from maritime_frame.ais import decode as decode_ais
from maritime_frame.n2k import decode_can_id
from maritime_frame.onenet import parse_datagram


class ParserTests(unittest.TestCase):
    def test_sentence_checksum_and_ddm(self):
        sentence = "$GPGGA,123519,4807.038,N,01131.000,E,1*53"
        parsed = parse_sentence(sentence, require_checksum=True)
        self.assertEqual(parsed.sentence_type, "GGA")
        self.assertAlmostEqual(ddm_to_decimal("4807.038", "N"), 48.1173, places=4)
        self.assertAlmostEqual(ddm_to_decimal("01131.000", "W"), -11.516666, places=4)

    def test_stream_fragment_status_and_recovery(self):
        parser = StreamParser()
        self.assertEqual(parser.feed("$GPRMC,1,2")[0].status, Status.PARTIAL_STREAM)
        event = parser.feed(",3*00\r\n")[0]
        self.assertEqual(event.status, Status.CORRUPTED_FRAME)

    def test_can_id(self):
        priority, pgn, source, destination = decode_can_id(0x0CF00401)
        self.assertEqual((priority, pgn, source, destination), (3, 61444, 1, None))

    def test_fast_packet_reassembly(self):
        assembler = FastPacketAssembler(timeout=1.0)
        can_id = 0x0CF00501
        self.assertIsNone(assembler.feed(can_id, bytes([0, 10, 1, 2, 3, 4, 5, 6]), 0.0))
        result = assembler.feed(can_id, bytes([1, 7, 8, 9, 10, 0, 0, 0]), 0.1)
        self.assertEqual(result.payload, bytes(range(1, 11)))
        self.assertIsNone(assembler.feed(can_id, bytes([0, 10, 1, 2, 3, 4, 5, 6]), 1.0))
        with self.assertRaises(ValueError):
            assembler.feed(can_id, bytes([1, 7, 8, 9, 10, 0, 0, 0]), 2.1)

    def test_onenet(self):
        datagram = parse_datagram(b"UdPBc 239.0.0.1\r\n$GPRMC")
        self.assertEqual(datagram.transport_header, "UdPBc")
        self.assertTrue(datagram.payload.startswith(b"239"))

    def test_unknown_ais_type_is_decoded(self):
        message = decode_ais("0" * 20)
        self.assertEqual(message.message_type, 0)


if __name__ == "__main__":
    unittest.main()
