# banking/payment_link_interface.py
from abc import ABC, abstractmethod


class PaymentLinkGenerator(ABC):
    """
    Interface for generating country-specific payment links or QR code data.
    """

    @staticmethod
    @abstractmethod
    def get_name() -> str:
        """Returns the user-friendly name of this payment implementation."""
        pass

    @abstractmethod
    def generate(self, amount: float, payment_id: str) -> str:
        """Generates the final payment URL."""
        pass
