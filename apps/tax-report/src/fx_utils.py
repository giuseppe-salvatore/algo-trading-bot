#!/usr/bin/env python3
"""
Helper utilities for GBP conversion in tax reports.

This module provides a thin wrapper around the `exchange_rate` package so that
all FX lookups for the tax-report app are:
- Centralised in one place
- Configurable via a single provider name
- Easy to test/mocks in unit tests
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

# Import from exchange_rate package (same pattern as apps/forex)
try:
    # Preferred: installed via PDM workspace as a package
    from exchange_rate import ExchangeRateProxy
except ImportError:  # pragma: no cover - fallback path
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent.parent.parent
    src_path = project_root / "packages" / "exchange_rate" / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    from exchange_rate_proxy import ExchangeRateProxy


@dataclass(frozen=True)
class GBPConversionInfo:
    """Holds FX information for a single conversion into GBP."""

    rate: float
    provider: str
    rate_date: str
    from_currency: str
    to_currency: str

    def convert(self, amount: float) -> float:
        """Convert an amount in from_currency into GBP."""
        return amount * self.rate


def _normalise_date_string(timestamp: str) -> str:
    """
    Normalise an ISO timestamp or date string to YYYY-MM-DD.

    The taxable activities use full ISO timestamps with a trailing Z, while
    the exchange rate cache is keyed by date only.
    """
    # Fast path: already looks like a date-only string.
    if "T" not in timestamp and len(timestamp) >= 10:
        return timestamp[:10]

    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        # As a last resort, fall back to the first 10 characters which should
        # still give us YYYY-MM-DD for well-formed inputs.
        return timestamp[:10]

    return dt.date().isoformat()


def get_gbp_conversion_info(
    transaction_time: str,
    provider_name: str,
    from_currency: str = "USD",
    to_currency: str = "GBP",
    cache_dir: str | None = None,
    config_file: str | None = None,
) -> GBPConversionInfo | None:
    """
    Fetch (or load from cache) the FX rate for converting into GBP.

    Args:
        transaction_time: ISO timestamp string (or YYYY-MM-DD date string).
        provider_name: Name of the FX provider to use (must match exchange_rate).
        from_currency: Source currency (default: USD).
        to_currency: Target currency (default: GBP).
        cache_dir: Optional override for cache directory.
        config_file: Optional override for exchange rate config file.

    Returns:
        GBPConversionInfo instance, or None if the lookup fails.
    """
    date_str = _normalise_date_string(transaction_time)

    try:
        proxy = ExchangeRateProxy(
            provider_name=provider_name,
            cache_dir=cache_dir,
            config_file=config_file,
        )
    except ValueError:
        # Provider initialization failed (e.g., missing API key)
        # Silently skip GBP conversion - this allows CI/test runs without API keys
        return None

    result: dict[str, Any] | None = proxy.get_rate(
        transaction_date=date_str,
        from_currency=from_currency,
        to_currency=to_currency,
    )

    if not result:
        return None

    rate = float(result["rate"])
    return GBPConversionInfo(
        rate=rate,
        provider=result.get("source", provider_name),
        rate_date=result.get("date", date_str),
        from_currency=from_currency,
        to_currency=to_currency,
    )
