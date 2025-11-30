#!/usr/bin/env python3
"""
Provider for exchangerate-api.com.

Historical data requires a paid plan (Pro, Business, or Volume).
Endpoint: https://v6.exchangerate-api.com/v6/{API_KEY}/history/{BASE}/{YEAR}/{MONTH}/{DAY}

Documentation: https://www.exchangerate-api.com/docs/historical-data-requests
"""

from datetime import date

try:
    import requests
except ImportError:
    requests = None

from .base import ExchangeRateProvider


class ExchangeRateAPIProvider(ExchangeRateProvider):
    """
    Provider for exchangerate-api.com.

    Historical data requires a paid plan (Pro, Business, or Volume).
    Endpoint: https://v6.exchangerate-api.com/v6/{API_KEY}/history/{BASE}/{YEAR}/{MONTH}/{DAY}

    Documentation: https://www.exchangerate-api.com/docs/historical-data-requests
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize exchangerate-api.com provider.

        Args:
            api_key: Required API key for historical data (paid plans only)
        """
        if not api_key:
            raise ValueError(
                "API key is required for exchangerate-api.com historical data. "
                "Historical data is only available for paid plans (Pro, Business, or Volume)."
            )
        self.api_key = api_key
        self.base_url = "https://v6.exchangerate-api.com/v6"

    @property
    def name(self) -> str:
        """Return provider name."""
        return "exchangerate_api"

    def fetch_rate(
        self, transaction_date: date, from_currency: str = "USD", to_currency: str = "GBP"
    ) -> float | None:
        """
        Fetch exchange rate from exchangerate-api.com.

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

        # Format date as YEAR/MONTH/DAY (no leading zeros)
        # Documentation requires: YEAR/MONTH/DAY format without leading zeros
        year = transaction_date.year
        month = transaction_date.month  # No leading zero
        day = transaction_date.day  # No leading zero

        # Build URL: /v6/{API_KEY}/history/{BASE}/{YEAR}/{MONTH}/{DAY}
        url = f"{self.base_url}/{self.api_key}/history/{from_currency}/{year}/{month}/{day}"

        try:
            response = requests.get(url, timeout=10)

            # Check for HTTP errors first
            if response.status_code == 403:
                # Try to parse error response
                try:
                    error_data = response.json()
                    error_type = error_data.get("error-type", "forbidden")
                    if error_type == "plan-upgrade-required":
                        print(
                            "Warning: Historical data requires a paid plan "
                            "(Pro, Business, or Volume). "
                            "Your API key may be on the free tier."
                        )
                    else:
                        print(f"Warning: API returned 403 Forbidden: {error_type}")
                except (ValueError, KeyError):
                    print(
                        "Warning: API returned 403 Forbidden. Historical data requires a paid plan."
                    )
                return None

            response.raise_for_status()
            data = response.json()

            # Check for error response
            if data.get("result") == "error":
                error_type = data.get("error-type", "unknown")
                print(f"Warning: API error for {transaction_date.isoformat()}: {error_type}")
                return None

            # Extract rate from response
            # Response format: {"conversion_rates": {"GBP": 0.7850, ...}, "base_code": "USD", ...}
            conversion_rates = data.get("conversion_rates", {})
            rate = conversion_rates.get(to_currency)

            if rate is None:
                date_str = transaction_date.isoformat()
                print(f"Warning: {to_currency} rate not found in API response for {date_str}")
                return None

            return float(rate)

        except requests.RequestException as e:
            date_str = transaction_date.isoformat()
            print(f"Warning: Failed to fetch exchange rate from API for {date_str}: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            print(f"Warning: Invalid API response for {transaction_date.isoformat()}: {e}")
            return None
