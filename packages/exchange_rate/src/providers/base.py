#!/usr/bin/env python3
"""
Base class for exchange rate providers.

Abstract base class that all exchange rate providers must implement.
"""

from abc import ABC, abstractmethod
from datetime import date


class ExchangeRateProvider(ABC):
    """
    Abstract base class for exchange rate providers.

    All providers must implement fetch_rate() method.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name (e.g., 'exchangerate_api', 'apilayer')."""
        pass

    @abstractmethod
    def fetch_rate(
        self, transaction_date: date, from_currency: str = "USD", to_currency: str = "GBP"
    ) -> float | None:
        """
        Fetch exchange rate for a specific date.

        Args:
            transaction_date: Date to fetch rate for
            from_currency: Source currency (default: USD)
            to_currency: Target currency (default: GBP)

        Returns:
            Exchange rate as float, or None if fetch failed
        """
        pass

