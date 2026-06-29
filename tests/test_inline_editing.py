import datetime
import unittest

from inline_editing import parse_address_text, parse_full_name, parse_optional_date


class InlineEditingHelpersTest(unittest.TestCase):
    def test_parse_full_name_keeps_first_token_as_first_name(self):
        first_name, last_name = parse_full_name("Tomáš Lánczos")

        self.assertEqual(first_name, "Tomáš")
        self.assertEqual(last_name, "Lánczos")

    def test_parse_full_name_keeps_multi_part_last_name(self):
        first_name, last_name = parse_full_name("Ján Novák Mladší")

        self.assertEqual(first_name, "Ján")
        self.assertEqual(last_name, "Novák Mladší")

    def test_parse_address_text_maps_comma_separated_parts(self):
        parsed = parse_address_text("Jaskynná 1, Liptovský Mikuláš, 031 01, SK")

        self.assertEqual(parsed.street, "Jaskynná 1")
        self.assertEqual(parsed.city, "Liptovský Mikuláš")
        self.assertEqual(parsed.zip_code, "031 01")
        self.assertEqual(parsed.country, "SK")

    def test_parse_optional_date_accepts_empty_value(self):
        self.assertIsNone(parse_optional_date(""))

    def test_parse_optional_date_requires_iso_date(self):
        self.assertEqual(parse_optional_date("2026-06-29"), datetime.date(2026, 6, 29))
        with self.assertRaises(ValueError):
            parse_optional_date("29.06.2026")


if __name__ == "__main__":
    unittest.main()
