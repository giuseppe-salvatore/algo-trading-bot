#!/usr/bin/env python3
"""
Provider for openexchangerates.org.

Free tier: 1,000 requests/month
Historical endpoint: https://openexchangerates.org/api/historical/{date}.json?app_id={app_id}

Documentation: https://openexchangerates.org/api
"""

from datetime import date

try:
    import requests
except ImportError:
    requests = None

from .base import ExchangeRateProvider


class OpenExchangeRatesProvider(ExchangeRateProvider):
    """
    Provider for openexchangerates.org.

    Free tier: 1,000 requests/month
    Historical endpoint: https://openexchangerates.org/api/historical/{date}.json?app_id={app_id}

    Documentation: https://openexchangerates.org/api
    """

    def __init__(self, api_key: str):
        """
        Initialize openexchangerates.org provider.

        Args:
            api_key: Required API key (app_id) for openexchangerates.org
        """
        if not api_key:
            raise ValueError("API key (app_id) is required for openexchangerates.org")
        self.api_key = api_key
        self.base_url = "https://openexchangerates.org/api"

    @property
    def name(self) -> str:
        """Return provider name."""
        return "openexchangerates"

    def fetch_rate(
        self, transaction_date: date, from_currency: str = "USD", to_currency: str = "GBP"
    ) -> float | None:
        """
        Fetch exchange rate from openexchangerates.org.

        Args:
            transaction_date: Date to fetch rate for
            from_currency: Source currency (default: USD)
            to_currency: Target currency (default: GBP)

        Returns:
            Exchange rate as float, or None if fetch failed
        """
        if requests is None:
            print("Error: requests library not installed")
            return None

        # Format date as YYYY-MM-DD
        date_str = transaction_date.isoformat()

        # Build URL: /historical/{date}.json?app_id={app_id}
        url = f"{self.base_url}/historical/{date_str}.json"
        params = {"app_id": self.api_key}

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Check for error response
            if "error" in data:
                error_msg = data.get("description", data.get("error", "Unknown error"))
                print(f"Warning: API error for {date_str}: {error_msg}")
                return None

            # OpenExchangeRates always uses USD as base
            # If from_currency is not USD, we need to convert
            rates = data.get("rates", {})

            if from_currency == "USD":
                # Direct conversion from USD
                rate = rates.get(to_currency)
                if rate is None:
                    print(f"Warning: {to_currency} rate not found in API response for {date_str}")
                    return None
                return float(rate)
            else:
                # Need to convert: from_currency -> USD -> to_currency
                # Get USD value of from_currency
                from_rate = rates.get(from_currency)
                if from_rate is None:
                    print(f"Warning: {from_currency} rate not found in API response for {date_str}")
                    return None

                # Get USD value of to_currency
                to_rate = rates.get(to_currency)
                if to_rate is None:
                    print(f"Warning: {to_currency} rate not found in API response for {date_str}")
                    return None

                # Convert: (1 / from_rate) * to_rate = to_currency per from_currency
                # Example: USD/GBP = (1 / USD/USD) * USD/GBP = 1 * 0.785 = 0.785
                # Example: EUR/GBP = (1 / USD/EUR) * USD/GBP = (1 / 0.92) * 0.785 = 0.853
                return float(to_rate / from_rate)

        except requests.RequestException as e:
            print(f"Warning: Failed to fetch exchange rate from API for {date_str}: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            print(f"Warning: Invalid API response for {date_str}: {e}")
            return None

