import unittest

from tools.import_sss_clubs import parse_club_directory, parse_person_name


class SssClubImportTest(unittest.TestCase):
    def test_parse_club_directory_preserves_multiple_contacts_and_webpage(self):
        html = """
        <table>
          <tr>
            <td>Speleo Test Club</td>
            <td>Public President</td>
            <td>
              0903 111 222, 02/123 45 67,
              <a href="mailto:first@example.sk">first@example.sk</a>,
              second@example.sk,
              <a href="https://speleo.example.sk">www.speleo.example.sk</a>
            </td>
          </tr>
        </table>
        """

        entries = parse_club_directory(html)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].club_name, "Speleo Test Club")
        self.assertEqual(entries[0].president_name, "Public President")
        self.assertEqual(entries[0].president_first_name, "Public")
        self.assertEqual(entries[0].president_last_name, "President")
        self.assertEqual(entries[0].phone, "0903 111 222, 02/123 45 67")
        self.assertEqual(entries[0].email, "first@example.sk, second@example.sk")
        self.assertEqual(entries[0].webpage, "https://speleo.example.sk")

    def test_parse_person_name_preserves_titles(self):
        parsed = parse_person_name("doc. Mgr. Tomáš Lánczos, PhD.")

        self.assertEqual(parsed, ("doc. Mgr.", "Tomáš", "Lánczos", "PhD."))

    def test_parse_person_name_handles_trailing_generation_suffix(self):
        parsed = parse_person_name("Mgr. Pavol Pokrievka ml.")

        self.assertEqual(parsed, ("Mgr.", "Pavol", "Pokrievka", "ml."))


if __name__ == "__main__":
    unittest.main()
