#!/usr/bin/env python3
"""
Provider for APILayer Currencylayer API.

Historical endpoint: https://api.apilayer.com/currency_data/historical?date={date}&access_key={api_key}

Documentation: https://docs.apilayer.com/currencylayer/docs/api-documentation
"""

from datetime import date

try:
    import requests
except ImportError:
    requests = None

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
        if requests is None:
            print("Error: requests library not installed")
            return None

        # Format date as YYYY-MM-DD
        date_str = transaction_date.isoformat()

        # Build URL: /historical?date={date}&access_key={api_key}
        url = f"{self.base_url}/historical"
        params = {
            "date": date_str,
            "access_key": self.api_key,
        }

        try:
            response = requests.get(url, params=params, timeout=10)

            # Check for HTTP errors first
            if response.status_code == 401:
                print("Warning: API key authentication failed (401 Unauthorized)")
                return None
            elif response.status_code == 403:
                print("Warning: API access forbidden (403). Check your subscription plan.")
                return None

            response.raise_for_status()
            data = response.json()

            # Check for error response
            if not data.get("success", False):
                error_info = data.get("error", {})
                error_code = error_info.get("code", "unknown")
                error_info_text = error_info.get("info", "Unknown error")
                print(
                    f"Warning: API error for {date_str}: {error_code} - {error_info_text}"
                )
                return None

            # APILayer always uses USD as base currency
            # Quotes are in format: "USDGBP", "USDEUR", etc.
            quotes = data.get("quotes", {})

            if from_currency == "USD":
                # Direct conversion from USD
                quote_key = f"USD{to_currency}"
                rate = quotes.get(quote_key)
                if rate is None:
                    print(f"Warning: {to_currency} rate not found in API response for {date_str}")
                    return None
                return float(rate)
            else:
                # Need to convert: from_currency -> USD -> to_currency
                # Get USD value of from_currency
                from_quote_key = f"USD{from_currency}"
                from_rate = quotes.get(from_quote_key)
                if from_rate is None:
                    print(
                        f"Warning: {from_currency} rate not found in API response for {date_str}"
                    )
                    return None

                # Get USD value of to_currency
                to_quote_key = f"USD{to_currency}"
                to_rate = quotes.get(to_quote_key)
                if to_rate is None:
                    print(f"Warning: {to_currency} rate not found in API response for {date_str}")
                    return None

                # Convert: (1 / from_rate) * to_rate = to_currency per from_currency
                # Example: USD/GBP = (1 / USD/USD) * USD/GBP = 1 * 0.785 = 0.785
                # Example: EUR/GBP = (1 / USD/EUR) * USD/GBP = (1 / 0.92) * 0.785 = 0.853
                return float(to_rate / from_rate)

        except requests.RequestException as e:
            date_str = transaction_date.isoformat()
            print(f"Warning: Failed to fetch exchange rate from API for {date_str}: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            print(f"Warning: Invalid API response for {transaction_date.isoformat()}: {e}")
            return None

