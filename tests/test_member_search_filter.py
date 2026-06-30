import unittest
from types import SimpleNamespace

from member_search_filter import member_matches_fast_search, normalize_member_search_text


class MemberSearchFilterTest(unittest.TestCase):
    def test_normalize_member_search_text_casefolds_accents_and_spaces(self):
        self.assertEqual(normalize_member_search_text("  ĎuRICA   Ján  "), "durica jan")

    def test_member_matches_fast_search_by_first_or_last_name_prefix(self):
        member = SimpleNamespace(first_name="Ján", last_name="Ďurica")

        self.assertTrue(member_matches_fast_search(member, "j"))
        self.assertTrue(member_matches_fast_search(member, "du"))
        self.assertTrue(member_matches_fast_search(member, "jan du"))
        self.assertTrue(member_matches_fast_search(member, "du jan"))
        self.assertFalse(member_matches_fast_search(member, "an"))
        self.assertFalse(member_matches_fast_search(member, "ri"))


if __name__ == "__main__":
    unittest.main()
