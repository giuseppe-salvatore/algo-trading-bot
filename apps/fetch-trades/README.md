# Fetch Trades App

Fetch trading activities (FILL, NC, SPLIT) from Alpaca API and save to timestamped daily folders.

## Overview

This app uses the `alpaca-api` package to fetch three types of trading activities from Alpaca's API:
- **FILL** activities (trade fills) → saved as `taxable_activities.json`
- **NC** activities (name changes) → saved as `name_changes.json`
- **SPLIT** activities (stock splits) → saved as `splits.json`

All data is saved to timestamped folders in `data/trading/alpaca/live/YYYY-MM-DD/` to avoid overriding existing data.

## Installation

The app is part of the monorepo workspace. Install dependencies:

```bash
pdm install
```

## Usage

### Basic Usage

Fetch all trading activities (saves to today's date folder):

```bash
pdm run -p apps/fetch-trades python apps/fetch-trades/src/fetch_trades.py
```

Or using the script command (after installation):

```bash
fetch-trades
```

### With Date Filtering

Fetch activities for a specific date range:

```bash
fetch-trades --after 2024-01-01 --until 2024-12-31
```

### Custom Output Directory

Use a custom output directory (for testing):

```bash
fetch-trades --output-dir data/trading/alpaca/test
```

## Command Reference

**fetch-trades**

Fetch trading activities from Alpaca API.

**Syntax:**
```bash
fetch-trades [--after DATE] [--until DATE] [--output-dir PATH]
```

**Options:**
- `--after DATE`: Fetch activities after this date (YYYY-MM-DD format)
- `--until DATE`: Fetch activities until this date (YYYY-MM-DD format)
- `--output-dir PATH`: Base output directory (default: `data/trading/alpaca/live`)

## Output Structure

The app creates a timestamped folder for each day it runs:

```
data/trading/alpaca/live/YYYY-MM-DD/
├── taxable_activities.json  # FILL activities (trade fills)
├── name_changes.json        # NC activities (name changes)
└── splits.json              # SPLIT activities (stock splits)
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
# Fetch all activities (today's date folder)
fetch-trades

# Fetch activities for a specific fiscal year
fetch-trades --after 2024-04-06 --until 2025-04-05

# Fetch activities for a calendar year
fetch-trades --after 2024-01-01 --until 2024-12-31
```

## Dependencies

- `alpaca-api` package - Alpaca API client abstraction layer

## Use Cases

### Daily Data Snapshot

Run daily to capture a snapshot of all trading activities:

```bash
# Add to cron or scheduled task
fetch-trades
```

### Fiscal Year Data

Fetch data for UK tax reporting (fiscal year):

```bash
fetch-trades --after 2024-04-06 --until 2025-04-05
```

## Related Documentation

- [packages/alpaca-api/README.md](../../packages/alpaca-api/README.md) - Alpaca API package documentation
