import importlib
import unittest


class UtilsImportabilityTest(unittest.TestCase):
    def test_utils_imports_without_optional_cloud_and_crypto_dependencies(self):
        module = importlib.import_module("utils")
        self.assertTrue(hasattr(module, "parse_camt053"))


if __name__ == "__main__":
    unittest.main()
