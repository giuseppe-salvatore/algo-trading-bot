# Forex App

Forex exchange rate fetching and management tools for currency conversion in tax reporting and financial analysis.

## Overview

This app provides command-line tools for fetching historical exchange rates from multiple providers with intelligent caching support. It uses the `exchange_rate` package to abstract away provider-specific details and automatically cache fetched rates to minimize API calls.

**Key Features:**
- Fetch exchange rates for date ranges
- Support for multiple currency pairs (USD/GBP, EUR/GBP, etc.)
- Multiple provider support (exchangerate-api.com, openexchangerates.org, APILayer)
- Automatic caching to reduce API calls
- Formatted table output with aligned columns
- Optional CSV export

## Installation

The app is part of the monorepo workspace. Install dependencies:

```bash
pdm install
```

## Usage

### Using `just` (Recommended)

The easiest way to run the forex tools is using the `justfile`:

```bash
# Fetch USD/GBP rates for a date range
just fetch-rates 15-01-2024 20-01-2024 USD/GBP

# Use a different provider
just fetch-rates 15-01-2024 20-01-2024 USD/GBP --provider openexchangerates

# Save output to CSV file
just fetch-rates 01-01-2024 31-01-2024 USD/GBP --output data/rates_jan_2024.csv
```

### Using PDM Directly

You can also run the script directly with PDM:

```bash
./venv/bin/pdm run -p apps/forex python apps/forex/src/fetch_rates.py <start-date> <end-date> <currency_pair>
```

### Command Reference

**fetch-rates**

Fetch exchange rates for a date range.

**Syntax:**
```bash
fetch-rates <start-date> <end-date> <currency_pair> [--provider PROVIDER] [--output FILE]
```

**Arguments:**
- `start-date`: Start date in DD-MM-YYYY format (e.g., `15-01-2024`)
- `end-date`: End date in DD-MM-YYYY format (e.g., `20-01-2024`)
- `currency_pair`: Currency pair in FROM/TO format (e.g., `USD/GBP`)

**Options:**
- `--provider`: Exchange rate provider to use (default: `exchangerate_api`)
  - Available providers: `exchangerate_api`, `openexchangerates`, `apilayer`
- `--output`, `-o`: Output file path (CSV format). If not specified, prints to stdout

**Currency Pair Formats:**
- `USD/GBP` (recommended)
- `USD-GBP`
- `USD_GBP`

**Examples:**

```bash
# Fetch USD/GBP rates for a week
just fetch-rates 15-01-2024 20-01-2024 USD/GBP

# Fetch rates for a month and save to file
just fetch-rates 01-01-2024 31-01-2024 USD/GBP --output data/rates_jan_2024.csv

# Use different provider (openexchangerates.org)
just fetch-rates 15-01-2024 20-01-2024 USD/GBP --provider openexchangerates
```

**Output Format:**

The output is a formatted table with aligned columns:

```
Date       | Currency Pair |     Rate | Source           
---------------------------------------------------------
2024-01-15 | USD/GBP       | 0.786436 | openexchangerates
2024-01-16 | USD/GBP       | 0.791321 | openexchangerates
2024-01-17 | USD/GBP       | 0.788835 | openexchangerates
```

When using `--output`, the same format is written to a CSV file.

## Configuration

The app uses the `exchange_rate` package for fetching rates. Configure API keys in `config/exchange_rates.json` or via environment variables.

### Config File

Create or edit `config/exchange_rates.json` in the project root:

```json
{
  "providers": {
    "exchangerate_api": {
      "api_key": "your_key_here"
    },
    "openexchangerates": {
      "api_key": "your_key_here"
    },
    "apilayer": {
      "api_key": "your_key_here"
    }
  },
  "cache": {
    "directory": "data/exchange-rates"
  }
}
```

### Environment Variables

You can also set API keys via environment variables (takes precedence over config file):

```bash
export EXCHANGE_RATE_EXCHANGERATE_API_API_KEY="your_key"
export EXCHANGE_RATE_OPENEXCHANGERATES_API_KEY="your_key"
export EXCHANGE_RATE_APILAYER_API_KEY="your_key"
```

### Cache

Fetched rates are automatically cached in `data/exchange-rates/cache.json` (configurable). This prevents redundant API calls when fetching the same dates multiple times.

For detailed configuration options and provider-specific requirements, see [packages/exchange_rate/README.md](../../packages/exchange_rate/README.md).

## Dependencies

- `exchange_rate` package - Exchange rate proxy abstraction layer
- `requests` - HTTP library for API calls

## Use Cases

### Tax Reporting

For UK tax reporting, you need daily spot rates on transaction dates. This tool helps you fetch and cache these rates:

```bash
# Fetch rates for all trading dates in a fiscal year
just fetch-rates 06-04-2023 05-04-2024 USD/GBP --output data/fy_2023_24_rates.csv
```

### Currency Conversion Analysis

Compare rates from different providers or analyze rate trends:

```bash
# Fetch from multiple providers and compare
just fetch-rates 01-01-2024 31-01-2024 USD/GBP --provider exchangerate_api
just fetch-rates 01-01-2024 31-01-2024 USD/GBP --provider openexchangerates
```

## Related Documentation

- [packages/exchange_rate/README.md](../../packages/exchange_rate/README.md) - Exchange rate package documentation
- [PLAN_FOR_CURRENCY_CONVERSION.md](../../PLAN_FOR_CURRENCY_CONVERSION.md) - Currency conversion strategy

