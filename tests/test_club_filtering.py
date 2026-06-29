from types import SimpleNamespace
import unittest

from club_filtering import club_matches_filter, normalise_filter_text


class ClubFilteringTest(unittest.TestCase):
    def test_normalise_filter_text_casefolds_and_collapses_whitespace(self):
        self.assertEqual(normalise_filter_text("  Speleo   NITRA "), "speleo nitra")

    def test_club_matches_filter_across_contact_and_president_fields(self):
        club = SimpleNamespace(
            name="Speleoklub Nitra",
            street="Jaskyniarska 1",
            city="Nitra",
            zip_code="94901",
            country="SK",
            email="club@example.sk, predseda@example.sk",
            phone="0903 111 222",
            webpage="https://speleo.example.sk",
            president_name="Ada Lovelace",
            president_name_text="Ada Lovelace",
            member_count=12,
        )

        self.assertTrue(club_matches_filter(club, "nitra ada"))
        self.assertTrue(club_matches_filter(club, "predseda@example"))
        self.assertTrue(club_matches_filter(club, "12"))
        self.assertFalse(club_matches_filter(club, "bratislava"))


if __name__ == "__main__":
    unittest.main()
