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
            response = requests.request("GET", url, headers=headers, data=payload, timeout=10)

            # Check HTTP status code first
            if response.status_code == 403:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", error_data.get("error", "Forbidden"))
                    print(
                        f"Warning: API returned 403 Forbidden for {transaction_date}: {error_msg}"
                    )
                except (ValueError, KeyError):
                    print(
                        f"Warning: API returned 403 Forbidden for {transaction_date}. "
                        "Check API key permissions."
                    )
                return None

            if response.status_code == 429:
                print(
                    f"Warning: API rate limit exceeded for {transaction_date}. "
                    "Please try again later."
                )
                return None

            if response.status_code == 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", error_data.get("error", "Bad Request"))
                    print(
                        f"Warning: API returned 400 Bad Request for {transaction_date}: {error_msg}"
                    )
                except (ValueError, KeyError):
                    print(f"Warning: API returned 400 Bad Request for {transaction_date}")
                return None

            response.raise_for_status()

            # Try to parse JSON response
            try:
                data = json.loads(response.text)
            except json.JSONDecodeError as e:
                print(f"Warning: Invalid JSON response for {transaction_date}: {e}")
                print(f"Response text (first 200 chars): {response.text[:200]}")
                return None

            # Check for error in response data
            if "error" in data:
                error_msg = data.get("message", data.get("error", "Unknown error"))
                print(f"Warning: API error for {transaction_date}: {error_msg}")
                return None

            # Extract rate from response
            if "rates" not in data:
                print(f"Warning: 'rates' key not found in API response for {transaction_date}")
                return None

            rates = data.get("rates", {})
            if to_currency not in rates:
                print(
                    f"Warning: {to_currency} rate not found in API response for {transaction_date}"
                )
                return None

            rate = float(rates[to_currency])
            print(f"Getting rates for {transaction_date}: {rate}")
            return rate

        except requests.RequestException as e:
            print(f"Warning: Request failed for {transaction_date}: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            print(f"Warning: Error parsing API response for {transaction_date}: {e}")
            return None
