# Fetch Dividends App

Fetch dividend activities from Alpaca API and save to timestamped daily folders.

## Overview

This app uses the `alpaca-api` package to fetch dividend activities (DIV) from Alpaca's API and saves them to `dividends.json` in a timestamped folder.

All data is saved to timestamped folders in `data/dividends/alpaca/live/YYYY-MM-DD/` to avoid overriding existing data.

## Installation

The app is part of the monorepo workspace. Install dependencies:

```bash
pdm install
```

## Usage

### Basic Usage

Fetch all dividend activities (saves to today's date folder):

```bash
pdm run -p apps/fetch-dividends python apps/fetch-dividends/src/fetch_dividends.py
```

Or using the script command (after installation):

```bash
fetch-dividends
```

### With Date Filtering

Fetch dividends for a specific date range:

```bash
fetch-dividends --after 2024-01-01 --until 2024-12-31
```

### Custom Output Directory

Use a custom output directory (for testing):

```bash
fetch-dividends --output-dir data/dividends/alpaca/test
```

## Command Reference

**fetch-dividends**

Fetch dividend activities from Alpaca API.

**Syntax:**
```bash
fetch-dividends [--after DATE] [--until DATE] [--output-dir PATH]
```

**Options:**
- `--after DATE`: Fetch dividends after this date (YYYY-MM-DD format)
- `--until DATE`: Fetch dividends until this date (YYYY-MM-DD format)
- `--output-dir PATH`: Base output directory (default: `data/dividends/alpaca/live`)

## Output Structure

The app creates a timestamped folder for each day it runs:

```
data/dividends/alpaca/live/YYYY-MM-DD/
└── dividends.json  # DIV activities (dividends)
```

**Date Format:** `YYYY-MM-DD` (e.g., `2025-01-15`)

**Note:** If run multiple times on the same day, files will be overwritten (expected behavior).

## Configuration

The app uses the `alpaca-api` package for API access. Configure API credentials in `config/alpaca-api.json` or via environment variables.

### Config File

Create or edit `config/alpaca-api.json` in the project root:

```json
{
  "api_key": "your_api_key_here",
  "api_secret": "your_api_secret_here",
  "base_url": "https://api.alpaca.markets",
  "environment": "live"
}
```

### Environment Variables

You can also set credentials via environment variables (takes precedence over config file):

```bash
export ALPACA_API_KEY="your_api_key"
export ALPACA_API_SECRET="your_api_secret"
export ALPACA_ENVIRONMENT="live"  # or "paper"
```

## Examples

```bash
# Fetch all dividends (today's date folder)
fetch-dividends

# Fetch dividends for a specific fiscal year
fetch-dividends --after 2024-04-06 --until 2025-04-05

# Fetch dividends for a calendar year
fetch-dividends --after 2024-01-01 --until 2024-12-31
```

## Dependencies

- `alpaca-api` package - Alpaca API client abstraction layer

## Use Cases

### Daily Data Snapshot

Run daily to capture a snapshot of all dividend activities:

```bash
# Add to cron or scheduled task
fetch-dividends
```

### Fiscal Year Data

Fetch data for UK tax reporting (fiscal year):

```bash
fetch-dividends --after 2024-04-06 --until 2025-04-05
```

## Related Documentation

- [packages/alpaca-api/README.md](../../packages/alpaca-api/README.md) - Alpaca API package documentation
