"""
Alpaca API client package.

Provides a clean interface for fetching account activities (trade events,
dividends, etc.) from the Alpaca REST API.
"""

from alpaca_api.activity_types import (
    DIV,
    DIVIDENDS,
    FILL,
    MISC,
    NC,
    SPLIT,
    TRANS,
)
from alpaca_api.alpaca_client import AlpacaClient
from alpaca_api.alpaca_config import (
    get_api_key,
    get_api_secret,
    get_base_url,
    load_config,
)

__all__ = [
    "AlpacaClient",
    "load_config",
    "get_api_key",
    "get_api_secret",
    "get_base_url",
    # Activity type constants
    "DIV",
    "FILL",
    "NC",
    "SPLIT",
    "DIVIDENDS",
    "TRANS",
    "MISC",
]
