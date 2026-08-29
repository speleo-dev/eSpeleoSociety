# banking/payme_slovakia.py
from urllib.parse import urlencode

import utils
from banking.payment_link_interface import PaymentLinkGenerator


class PaymentLinkV1_2Generator(PaymentLinkGenerator):
    """
    Generates a payment link based on the Slovak 'PaymentLink' standard v1.2.
    """

    @staticmethod
    def get_name() -> str:
        return "PAYME v1.2 (Slovakia)"

    def generate(self, amount: float, payment_id: str) -> str:
        """Generates a PaymentLink v1.2 URL."""
        iban = utils.get_iban()
        account_name = utils.get_account_name()
        currency = utils.get_membership_currency()
        year = utils.get_membership_fee_year()

        if not all([iban, account_name, currency]):
            raise ValueError("IBAN, account_name, or membership_currency is missing from config.properties")

        params = {
            "V": "1",
            "IBAN": iban,
            "AM": f"{amount:.2f}",
            "CC": currency.upper(),
            "PI": payment_id,
            "MSG": f"Členský poplatok za rok {year}",
            "CN": account_name,
        }
        return f"https://payme.sk?{urlencode(params)}"


class PaymentLinkV2Generator(PaymentLinkGenerator):
    """
    Generates a payment link based on the Slovak 'PaymentLink' standard v2.0.
    """

    @staticmethod
    def get_name() -> str:
        return "PAYME v2.0 (Slovakia)"

    def generate(self, amount: float, payment_id: str) -> str:
        """Generates a PaymentLink v2.0 URL."""
        iban = utils.get_iban()
        account_name = utils.get_account_name()
        currency = utils.get_membership_currency()
        year = utils.get_membership_fee_year()

        if not all([iban, account_name, currency]):
            raise ValueError("IBAN, account_name, or membership_currency is missing from config.properties")

        params = {
            "IBAN": iban,
            "AM": f"{amount:.2f}",
            "CC": currency.upper(),
            "PI": payment_id,
            "MSG": f"Členský poplatok za rok {year}",
            "CN": account_name,
        }
        return f"https://payme.sk/2/m/PME?{urlencode(params)}"
