# Alpaca API Package

A reusable client library for fetching account activities (trade events, dividends, etc.) from the Alpaca REST API. Used by the [tax-report app](../../apps/tax-report/) for generating tax reports.

## Overview

The Alpaca API package provides a clean, typed interface for fetching account activities from Alpaca's REST API with:

- **Simple API**: Easy-to-use methods for fetching dividends, trade fills, and other activities
- **Automatic pagination**: Handles pagination automatically to fetch all results
- **Date filtering**: Filter activities by date range
- **Flexible configuration**: API keys via config file or environment variables
- **Type safety**: Typed data structures for better IDE support

## Quick Start

### 1. Configuration

Create or edit `config/alpaca-api.json` in the project root:

```json
{
  "api_key": "your_alpaca_api_key",
  "api_secret": "your_alpaca_api_secret",
  "base_url": "https://api.alpaca.markets",
  "environment": "live"
}
```

**Or use environment variables** (takes precedence over config file):
```bash
export ALPACA_API_KEY="your_api_key"
export ALPACA_API_SECRET="your_api_secret"
export ALPACA_ENVIRONMENT="live"  # or "paper"
```

### 2. Basic Usage

#### Using the client directly

```python
from alpaca_api import AlpacaClient, load_config

# Load configuration
config = load_config()

# Initialize client
client = AlpacaClient(
    api_key=config["api_key"],
    api_secret=config["api_secret"],
    base_url=config.get("base_url", "https://api.alpaca.markets")
)

# Fetch dividends for tax year
dividends = client.get_dividends(
    after="2024-04-06",
    until="2025-04-05"
)

# Fetch trade fills
fills = client.get_trade_fills(
    after="2024-04-06",
    until="2025-04-05"
)
```

#### Using convenience methods

```python
from alpaca_api import AlpacaClient, get_api_key, get_api_secret, get_base_url

# Initialize with helper functions
client = AlpacaClient(
    api_key=get_api_key(),
    api_secret=get_api_secret(),
    base_url=get_base_url()
)

# Fetch name changes
name_changes = client.get_name_changes(
    after="2024-01-01",
    until="2025-01-01"
)

# Fetch splits
splits = client.get_splits(
    after="2024-01-01",
    until="2025-01-01"
)
```

#### Fetching any activity type

```python
from alpaca_api import AlpacaClient, DIV, FILL

client = AlpacaClient(api_key="...", api_secret="...")

# Fetch any activity type
activities = client.get_activities(
    activity_type=DIV,
    after="2024-04-06",
    until="2025-04-05"
)

# Fetch with pagination control
first_page = client.get_activities(
    activity_type=FILL,
    after="2024-04-06",
    until="2025-04-05",
    fetch_all_pages=False  # Only fetch first page
)
```

## Features

### Automatic Pagination

The client automatically handles pagination to fetch all results:

```python
# This will fetch ALL dividends, not just the first page
dividends = client.get_dividends(after="2024-01-01", until="2025-01-01")
```

### Date Filtering

Filter activities by date range using `after` and `until` parameters:

```python
# Fetch activities in a specific tax year (UK tax year: April 6 to April 5)
dividends = client.get_dividends(
    after="2024-04-06",
    until="2025-04-05"
)
```

### Activity Types

The package provides constants for all activity types:

```python
from alpaca_api import DIV, FILL, NC, SPLIT, DIVIDENDS, TRANS, MISC

# Individual types
client.get_activities(DIV)
client.get_activities(FILL)

# Activity type groups
# DIVIDENDS includes: DIV, DIVCGL, DIVCGS, DIVFEE, DIVFT, DIVNRA, DIVROC, DIVTW, DIVTXEX
# TRANS includes: CSD, CSW, ACATC, ACATS
# MISC includes: INT, NC, SPLIT, MA, REORG, SPIN, etc.
```

See `activity_types.py` for the complete list of activity types.

## Supported Activity Types

### Trade Activities
- `FILL` - Order fills (both partial and full fills)
- `OPTRD` - Option trade

