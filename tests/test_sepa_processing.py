from decimal import Decimal
from types import SimpleNamespace
import unittest

from sepa_processing import process_transactions


class SepaProcessingTest(unittest.TestCase):
    def test_process_transactions_returns_valid_payment_for_active_member(self):
        parsed = {
            "transactions": [
                {
                    "ecp_hash_candidate": "ecp-1",
                    "amount": "20.00",
                    "currency": "EUR",
                    "transaction_date": "2026-01-10",
                }
            ]
        }
        member = SimpleNamespace(first_name="Ada", last_name="Lovelace", discounted_membership=False)
        ecp = SimpleNamespace(member_id=7, is_ecp_active=True)

        result = process_transactions(
            parsed,
            normal_fee=Decimal("20.00"),
            discounted_fee=Decimal("10.00"),
            fetch_ecp=lambda value: ecp if value == "ecp-1" else None,
            fetch_member_by_id=lambda value: member if value == 7 else None,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "valid")
        self.assertEqual(result[0]["name_or_iban"], "Ada Lovelace")
        self.assertEqual(result[0]["bg_color"], "lightgreen")

    def test_process_transactions_returns_list_for_unknown_reference(self):
        parsed = {
            "transactions": [
                {
                    "ecp_hash_candidate": "missing",
                    "amount": "20.00",
                    "currency": "EUR",
                    "debtor_account_iban": "SK00",
                }
            ]
        }

        result = process_transactions(
            parsed,
            normal_fee=Decimal("20.00"),
            discounted_fee=Decimal("10.00"),
            fetch_ecp=lambda value: None,
            fetch_member_by_id=lambda value: None,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "unknown_reference_expected_amount")
        self.assertEqual(result[0]["name_or_iban"], "SK00")
        self.assertEqual(result[0]["text_color"], "darkGreen")


if __name__ == "__main__":
    unittest.main()
