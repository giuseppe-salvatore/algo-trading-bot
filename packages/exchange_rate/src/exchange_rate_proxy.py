#!/usr/bin/env python3
"""
Exchange rate proxy abstraction layer.

Provides both class-based and function-based interfaces for fetching
exchange rates with caching and multi-provider support.
"""

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

from exchange_rate_config import get_cache_directory, get_provider_api_key
from exchange_rate_providers import (
    APILayerProvider,
    ExchangeRateAPIProvider,
    ExchangeRateProvider,
    OpenExchangeRatesProvider,
)

# Set up logging
logger = logging.getLogger(__name__)


class CacheManager:
    """Manages exchange rate cache with support for multiple sources per date."""

    def __init__(self, cache_file: str | Path):
        """
        Initialize cache manager.

        Args:
            cache_file: Path to cache JSON file
        """
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_data: dict[str, Any] = self._load_cache()

    def _load_cache(self) -> dict[str, Any]:
        """Load cache from JSON file."""
        if not self.cache_file.exists():
            return {
                "metadata": {
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0",
                },
                "rates": {},
            }

        try:
            with open(self.cache_file) as f:
                data = json.load(f)
                # Ensure structure is correct
                if "rates" not in data:
                    data["rates"] = {}
                if "metadata" not in data:
                    data["metadata"] = {
                        "last_updated": datetime.now().isoformat(),
                        "version": "1.0",
                    }
                return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not load cache file {self.cache_file}: {e}")
            return {
                "metadata": {
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0",
                },
                "rates": {},
            }

    def save_cache(self) -> None:
        """Save cache to JSON file."""
        try:
            self.cache_data["metadata"]["last_updated"] = datetime.now().isoformat()
            with open(self.cache_file, "w") as f:
                json.dump(self.cache_data, f, indent=2)
        except OSError as e:
            logger.warning(f"Could not save cache file {self.cache_file}: {e}")

    def has_rate(self, date_str: str, source: str) -> bool:
        """
        Check if rate exists for date and source.

        Args:
            date_str: Date string (YYYY-MM-DD)
            source: Provider source name

        Returns:
            True if rate exists, False otherwise
        """
        if date_str not in self.cache_data["rates"]:
            return False

        rate_entry = self.cache_data["rates"][date_str]
        return source in rate_entry.get("rates", {})

    def get_rate(self, date_str: str, source: str) -> float | None:
        """
        Get rate for date and source from cache.

        Args:
            date_str: Date string (YYYY-MM-DD)
            source: Provider source name

        Returns:
            Rate as float, or None if not found
        """
        if not self.has_rate(date_str, source):
            return None

        rate_entry = self.cache_data["rates"][date_str]
        return rate_entry.get("rates", {}).get(source)

    def add_rate(
        self,
        date_str: str,
        rate: float,
        source: str,
        currency_pair: str = "USD/GBP",
    ) -> None:
        """
        Add rate to cache (enrich, don't overwrite).

        If rate already exists for same date+source, skip (don't overwrite).
        If rate exists for same date but different source, add to rates object.

        Args:
            date_str: Date string (YYYY-MM-DD)
            rate: Exchange rate value
            source: Provider source name
            currency_pair: Currency pair (default: USD/GBP)
        """
        if date_str not in self.cache_data["rates"]:
            self.cache_data["rates"][date_str] = {
                "date": date_str,
                "currency_pair": currency_pair,
                "rates": {},
            }

        rate_entry = self.cache_data["rates"][date_str]

        # Don't overwrite if same source already exists
        if source in rate_entry.get("rates", {}):
            logger.debug(f"Rate for {date_str} from {source} already exists, skipping")
            return

        # Add rate (enrichment)
        rate_entry["rates"][source] = rate
        rate_entry["currency_pair"] = currency_pair  # Update currency pair

    def get_all_sources_for_date(self, date_str: str) -> dict[str, Any] | None:
        """
        Get all cached rates for a date from all sources.

        Args:
            date_str: Date string (YYYY-MM-DD)

        Returns:
            Dictionary with date, currency_pair, and rates dict, or None if not found
        """
        if date_str not in self.cache_data["rates"]:
            return None

        return self.cache_data["rates"][date_str].copy()


