# banking/payment_link_factory.py
import os
import importlib
from banking.payment_link_interface import PaymentLinkGenerator

_implementations = {}


def _discover_implementations():
    """
    Dynamically discovers all classes that implement PaymentLinkGenerator
    in the banking package directory.
    """
    if _implementations:
        return

    current_dir = os.path.dirname(__file__)
    for filename in os.listdir(current_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = f"banking.{filename[:-3]}"
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                print(f"Could not import {module_name}: {e}")

    # Find all subclasses of PaymentLinkGenerator that were loaded
    for subclass in PaymentLinkGenerator.__subclasses__():
        _implementations[subclass.get_name()] = subclass


def get_available_generators() -> list:
    """Returns a list of names of all available payment link generators."""
    _discover_implementations()
    return list(_implementations.keys())


def get_payment_link_generator(name: str) -> PaymentLinkGenerator:
    """Factory method to get an instance of a payment link generator by name."""
    _discover_implementations()
    generator_class = _implementations.get(name)
    if not generator_class:
        raise ValueError(f"No payment link generator found with the name '{name}'")
    return generator_class()
