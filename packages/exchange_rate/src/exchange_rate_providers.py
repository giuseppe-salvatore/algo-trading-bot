#!/usr/bin/env python3
"""
Exchange rate provider implementations.

Abstract base class and concrete implementations for different exchange rate APIs.
"""

from abc import ABC, abstractmethod
from datetime import date

try:
    import requests
except ImportError:
    requests = None


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


class APILayerProvider(ExchangeRateProvider):
    """
    Provider for APILayer (placeholder for Phase 2).

    Will be implemented in Phase 2.
    """

    def __init__(self, api_key: str):
        """
        Initialize APILayer provider.

        Args:
            api_key: Required API key for APILayer
        """
        self.api_key = api_key

    @property
    def name(self) -> str:
        """Return provider name."""
        return "apilayer"

    def fetch_rate(
        self, transaction_date: date, from_currency: str = "USD", to_currency: str = "GBP"
    ) -> float | None:
        """
        Fetch exchange rate from APILayer (not yet implemented).

        Args:
            transaction_date: Date to fetch rate for
            from_currency: Source currency (default: USD)
            to_currency: Target currency (default: GBP)

        Returns:
            None (not implemented yet)
        """
        print("Warning: APILayer provider not yet implemented (Phase 2)")
        return None
