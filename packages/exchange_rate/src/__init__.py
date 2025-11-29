"""
Exchange rate proxy abstraction layer.

Provides interfaces for fetching exchange rates from multiple providers
with caching and source tracking.
"""

from exchange_rate_proxy import (
    ExchangeRateProxy,
    get_exchange_rate,
    get_exchange_rates,
)

__all__ = [
    "ExchangeRateProxy",
    "get_exchange_rate",
    "get_exchange_rates",
]
