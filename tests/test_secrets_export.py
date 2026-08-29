import csv
import io
import os
import stat
import tempfile
import unittest

from secrets_export import (
    build_secrets_csv,
    build_secrets_export,
    build_secrets_txt,
    write_secrets_export,
)

FIELDS = [
    ("db_password", "Database password"),
    ("credentials_json", "GCP service account key"),
    ("api_token", "API token"),
]


class BuildSecretsTxtTest(unittest.TestCase):
    def test_masked_values_are_exported_in_plaintext(self):
        text = build_secrets_txt({"db_password": "s3cr3t!"}, FIELDS)
        self.assertIn("db_password = s3cr3t!", text)
        self.assertNotIn("*", text.split("db_password")[1].splitlines()[0])

    def test_warning_header_is_present(self):
        text = build_secrets_txt({}, FIELDS)
        self.assertIn("PLAINTEXT secrets", text)

    def test_multiline_values_are_indented_under_the_key(self):
        text = build_secrets_txt({"credentials_json": '{\n  "type": "service_account"\n}'}, FIELDS)
        self.assertIn("credentials_json =\n", text)
        self.assertIn('    "type": "service_account"', text)

    def test_missing_and_none_values_render_as_empty(self):
        text = build_secrets_txt({"api_token": None}, FIELDS)
        self.assertIn("api_token = \n", text)
        self.assertIn("db_password = \n", text)

    def test_secrets_outside_the_form_are_still_exported(self):
        text = build_secrets_txt({"legacy_key": "kept"}, FIELDS)
        self.assertIn("legacy_key = kept", text)


class BuildSecretsCsvTest(unittest.TestCase):
    def test_round_trips_commas_quotes_and_newlines(self):
        tricky = 'a,b "quoted"\nsecond line'
        content = build_secrets_csv({"credentials_json": tricky}, FIELDS)
        rows = list(csv.reader(io.StringIO(content)))

        self.assertEqual(rows[0], ["key", "label", "value"])
        row = next(r for r in rows if r[0] == "credentials_json")
        self.assertEqual(row[2], tricky)

    def test_every_field_has_a_row_even_when_unset(self):
        rows = list(csv.reader(io.StringIO(build_secrets_csv({}, FIELDS))))
        self.assertEqual([r[0] for r in rows[1:]], [key for key, _ in FIELDS])


class BuildSecretsExportTest(unittest.TestCase):
    def test_rejects_unknown_format(self):
        with self.assertRaises(ValueError):
            build_secrets_export({}, FIELDS, "pdf")

    def test_dispatches_on_format(self):
        self.assertTrue(build_secrets_export({}, FIELDS, "CSV").startswith("key,label,value"))
        self.assertTrue(build_secrets_export({}, FIELDS, "txt").startswith("# eSpeleoSociety"))


class WriteSecretsExportTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def _path(self, name):
        return os.path.join(self.temp_dir, name)

    @unittest.skipIf(os.name == "nt", "POSIX file mode 0o600 is not supported on Windows")
    def test_file_is_owner_readable_only(self):
        path = self._path("out.txt")
        write_secrets_export(path, {"db_password": "x"}, FIELDS)
        mode = stat.S_IMODE(os.stat(path).st_mode)
        self.assertEqual(mode, 0o600, f"expected 0600, got {oct(mode)}")

    def test_format_is_inferred_from_the_extension(self):
        path = self._path("out.csv")
        self.assertEqual(write_secrets_export(path, {}, FIELDS), "csv")
        with open(path, encoding="utf-8") as handle:
            self.assertTrue(handle.read().startswith("key,label,value"))

    def test_explicit_format_overrides_the_extension(self):
        path = self._path("out.dat")
        self.assertEqual(write_secrets_export(path, {}, FIELDS, "csv"), "csv")

    def test_no_file_is_created_for_an_invalid_format(self):
        path = self._path("out.pdf")
        with self.assertRaises(ValueError):
            write_secrets_export(path, {}, FIELDS)
        self.assertFalse(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