### Dividend Activities
- `DIV` - Dividends
- `DIVCGL` - Dividend (capital gain long term)
- `DIVCGS` - Dividend (capital gain short term)
- `DIVFEE` - Dividend fee
- `DIVFT` - Dividend adjusted (Foreign Tax Withheld)
- `DIVNRA` - Dividend adjusted (NRA Withheld)
- `DIVROC` - Dividend return of capital
- `DIVTW` - Dividend adjusted (Tefra Withheld)
- `DIVTXEX` - Dividend (tax exempt)

### Corporate Actions
- `NC` - Name change
- `SPLIT` - Stock split
- `MA` - Merger/Acquisition
- `REORG` - Reorg CA
- `SPIN` - Stock spinoff

### Cash Transactions
- `CSD` - Cash deposit (+)
- `CSW` - Cash withdrawal (-)
- `ACATC` - ACATS IN/OUT (Cash)
- `ACATS` - ACATS IN/OUT (Securities)

### Other Activities
- `INT` - Interest (credit/margin)
- `FEE` - Fee denominated in USD
- `JNL` - Journal entry
- And many more...

See `activity_types.py` for the complete list.

## Error Handling

The client provides clear error messages for common issues:

```python
try:
    dividends = client.get_dividends(after="2024-01-01")
except ValueError as e:
    if "Authentication failed" in str(e):
        print("Check your API key and secret")
    elif "Rate limit exceeded" in str(e):
        print("Too many requests, wait and try again")
```

## Configuration

### Config File

The config file `config/alpaca-api.json` supports:

- `api_key`: Your Alpaca API key
- `api_secret`: Your Alpaca API secret
- `base_url`: API base URL (defaults to live API)
- `environment`: "live" or "paper" (affects default base_url)

### Environment Variables

Environment variables take precedence over config file:

- `ALPACA_API_KEY` - API key
- `ALPACA_API_SECRET` - API secret
- `ALPACA_BASE_URL` - Base URL (optional)
- `ALPACA_ENVIRONMENT` - "live" or "paper" (optional)

If `ALPACA_ENVIRONMENT=paper` is set and `ALPACA_BASE_URL` is not set, the client will automatically use the paper trading API URL.

## Architecture

```
alpaca_api/
├── __init__.py              # Package exports
├── alpaca_config.py          # Configuration management
├── alpaca_client.py          # Main API client
├── activity_types.py         # Activity type constants
└── models.py                 # Type definitions
```

### Key Components

1. **AlpacaClient** (in `alpaca_client.py`)
   - Main client class for API interactions
   - Handles authentication, pagination, and error handling
   - Provides convenience methods for common activity types

2. **Configuration** (in `alpaca_config.py`)
   - Loads config from file and environment variables
   - Provides helper functions for getting credentials

3. **Activity Types** (in `activity_types.py`)
   - Constants for all activity types
   - Activity type groups for convenience

## Use Cases

### Tax Reporting

For UK tax reporting, fetch dividends and trade fills for a tax year:

```python
from alpaca_api import AlpacaClient, load_config

config = load_config()
client = AlpacaClient(
    api_key=config["api_key"],
    api_secret=config["api_secret"]
)

# Fetch dividends for tax year 2024-25 (April 6, 2024 to April 5, 2025)
dividends = client.get_dividends(
    after="2024-04-06",
    until="2025-04-05"
)

# Fetch trade fills for capital gains calculation
fills = client.get_trade_fills(
    after="2024-04-06",
    until="2025-04-05"
)
```

### Corporate Actions Tracking

Track name changes and splits:

```python
# Fetch all name changes
name_changes = client.get_name_changes(
    after="2020-01-01",
    until="2025-01-01"
)

# Fetch all splits
splits = client.get_splits(
    after="2020-01-01",
    until="2025-01-01"
)
```

## Requirements

- Python 3.12+
- `requests` library (for HTTP calls)

## Related Documentation

- [apps/tax-report/README.md](../../apps/tax-report/README.md) - Tax report app that uses this package
- [Alpaca API Documentation](https://alpaca.markets/docs/api-references/trading-api/) - Official Alpaca API docs
