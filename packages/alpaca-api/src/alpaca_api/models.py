"""
Data models for Alpaca API responses.

Type definitions for activity data structures returned by the Alpaca API.
"""

from typing import Any

# Type alias for activity data (Alpaca returns dicts with various fields)
ActivityData = dict[str, Any]

# Common fields in activity responses
# Note: Actual fields vary by activity type, but these are common across many
COMMON_ACTIVITY_FIELDS = [
    "id",
    "account_id",
    "activity_type",
    "date",
    "net_amount",
    "symbol",
    "qty",
    "price",
    "side",
    "transaction_time",
    "type",
    "status",
]

# Dividend-specific fields
DIVIDEND_FIELDS = [
    "id",
    "account_id",
    "activity_type",
    "date",
    "net_amount",
    "symbol",
    "qty",
    "per_share_amount",
    "payable_date",
]

# Trade fill-specific fields
FILL_FIELDS = [
    "id",
    "account_id",
    "activity_type",
    "date",
    "net_amount",
    "symbol",
    "qty",
    "price",
    "side",
    "transaction_time",
    "order_id",
    "cum_qty",
    "leaves_qty",
    "position_effect",
]

# Name change-specific fields
NAME_CHANGE_FIELDS = [
    "id",
    "account_id",
    "activity_type",
    "date",
    "symbol",
    "old_symbol",
    "new_symbol",
]

# Split-specific fields
SPLIT_FIELDS = [
    "id",
    "account_id",
    "activity_type",
    "date",
    "symbol",
    "old_symbol",
    "new_symbol",
    "qty",
    "ratio",
]
