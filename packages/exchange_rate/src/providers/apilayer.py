#!/usr/bin/env python3
"""
Provider for APILayer Currencylayer API.

Historical endpoint: https://api.apilayer.com/currency_data/historical?date={date}&access_key={api_key}

Documentation: https://docs.apilayer.com/currencylayer/docs/api-documentation
"""

import json
from datetime import date

import requests

from .base import ExchangeRateProvider


class APILayerProvider(ExchangeRateProvider):
    """
    Provider for APILayer Currencylayer API.

    Historical endpoint: https://api.apilayer.com/currency_data/historical?date={date}&access_key={api_key}

    Documentation: https://docs.apilayer.com/currencylayer/docs/api-documentation
    """

    def __init__(self, api_key: str):
        """
        Initialize APILayer provider.

        Args:
            api_key: Required API key for APILayer
        """
        if not api_key:
            raise ValueError("API key is required for APILayer")
        self.api_key = api_key
        self.base_url = "https://api.apilayer.com/currency_data"

    @property
    def name(self) -> str:
        """Return provider name."""
        return "apilayer"

    def fetch_rate(
        self, transaction_date: date, from_currency: str = "USD", to_currency: str = "GBP"
    ) -> float | None:
        """
        Fetch exchange rate from APILayer.

        Args:
            transaction_date: Date to fetch rate for
            from_currency: Source currency (default: USD)
            to_currency: Target currency (default: GBP)

        Returns:
            Exchange rate as float, or None if fetch failed
        """

        headers = {"apikey": self.api_key}
        url = f"https://api.apilayer.com/exchangerates_data/{transaction_date}?symbols={to_currency}&base={from_currency}"

        try:
            payload = {}
            response = requests.request("GET", url, headers=headers, data=payload)
            data = json.loads(response.text)
            print(f"Getting rates for {transaction_date}: {data['rates'][to_currency]}")
            return float(data["rates"][to_currency])
        except (requests.RequestException, KeyError, ValueError) as e:
            print(f"Error fetching exchange rate for {date}: {e}")
            return None