class ExchangeRateProxy:
    """
    Main proxy class for fetching exchange rates with caching.

    Supports multiple providers and caches rates with source tracking.
    """

    # Provider registry
    _providers: dict[str, type[ExchangeRateProvider]] = {
        "exchangerate_api": ExchangeRateAPIProvider,
        "openexchangerates": OpenExchangeRatesProvider,
        "apilayer": APILayerProvider,
    }

    def __init__(
        self,
        provider_name: str = "exchangerate_api",
        cache_dir: str | Path | None = None,
        config_file: str | Path | None = None,
    ):
        """
        Initialize exchange rate proxy.

        Args:
            provider_name: Name of provider to use (default: "exchangerate_api")
            cache_dir: Optional cache directory (default: from config)
            config_file: Optional config file path (default: config/exchange_rates.json)
        """
        self.provider_name = provider_name
        self.config_file = config_file

        # Get cache directory
        if cache_dir is None:
            cache_dir = get_cache_directory(config_file)
        else:
            cache_dir = Path(cache_dir)

        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "cache.json"

        # Initialize cache manager
        self.cache = CacheManager(cache_file)

        # Initialize provider
        self.provider = self._create_provider(provider_name, config_file)

    def _create_provider(
        self, provider_name: str, config_file: str | Path | None
    ) -> ExchangeRateProvider:
        """
        Create provider instance.

        Args:
            provider_name: Name of provider
            config_file: Optional config file path

        Returns:
            Provider instance

        Raises:
            ValueError: If provider name is not recognized
        """
        if provider_name not in self._providers:
            raise ValueError(
                f"Unknown provider: {provider_name}. Available: {', '.join(self._providers.keys())}"
            )

        provider_class = self._providers[provider_name]
        api_key = get_provider_api_key(provider_name, config_file)

        if provider_name == "exchangerate_api":
            return provider_class(api_key if api_key else None)
        elif provider_name in ["openexchangerates", "apilayer"]:
            if not api_key:
                raise ValueError(f"API key required for provider: {provider_name}")
            return provider_class(api_key)
        else:
            return provider_class(api_key)

    def get_rate(
        self,
        transaction_date: date | str,
        from_currency: str = "USD",
        to_currency: str = "GBP",
    ) -> dict[str, Any] | None:
        """
        Get exchange rate for a specific date.

        Checks cache first, then fetches from provider if needed.

        Args:
            transaction_date: Date to fetch rate for (date object or YYYY-MM-DD string)
            from_currency: Source currency (default: USD)
            to_currency: Target currency (default: GBP)

        Returns:
            Dictionary with date, currency_pair, rate, and source, or None if failed
        """
        # Normalize date
        if isinstance(transaction_date, str):
            date_obj = datetime.fromisoformat(transaction_date).date()
            date_str = (
                transaction_date.split("T")[0] if "T" in transaction_date else transaction_date
            )
        else:
            date_obj = transaction_date
            date_str = transaction_date.isoformat()

        currency_pair = f"{from_currency}/{to_currency}"

        # Check cache first
        if self.cache.has_rate(date_str, self.provider.name):
            rate = self.cache.get_rate(date_str, self.provider.name)
            if rate is not None:
                logger.debug(f"Using cached rate for {date_str} from {self.provider.name}")
                return {
                    "date": date_str,
                    "currency_pair": currency_pair,
                    "rate": rate,
                    "source": self.provider.name,
                    "cached": True,
                }

        # Fetch from provider
        logger.debug(f"Fetching rate for {date_str} from {self.provider.name}")
        rate = self.provider.fetch_rate(date_obj, from_currency, to_currency)

        if rate is None:
            logger.warning(f"Failed to fetch rate for {date_str} from {self.provider.name}")
            return None

        # Cache the rate
        self.cache.add_rate(date_str, rate, self.provider.name, currency_pair)
        self.cache.save_cache()

        return {
            "date": date_str,
            "currency_pair": currency_pair,
            "rate": rate,
            "source": self.provider.name,
            "cached": False,
        }

    def get_rates(
        self,
        dates: list[date] | list[str],
        from_currency: str = "USD",
        to_currency: str = "GBP",
    ) -> list[dict[str, Any]]:
        """
        Get exchange rates for multiple dates (batch fetch).

        Args:
            dates: List of dates (date objects or YYYY-MM-DD strings)
            from_currency: Source currency (default: USD)
            to_currency: Target currency (default: GBP)

        Returns:
            List of rate dictionaries (same format as get_rate)
        """
        results = []
        for date_val in dates:
            rate = self.get_rate(date_val, from_currency, to_currency)
            if rate:
                results.append(rate)
        return results

    def get_all_sources_for_date(self, transaction_date: date | str) -> dict[str, Any] | None:
        """
        Get all cached rates for a date from all sources.

        Args:
            transaction_date: Date to query (date object or YYYY-MM-DD string)

        Returns:
            Dictionary with date, currency_pair, and rates dict, or None if not found
        """
        # Normalize date
        if isinstance(transaction_date, str):
            date_str = (
                transaction_date.split("T")[0] if "T" in transaction_date else transaction_date
            )
        else:
            date_str = transaction_date.isoformat()

        return self.cache.get_all_sources_for_date(date_str)


# Function-based convenience wrappers


def get_exchange_rate(
    transaction_date: date | str,
    provider: str = "exchangerate_api",
    from_currency: str = "USD",
    to_currency: str = "GBP",
    cache_dir: str | Path | None = None,
    config_file: str | Path | None = None,
) -> dict[str, Any] | None:
    """
    Get exchange rate (function-based interface).

    Args:
        transaction_date: Date to fetch rate for
        provider: Provider name (default: "exchangerate_api")
        from_currency: Source currency (default: USD)
        to_currency: Target currency (default: GBP)
        cache_dir: Optional cache directory
        config_file: Optional config file path

    Returns:
        Dictionary with date, currency_pair, rate, and source, or None if failed
    """
    proxy = ExchangeRateProxy(provider, cache_dir, config_file)
    return proxy.get_rate(transaction_date, from_currency, to_currency)


def get_exchange_rates(
    dates: list[date] | list[str],
    provider: str = "exchangerate_api",
    from_currency: str = "USD",
    to_currency: str = "GBP",
    cache_dir: str | Path | None = None,
    config_file: str | Path | None = None,
) -> list[dict[str, Any]]:
    """
    Get exchange rates for multiple dates (function-based interface).

    Args:
        dates: List of dates to fetch rates for
        provider: Provider name (default: "exchangerate_api")
        from_currency: Source currency (default: USD)
        to_currency: Target currency (default: GBP)
        cache_dir: Optional cache directory
        config_file: Optional config file path

    Returns:
        List of rate dictionaries
    """
    proxy = ExchangeRateProxy(provider, cache_dir, config_file)
    return proxy.get_rates(dates, from_currency, to_currency)
