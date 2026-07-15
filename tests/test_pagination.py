import unittest

from backend.pagination import (
    InvalidCursorError,
    decode_cursor,
    decode_id_cursor,
    decode_keyset_cursor,
    encode_cursor,
    encode_id_cursor,
    encode_keyset_cursor,
)


class PaginationCursorTest(unittest.TestCase):
    def test_decode_cursor_round_trips_valid_offset(self):
        self.assertEqual(decode_cursor(encode_cursor(42)), 42)

    def test_decode_cursor_treats_missing_cursor_as_start(self):
        self.assertEqual(decode_cursor(None), 0)
        self.assertEqual(decode_cursor(""), 0)

    def test_decode_cursor_raises_on_corrupted_cursor_instead_of_silently_resetting(self):
        with self.assertRaises(InvalidCursorError):
            decode_cursor("not-a-valid-cursor!!!")

    def test_decode_id_cursor_round_trips_valid_id(self):
        self.assertEqual(decode_id_cursor(encode_id_cursor(7)), 7)

    def test_decode_id_cursor_raises_on_corrupted_cursor(self):
        with self.assertRaises(InvalidCursorError):
            decode_id_cursor("tampered")

    def test_decode_keyset_cursor_round_trips_valid_keyset(self):
        values = {"lastName": "Lovelace", "memberId": 101}
        self.assertEqual(decode_keyset_cursor(encode_keyset_cursor(values)), values)

    def test_decode_keyset_cursor_raises_on_corrupted_cursor(self):
        with self.assertRaises(InvalidCursorError):
            decode_keyset_cursor("garbage$$$")


if __name__ == "__main__":
    unittest.main()
