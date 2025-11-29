# Forex App

Forex exchange rate fetching and management tools.

## Overview

This app provides command-line tools for fetching historical exchange rates from multiple providers with caching support.

## Installation

The app is part of the monorepo workspace. Install dependencies:

```bash
pdm install
```

## Usage

### fetch-rates

Fetch exchange rates for a date range.

```bash
fetch-rates <start-date> <end-date> <currency_pair>
```

**Arguments:**
- `start-date`: Start date in DD-MM-YYYY format (e.g., `15-01-2024`)
- `end-date`: End date in DD-MM-YYYY format (e.g., `20-01-2024`)
- `currency_pair`: Currency pair in FROM/TO format (e.g., `USD/GBP`)

**Options:**
- `--provider`: Exchange rate provider to use (default: `exchangerate_api`)
- `--output`, `-o`: Output file path (CSV format). If not specified, prints to stdout

**Currency Pair Formats:**
- `USD/GBP` (recommended)
- `USD-GBP`
- `USD_GBP`

**Examples:**

```bash
# Fetch USD/GBP rates for a week
fetch-rates 15-01-2024 20-01-2024 USD/GBP

# Fetch rates for a month and save to file
fetch-rates 01-01-2024 31-01-2024 USD/GBP --output data/rates_jan_2024.csv

# Use different provider
fetch-rates 15-01-2024 20-01-2024 USD/GBP --provider apilayer
```

**Output Format:**

```
Date | Currency Pair | Rate | Source
------------------------------------------------------------
2024-01-15 | USD/GBP | 0.785000 | exchangerate_api
2024-01-16 | USD/GBP | 0.785200 | exchangerate_api
...
```

## Configuration

The app uses the exchange rate proxy from the `common` package. Configure API keys in `config/exchange_rates.json` or via environment variables.

See [packages/common/src/common/exchange_rate/README.md](../../packages/common/src/common/exchange_rate/README.md) for configuration details.

## Dependencies

- `common` package (exchange_rate module)
- `requests` (via common package)

