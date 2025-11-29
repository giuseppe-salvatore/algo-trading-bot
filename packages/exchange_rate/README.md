# Exchange Rate Package

A reusable abstraction layer for fetching historical exchange rates from multiple providers with intelligent caching and source tracking. Used by the [forex app](../../apps/forex/) for command-line exchange rate fetching.

## Overview

The Exchange Rate Proxy provides a unified interface for fetching USD to GBP (or other currency pair) exchange rates from different providers (exchangerate-api.com, APILayer, etc.) with:

- **Multi-provider support**: Switch between providers easily
- **Intelligent caching**: Cache rates with source tracking to avoid redundant API calls
- **Source enrichment**: Store rates from multiple sources for the same date (for comparison/validation)
- **Flexible configuration**: API keys via config file or environment variables
- **Dual interface**: Both class-based and function-based APIs

## Quick Start

### 1. Configuration

Create or edit `config/exchange_rates.json` in the project root:

```json
{
  "providers": {
    "exchangerate_api": {
      "api_key": "your_key_here_or_leave_empty_for_free_tier"
    },
    "apilayer": {
      "api_key": "your_apilayer_key"
    }
  },
  "cache": {
    "directory": "data/exchange-rates"
  }
}
```

**Or use environment variables** (takes precedence over config file):
```bash
export EXCHANGE_RATE_EXCHANGERATE_API_API_KEY="your_key"
export EXCHANGE_RATE_APILAYER_API_KEY="your_key"
```

### 2. Basic Usage

#### Function-based (Simple)

```python
from exchange_rate import get_exchange_rate, get_exchange_rates
from datetime import date

# Get a single rate
rate = get_exchange_rate(date(2025, 1, 15))
# Returns: {"date": "2025-01-15", "currency_pair": "USD/GBP", "rate": 0.7850, "source": "exchangerate_api"}

# Get multiple rates
dates = [date(2025, 1, 15), date(2025, 1, 16)]
rates = get_exchange_rates(dates)
# Returns: [{"date": "...", ...}, {"date": "...", ...}]
```

#### Class-based (Flexible)

```python
from exchange_rate import ExchangeRateProxy
from datetime import date

# Initialize proxy
proxy = ExchangeRateProxy(provider_name="exchangerate_api")

# Get a single rate
rate = proxy.get_rate(date(2025, 1, 15))

# Get multiple rates
rates = proxy.get_rates([date(2025, 1, 15), date(2025, 1, 16)])

# Get all sources for a date (if enriched from multiple providers)
all_sources = proxy.get_all_sources_for_date(date(2025, 1, 15))
# Returns: {"date": "2025-01-15", "currency_pair": "USD/GBP", "rates": {"exchangerate_api": 0.7850, "apilayer": 0.7852}}
```

### 3. Custom Configuration

```python
from exchange_rate import ExchangeRateProxy
from pathlib import Path

# Custom cache directory
proxy = ExchangeRateProxy(
    provider_name="exchangerate_api",
    cache_dir=Path("custom/cache/path")
)

# Custom config file
proxy = ExchangeRateProxy(
    provider_name="exchangerate_api",
    config_file=Path("custom/config.json")
)
```

## Features

### Caching

Rates are automatically cached in `data/exchange-rates/cache.json` (configurable). The cache:

- **Prevents redundant API calls**: Same date + same source = uses cache
- **Supports enrichment**: Different source + same date = adds to cache (doesn't overwrite)
- **Tracks sources**: Each cached rate includes which provider it came from

### Multi-Source Support

You can enrich your cache with rates from multiple providers:

```python
# Fetch from exchangerate-api.com
proxy1 = ExchangeRateProxy("exchangerate_api")
rate1 = proxy1.get_rate(date(2025, 1, 15))

# Fetch from APILayer (adds to cache, doesn't overwrite)
proxy2 = ExchangeRateProxy("apilayer")
rate2 = proxy2.get_rate(date(2025, 1, 15))

# Get all sources for comparison
all_sources = proxy1.get_all_sources_for_date(date(2025, 1, 15))
# {"rates": {"exchangerate_api": 0.7850, "apilayer": 0.7852}}
```

### Supported Providers

#### Phase 1 (Implemented)
- **exchangerate_api** (exchangerate-api.com)
  - Historical data requires paid plan (Pro, Business, or Volume)
  - Endpoint: `/v6/{API_KEY}/history/{BASE}/{YEAR}/{MONTH}/{DAY}`
  - Documentation: https://www.exchangerate-api.com/docs/historical-data-requests

- **openexchangerates** (openexchangerates.org)
  - Free tier: 1,000 requests/month
  - API key (app_id) required
  - Endpoint: `/api/historical/{YYYY-MM-DD}.json?app_id={app_id}`
  - Always uses USD as base currency
  - Documentation: https://openexchangerates.org/api

- **apilayer** (APILayer Currencylayer API)
  - Paid subscription required
  - API key required
  - Endpoint: `/currency_data/historical?date={YYYY-MM-DD}&access_key={api_key}`
  - Always uses USD as base currency
  - Documentation: https://docs.apilayer.com/currencylayer/docs/api-documentation

## Architecture

```
exchange_rate/
├── __init__.py              # Package exports
├── exchange_rate_config.py  # Configuration management
├── exchange_rate_providers.py # Provider implementations
└── exchange_rate_proxy.py   # Main proxy and cache manager
```

### Key Components

1. **ExchangeRateProvider** (abstract base class)
   - Defines interface for all providers
   - Implementations: `ExchangeRateAPIProvider`, `OpenExchangeRatesProvider`, `APILayerProvider`

2. **CacheManager**
   - Manages JSON-based cache
   - Handles multi-source enrichment
   - Prevents overwriting existing data

3. **ExchangeRateProxy**
   - Main interface class
   - Coordinates provider and cache
   - Provides both single and batch operations

## Cache Format

The cache file structure:

```json
{
  "metadata": {
    "last_updated": "2025-01-15T10:30:00Z",
    "version": "1.0"
  },
  "rates": {
    "2025-01-15": {
      "date": "2025-01-15",
      "currency_pair": "USD/GBP",
      "rates": {
        "exchangerate_api": 0.7850,
        "apilayer": 0.7852
      }
    }
  }
}
```

## Error Handling

The proxy handles errors gracefully:

- **API failures**: Returns `None`, logs warning
- **Invalid dates**: Returns `None`, logs warning
- **Missing config**: Uses defaults, logs warning
- **Cache errors**: Falls back to API, logs warning

## Use Cases

### Tax Reporting

For UK tax reporting, you need daily spot rates on transaction dates:

```python
from exchange_rate import get_exchange_rate
from datetime import date

# Get rate for a transaction date
transaction_date = date(2025, 1, 15)
rate_data = get_exchange_rate(transaction_date)

if rate_data:
    exchange_rate = rate_data["rate"]
    source = rate_data["source"]
    # Use rate for tax calculations
```

### Batch Processing

Process multiple dates efficiently (cached dates won't hit API):

```python
from exchange_rate import get_exchange_rates
from datetime import date, timedelta

# Get rates for a date range
start_date = date(2025, 1, 1)
dates = [start_date + timedelta(days=i) for i in range(30)]
rates = get_exchange_rates(dates)
```

## Requirements

- Python 3.12+
- `requests` library (for API calls)

## Related Documentation

- [apps/forex/README.md](../../apps/forex/README.md) - Forex app that uses this package
- [PLAN_FOR_CURRENCY_CONVERSION.md](../../../PLAN_FOR_CURRENCY_CONVERSION.md) - Overall currency conversion strategy
- [apps/tax-report/TAX_ACCOUNTING.md](../../apps/tax-report/TAX_ACCOUNTING.md) - Tax accounting methodology

